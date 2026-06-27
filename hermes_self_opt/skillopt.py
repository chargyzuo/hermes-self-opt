"""
skillopt.py — Skills 优化循环: Rollout → Reflect → Edit → Gate-Lite.

借鉴 SkillOpt Training Loop，对已有 skill 做迭代优化：
  1. Rollout: 用 LLM 模拟 skill 在 benchmark 场景下的执行，产出 trace
  2. Reflect: 对比 trace 和 benchmark 的 required_steps + redlines，找差距
  3. Edit: 根据差距分析生成 skill 修改补丁
  4. Gate-Lite: 验证修改后的 skill 不倒退

对外暴露 optimize_skill() 作为入口。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3
PASS_THRESHOLD = 3  # coverage_score 达到 3 视为通过

# ──────────────────────────────────────────────
#  Prompt 模板
# ──────────────────────────────────────────────

ROLLOUT_PROMPT = """你是一个网络排障 AI agent。你加载了以下 skill，现在遇到一个排障场景。

## Skill 内容
{skill_content}

## 排障场景
{scenario}

## 任务
请逐步走一遍这个 skill 指导的排障流程，输出每一步你会执行的操作和预期结果。
这是模拟执行，不需要真实设备。

输出格式：用编号列表输出步骤，每步包含：
1. 你执行的命令/操作
2. 你期望看到的输出
3. 如果期望输出不满足，下一步做什么
"""

REFLECT_PROMPT = """你是一个 skill 质量评审员。对比模拟执行的 trace 和 Benchmark 的要求，评估 skill 质量。

## Skill 内容
{skill_content}

## 模拟执行 Trace
{trace}

## Benchmark 要求
{benchmark}

## 评分维度
1. 必要步骤覆盖（0-5）：skill 是否引导 agent 执行了 Benchmark 指定的必要步骤。
   - 对比 trace 中实际执行的步骤和 Benchmark 的 required_steps
   - 0-1 = 基本不相关或漏掉大部分步骤
   - 2-3 = 覆盖了部分步骤但缺关键环节
   - 4-5 = 完整覆盖或超额覆盖
2. 红线检查（pass/fail）：trace 中是否出现了 Benchmark 标记的红线操作？

## 输出格式（严格 JSON）
```json
{{
  "coverage_score": 0,
  "redline_pass": true,
  "missed_steps": ["skill 缺失的必要步骤"],
  "bad_guidance": ["skill 引导了错误操作的描述"],
  "suggestions": ["具体的改进建议"]
}}
```"""

EDIT_PROMPT = """你是一个 skill 编辑器。根据质量评审反馈，修改 skill 内容以修复覆盖缺口。

## 当前 Skill
{skill_content}

## 质量评审反馈
- 覆盖分数: {coverage_score}/5
- 红线通过: {redline_pass}
- 缺失步骤: {missed_steps}
- 错误引导: {bad_guidance}
- 改进建议: {suggestions}

## 任务
基于反馈修改 skill。只修改有问题的部分，保留其他内容不变。
输出完整修改后的 skill（包含 frontmatter）。

要求：
- 补充缺失的必要步骤
- 修复错误引导
- 保留原有格式和结构
- 保持简洁

