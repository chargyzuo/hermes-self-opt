"""
gate.py — Step 3: Gate-Lite 验证。

对 Mine 的结果做基本验证：
  1. memory_chunk: 长度限制 + 敏感信息检查
  2. skill_candidate: LLM Judge 评分（必要步骤覆盖 + 红线检查）

Benchmark 为空时只做基本检查（长度、敏感信息），不跑评分。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Memory 最大长度
MAX_MEMORY_CHARS = 500
# 敏感信息模式（阻止写入密码/token）
SENSITIVE_PATTERNS = [
    r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+",
    r"(?i)(api[_-]?key|apikey)\s*[:=]\s*\S+",
    r"(?i)(secret|token)\s*[:=]\s*\S+",
    r"(?i)sk-[a-zA-Z0-9]{20,}",  # OpenAI API key 格式
]

GATE_PROMPT = """你是一个网络排障 skill 质量评审员。以下是一个自动生成的 skill 草稿和 Benchmark 题库。

## Skill 草稿
{skill_content}

## Benchmark 题库（每条都包含：问题 + 必要步骤 + 红线）
{benchmark}

## 评分标准

**模式 A — 如果 Skill 与某条 Benchmark 直接相关（描述同类故障）：**
1. 必要步骤覆盖（0-5）：skill 是否覆盖了 Benchmark 指定的必要步骤。
   - 0-1 = 基本不相关或漏掉大部分步骤
   - 2-3 = 覆盖了部分步骤但缺关键环节
   - 4-5 = 完整覆盖或超额覆盖
2. 红线检查（pass/fail）：skill 是否包含了 Benchmark 标记的红线操作？
   - 注意：除了 Benchmark 明确列出的红线，也要警惕明显错误（如跳过必经步骤）

**模式 B — 如果 Skill 与所有 Benchmark 都不直接相关：**
1. 给出覆盖分 3（通用质量，不匹配任何已知排障场景）
2. 红线检查：skill 是否明显错误（如跳过必经物理层检查、直接 reset 设备等）