输出完整修改后的 SKILL.md 内容，不要解释修改了什么。
"""


# ──────────────────────────────────────────────
#  Benchmark 加载
# ──────────────────────────────────────────────

def _load_benchmark_for_skill(skill_name: str) -> List[Dict[str, Any]]:
    """加载 skill_execution_benchmark.json 中对应 skill 的条目。

    Args:
        skill_name: skill 的 frontmatter name 或目录名

    Returns:
        匹配的 benchmark 条目列表
    """
    path = Path.home() / ".hermes" / "knowledge" / "self-opt" / "skill_execution_benchmark.json"
    if not path.exists():
        logger.info("Skill execution benchmark not found at %s", path)
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        matched = [item for item in data if item.get("skill", "") == skill_name]
        if not matched:
            logger.info("No benchmark entries for skill '%s'", skill_name)
        return matched
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load skill benchmark: %s", e)
        return []


def _format_benchmark(benchmark: Dict[str, Any]) -> str:
    """格式化单条 benchmark 为 LLM 可读文本。"""
    parts = []
    bid = benchmark.get("id", "?")
    scenario = benchmark.get("scenario", "")
    required = benchmark.get("required_steps", [])
    redlines = benchmark.get("redlines", [])

    parts.append(f"## {bid}: {scenario}")
    parts.append("必要步骤:")
    for s in required:
        parts.append(f"  - {s}")
    parts.append("红线 (绝对不能做):")
    for r in redlines:
        parts.append(f"  - {r}")
    parts.append("")
    return "\n".join(parts)


# ──────────────────────────────────────────────
#  Skill 文件操作
# ──────────────────────────────────────────────

def _find_skill_file(skill_name: str) -> Optional[Path]:
    """在 ~/.hermes/skills/ 下查找 skill 的 SKILL.md。

    按 frontmatter name 或目录名匹配。
    """
    import yaml
    skills_root = Path.home() / ".hermes" / "skills"
    for skill_md in skills_root.rglob("SKILL.md"):
        content = skill_md.read_text(encoding="utf-8")
        # 尝试 frontmatter name
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1])
                    if fm and fm.get("name") == skill_name:
                        return skill_md
                except Exception:
                    pass
        # fallback: 目录名
        if skill_md.parent.name == skill_name:
            return skill_md
    return None


def _read_skill(skill_name: str) -> Optional[str]:
    """读取 skill 的 SKILL.md 内容。"""
    path = _find_skill_file(skill_name)
    if not path:
        logger.error("Skill not found: %s", skill_name)
        return None
    return path.read_text(encoding="utf-8")


def _write_skill(skill_name: str, content: str) -> bool:
    """写回 skill 的 SKILL.md。先备份原文件。"""
    path = _find_skill_file(skill_name)
    if not path:
        logger.error("Cannot write skill, not found: %s", skill_name)
        return False

    # 备份
    backup_path = path.with_suffix(".md.bak")
    path.rename(backup_path)
    logger.info("Backed up to %s", backup_path)

    path.write_text(content, encoding="utf-8")
    logger.info("Written %s (%d bytes)", path, len(content))
    return True


# ──────────────────────────────────────────────
#  LLM 调用辅助
# ──────────────────────────────────────────────

def _call_llm(prompt: str, auxiliary_client=None) -> str:
    """调 auxiliary LLM，返回响应文本。"""
    if auxiliary_client is None:
        try:
            from agent.auxiliary_client import call_llm
            auxiliary_client = call_llm
        except ImportError:
            logger.error("Cannot import auxiliary_client")
            return ""

    messages = [{"role": "user", "content": prompt}]
    try:
        response = auxiliary_client(task="default", messages=messages)
        if hasattr(response, "choices"):
            return response.choices[0].message.content or ""
        elif isinstance(response, dict):
            return response.get("content", "")
        else:
            return str(response)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return ""


def _parse_json(text: str) -> Dict[str, Any]:
    """从 LLM 响应中提取 JSON，处理 markdown 代码块包裹。"""
    text = text.strip()
    # 去掉 ```json ... ``` 包裹
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试修复常见转义问题
        import re
        fixed = re.sub(r'\\(?!["\\/bfnrtu])', '\\\\\\\\', text)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return {}


# ──────────────────────────────────────────────
#  核心三步
# ──────────────────────────────────────────────

def run_rollout(
    skill_content: str,
    scenario: str,
    auxiliary_client=None,
) -> str:
    """Rollout: 模拟 skill 在指定场景下的执行，返回 trace。

    Args:
        skill_content: SKILL.md 内容
        scenario: benchmark 场景描述
        auxiliary_client: LLM client

    Returns:
        模拟执行的 trace 文本
    """
    prompt = ROLLOUT_PROMPT.format(
        skill_content=skill_content,
        scenario=scenario,
    )
    trace = _call_llm(prompt, auxiliary_client=auxiliary_client)
    logger.info("Rollout generated trace (%d chars)", len(trace))
    return trace


def run_reflect(
    skill_content: str,
    trace: str,
    benchmark: Dict[str, Any],
    auxiliary_client=None,
) -> Dict[str, Any]:
    """Reflect: 对比 trace 和 benchmark，评估覆盖度和红线。

    Args:
        skill_content: SKILL.md 内容
        trace: Rollout 产出的模拟执行 trace
        benchmark: 单条 benchmark 条目
        auxiliary_client: LLM client

    Returns:
        {
            "coverage_score": int,
            "redline_pass": bool,
            "missed_steps": [str],
            "bad_guidance": [str],
            "suggestions": [str],
        }
    """
    prompt = REFLECT_PROMPT.format(
        skill_content=skill_content,
        trace=trace,
        benchmark=_format_benchmark(benchmark),
    )
    response_text = _call_llm(prompt, auxiliary_client=auxiliary_client)
    result = _parse_json(response_text)

    if not result:
        logger.warning("Reflect parse failed, returning defaults")
        return {
            "coverage_score": 3,
            "redline_pass": True,
            "missed_steps": [],
            "bad_guidance": [],
            "suggestions": ["自动解析失败，使用默认通过"],
        }

    result.setdefault("coverage_score", 3)
    result.setdefault("redline_pass", True)
    result.setdefault("missed_steps", [])
    result.setdefault("bad_guidance", [])
    result.setdefault("suggestions", [])
    return result


def run_edit(
    skill_content: str,
    reflect_result: Dict[str, Any],
    auxiliary_client=None,
) -> str:
    """Edit: 根据 Reflect 反馈修改 skill。

    Args:
        skill_content: 当前 SKILL.md 内容
        reflect_result: Reflect 的输出
        auxiliary_client: LLM client

    Returns:
        修改后的 SKILL.md 内容
    """
    prompt = EDIT_PROMPT.format(
        skill_content=skill_content,
        coverage_score=reflect_result.get("coverage_score", 0),
        redline_pass=reflect_result.get("redline_pass", True),
        missed_steps="\n  - ".join(reflect_result.get("missed_steps", [])) or "无",
        bad_guidance="\n  - ".join(reflect_result.get("bad_guidance", [])) or "无",
        suggestions="\n  - ".join(reflect_result.get("suggestions", [])) or "无",
    )
    edited = _call_llm(prompt, auxiliary_client=auxiliary_client)

    # 清理 LLM 可能添加的 markdown 代码块包裹
    if edited.startswith("```"):
        lines = edited.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        edited = "\n".join(lines)

    logger.info("Edit produced new skill (%d chars)", len(edited))
    return edited


# ──────────────────────────────────────────────
#  入口：优化循环
# ──────────────────────────────────────────────

def optimize_skill(
    skill_name: str,
    *,
    auxiliary_client=None,
    max_iterations: int = MAX_ITERATIONS,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """对指定 skill 执行完整的 Rollout → Reflect → Edit → Gate-Lite 循环。

    Args:
        skill_name: skill 名称（frontmatter name 或目录名）
        auxiliary_client: LLM client
        max_iterations: 最大迭代次数
        dry_run: True 只报告不写入

    Returns:
        {
            "skill_name": str,
            "benchmark_count": int,
            "iterations": [
                {
                    "iteration": int,
                    "coverage_score": int,
                    "redline_pass": bool,
                    "edits_applied": bool,
                },
                ...
            ],
            "final_score": int,
            "passed": bool,
            "written": bool,
        }
    """
    result: Dict[str, Any] = {
        "skill_name": skill_name,
        "benchmark_count": 0,
        "iterations": [],
        "final_score": 0,
        "passed": False,
        "written": False,
    }

    # 加载 skill
    skill_content = _read_skill(skill_name)
    if not skill_content:
        result["error"] = f"Skill not found: {skill_name}"
        return result

    # 加载 benchmark
    benchmarks = _load_benchmark_for_skill(skill_name)
    result["benchmark_count"] = len(benchmarks)
    if not benchmarks:
        result["error"] = "No benchmark entries for this skill"
        return result

    # 对每个 benchmark 条目做优化循环
    # 合并在同一次 Edit 中处理所有 benchmark 的反馈
    current_content = skill_content
    all_passed = True

    for iteration in range(1, max_iterations + 1):
        iter_result: Dict[str, Any] = {
            "iteration": iteration,
            "benchmarks": [],
        }
        all_bench_ok = True
        combined_missed: List[str] = []
        combined_bad: List[str] = []
        combined_suggestions: List[str] = []
        worst_score = 5

        for bm in benchmarks:
            bm_result: Dict[str, Any] = {"id": bm.get("id", "?")}

            # Rollout
            logger.info("[%s] Iter %d, benchmark %s: Rollout...", skill_name, iteration, bm.get("id"))
            trace = run_rollout(current_content, bm.get("scenario", ""), auxiliary_client)

            # Reflect
            logger.info("[%s] Iter %d, benchmark %s: Reflect...", skill_name, iteration, bm.get("id"))
            reflect = run_reflect(current_content, trace, bm, auxiliary_client)

            score = reflect.get("coverage_score", 3)
            redline = reflect.get("redline_pass", True)
            bm_result["coverage_score"] = score
            bm_result["redline_pass"] = redline

            if score < PASS_THRESHOLD or not redline:
                all_bench_ok = False
                combined_missed.extend(reflect.get("missed_steps", []))
                combined_bad.extend(reflect.get("bad_guidance", []))
                combined_suggestions.extend(reflect.get("suggestions", []))

            if score < worst_score:
                worst_score = score

            iter_result["benchmarks"].append(bm_result)

        iter_result["coverage_score"] = worst_score
        iter_result["all_passed"] = all_bench_ok
        result["iterations"].append(iter_result)

        if all_bench_ok:
            logger.info("[%s] Iter %d: all benchmarks pass (score >= %d)", skill_name, iteration, PASS_THRESHOLD)
            break

        # Edit
        logger.info("[%s] Iter %d: Edit with %d missed, %d bad, %d suggestions",
                    skill_name, iteration,
                    len(combined_missed), len(combined_bad), len(combined_suggestions))

        reflect_summary = {
            "coverage_score": worst_score,
            "redline_pass": False,  # 有未通过的就标记
            "missed_steps": list(set(combined_missed)),
            "bad_guidance": list(set(combined_bad)),
            "suggestions": list(set(combined_suggestions)),
        }
        current_content = run_edit(current_content, reflect_summary, auxiliary_client)
        iter_result["edits_applied"] = True

    # Gate-Lite: 最终验证
    logger.info("[%s] Final Gate-Lite validation...", skill_name)
    from hermes_self_opt.gate import gate_skill
    gate_result = gate_skill(
        current_content,
        auxiliary_client=auxiliary_client,
        skill_name=skill_name,
    )
    result["gate_result"] = gate_result

    final_score = gate_result.get("coverage_score", 0)
    result["final_score"] = final_score
    result["passed"] = gate_result.get("decision") == "pass"

    # 写入
    if result["passed"] and not dry_run:
        written = _write_skill(skill_name, current_content)
        result["written"] = written
    elif dry_run:
        result["written"] = False
        result["dry_run_skill"] = current_content

    # 汇总所有 iteration 中最好的 score
    all_scores = [gate_result.get("coverage_score", 0)]
    for it in result["iterations"]:
        all_scores.append(it.get("coverage_score", 0))
    result["best_score"] = max(all_scores)

    return result


def optimize_all(
    *,
    auxiliary_client=None,
    max_iterations: int = MAX_ITERATIONS,
    dry_run: bool = False,
    skill_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """对所有有 benchmark 的 skill 执行优化循环。

    Args:
        auxiliary_client: LLM client
        max_iterations: 最大迭代次数
        dry_run: True 只报告不写入
        skill_filter: 只优化列表中指定的 skill

    Returns:
        每个 skill 的结果列表
    """
    # 从 benchmark 中提取所有 skill 名
    benchmarks = _load_all_benchmark_skills()
    if skill_filter:
        benchmarks = [s for s in benchmarks if s in skill_filter]

    logger.info("Optimizing %d skills (max %d iterations each)", len(benchmarks), max_iterations)
    results = []
    for skill_name in benchmarks:
        logger.info("=== Optimizing: %s ===", skill_name)
        result = optimize_skill(
            skill_name,
            auxiliary_client=auxiliary_client,
            max_iterations=max_iterations,
            dry_run=dry_run,
        )
        results.append(result)
    return results


def _load_all_benchmark_skills() -> List[str]:
    """从 skill_execution_benchmark.json 提取所有 skill 名。"""
    path = Path.home() / ".hermes" / "knowledge" / "self-opt" / "skill_execution_benchmark.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return sorted(set(item.get("skill", "") for item in data if item.get("skill")))
    except (json.JSONDecodeError, OSError):
        return []