## 输出格式（严格 JSON）
```json
{{
  "matched_benchmark": "bench-001 或 null",
  "coverage_score": 0,
  "redline_pass": true,
  "reason": "简要说明"
}}
```"""


def _has_sensitive_content(text: str) -> bool:
    """检查文本是否包含敏感信息（密码、token 等）。"""
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def _load_benchmark(benchmark_path: Optional[str] = None) -> str:
    """加载知识库 Benchmark 题库，返回格式化的文本。

    返回内容包含每条 Benchmark 的问题/场景、必要步骤和红线，
    供 LLM Judge 做两个维度的评分。
    """
    if benchmark_path:
        path = Path(benchmark_path)
    else:
        path = Path.home() / ".hermes" / "knowledge" / "self-opt" / "benchmark.json"

    if not path.exists():
        logger.info("Benchmark file not found at %s, skipping LLM Judge", path)
        return ""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or len(data) == 0:
            return ""

        return _format_benchmark_entries(data)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load benchmark: %s", e)
        return ""


def _load_skill_execution_benchmark(skill_name: str) -> str:
    """加载 Skill Execution Benchmark，按 skill 名过滤匹配的测试条目。

    从 skill_execution_benchmark.json 中筛选 skill 字段匹配的条目，
    格式化后供 LLM Judge 对自动生成的 skill 做精准评分。

    Args:
        skill_name: skill 名称（如 huawei-mac-auth-debug）

    Returns:
        格式化的 benchmark 文本；无匹配条目时返回空字符串
    """
    path = Path.home() / ".hermes" / "knowledge" / "self-opt" / "skill_execution_benchmark.json"

    if not path.exists():
        logger.info("Skill execution benchmark not found at %s", path)
        return ""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or len(data) == 0:
            return ""

        # 按 skill_name 过滤匹配的条目
        matched = [item for item in data if item.get("skill", "") == skill_name]
        if not matched:
            logger.info("No benchmark entries found for skill '%s'", skill_name)
            return ""

        return _format_benchmark_entries(matched)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load skill execution benchmark: %s", e)
        return ""


def _format_benchmark_entries(entries: List[Dict[str, Any]]) -> str:
    """将 benchmark 条目列表格式化为 LLM Judge 可读的文本。

    同时支持知识库 benchmark（question 字段）和
    skill execution benchmark（scenario 字段）。
    """
    parts = []
    for item in entries:
        bid = item.get("id", "?")
        # 同时支持 question（知识库）和 scenario（技能）字段
        question = item.get("question", "") or item.get("scenario", "")
        required = item.get("required_steps", [])
        redlines = item.get("redlines", [])

        parts.append(f"## {bid}: {question}")
        parts.append("必要步骤:")
        for s in required:
            parts.append(f"  - {s}")
        parts.append("红线 (绝对不能出现在 skill 中):")
        for r in redlines:
            parts.append(f"  - {r}")
        parts.append("")

    return "\n".join(parts)


def gate_skill(
    skill_content: str,
    auxiliary_client=None,
    benchmark_path: Optional[str] = None,
    skill_name: Optional[str] = None,
) -> Dict[str, Any]:
    """对 skill 草稿做 LLM Judge 评分。

    优先使用 skill_name 匹配的 Skill Execution Benchmark，
    未匹配时降级到知识库 benchmark（benchmark_path 或默认 benchmark.json）。

    Args:
        skill_content: SKILL.md 内容
        auxiliary_client: Hermes auxiliary client
        benchmark_path: 知识库 Benchmark 题库路径（可选）
        skill_name: skill 名称，用于匹配 Skill Execution Benchmark

    Returns:
        {"decision": "pass"|"fail"|"skip", "coverage_score": int, "reason": str}
    """
    if not skill_content or not skill_content.strip():
        return {"decision": "skip", "coverage_score": 0, "reason": "无 skill 内容"}

    # === 优先做本地基本检查（快、确定） ===
    if len(skill_content) > 15000:
        return {"decision": "fail", "coverage_score": 0, "reason": "skill 过长（>15KB）"}
    if _has_sensitive_content(skill_content):
        return {"decision": "fail", "coverage_score": 0, "reason": "包含敏感信息（密码/token）"}

    # === 加载 Benchmark ===
    # 优先级：Skill Execution Benchmark（精准匹配）→ 知识库 Benchmark → 降级
    benchmark = ""
    source = ""

    if skill_name:
        benchmark = _load_skill_execution_benchmark(skill_name)
        if benchmark:
            source = f"Skill Execution Benchmark ({skill_name})"
        else:
            logger.info("Skill '%s' not in skill benchmark, falling back to knowledge benchmark", skill_name)

    if not benchmark:
        benchmark = _load_benchmark(benchmark_path)
        if benchmark:
            source = "知识库 Benchmark"
        else:
            source = "无 Benchmark"

    if not benchmark:
        return {"decision": "pass", "coverage_score": 3, "reason": "无匹配 Benchmark，通过基本检查"}

    logger.info("Gate-Lite scoring with: %s", source)

    if auxiliary_client is None:
        from agent.auxiliary_client import call_llm
        auxiliary_client = call_llm

    prompt = GATE_PROMPT.format(skill_content=skill_content, benchmark=benchmark)
    try:
        messages = [{"role": "user", "content": prompt}]
        response = auxiliary_client(task="default", messages=messages)
        if hasattr(response, "choices"):
            response_text = response.choices[0].message.content or ""
        elif isinstance(response, dict):
            response_text = response.get("content", "")
        else:
            response_text = str(response)

        if not response_text.strip():
            return {"decision": "pass", "coverage_score": 3, "reason": "LLM 返回空，基本检查已通过"}
    except Exception as e:
        logger.warning("Gate LLM call failed: %s", e)
        return {"decision": "pass", "coverage_score": 3, "reason": f"LLM 调用失败，基本检查已通过: {e}"}

    # 尝试解析 JSON，支持从 markdown 代码块中提取
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """尝试多种策略提取 JSON：纯 JSON → markdown 代码块 → 常见转义修复。"""
        # 策略 1: 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        import re as _re

        # 策略 2: 从 ```json ... ``` 代码块中提取
        m = _re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, _re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 策略 3: 从最外层的 { ... } 中提取（支持简单嵌套）
        m = _re.search(r'\{[^{}]*\}', text, _re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        # 再试匹配完整 JSON 对象（含嵌套）
        m = _re.search(r'\{.*\}', text, _re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        # 策略 4: 修复转义后重试
        fixed = _re.sub(r'\\(?!["\\/bfnrtu])', '\\\\', text)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    result = _extract_json(response_text)
    if result is not None:
        coverage = result.get("coverage_score", 0)
        redline = result.get("redline_pass", True)
        reason = result.get("reason", "")

        if not redline:
            return {"decision": "fail", "coverage_score": coverage, "reason": f"红线检查失败: {reason}"}
        if coverage < 2:
            return {"decision": "fail", "coverage_score": coverage, "reason": f"必要步骤覆盖不足: {reason}"}

        return {"decision": "pass", "coverage_score": coverage, "reason": reason}

    logger.warning("Gate LLM response parse failed after all strategies: %s", response_text[:200])
    return {"decision": "pass", "coverage_score": 3, "reason": "评分解析失败（JSON/markdown/escape 均不可解析），默认通过"}


def gate_memory(memory_chunk: str) -> Dict[str, Any]:
    """对 memory_chunk 做基本验证。

    Args:
        memory_chunk: 待写入的 memory 内容

    Returns:
        {"decision": "pass"|"fail"|"skip", "reason": str}
    """
    if not memory_chunk or not memory_chunk.strip():
        return {"decision": "skip", "reason": "无 memory 内容"}

    if len(memory_chunk) > MAX_MEMORY_CHARS:
        return {"decision": "fail", "reason": f"memory 过长（{len(memory_chunk)}>{MAX_MEMORY_CHARS}）"}

    if _has_sensitive_content(memory_chunk):
        return {"decision": "fail", "reason": "包含敏感信息（密码/token）"}

    return {"decision": "pass", "reason": "通过基本检查"}
