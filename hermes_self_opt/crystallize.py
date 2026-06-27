"""
crystallize.py — 新 Skill 自动生成（借鉴 GenericAgent Crystallization）。

从多个 session 中发现重复排障模式，自动生成 SKILL.md：
  1. 收集近期排障 session 的对话文本
  2. 调 LLM 跨 session 检测重复模式 → 生成 skill 草稿
  3. 去重检查（对比已有 skill）
  4. Gate-Lite 验证 → 写入

对外暴露 crystallize() 和 crystallize_detect()。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MIN_SESSIONS_FOR_PATTERN = 3  # 至少 N 个 session 才触发生成
MAX_DIALOG_CHARS_PER_SESSION = 2000  # 每个 session 截取上限
MAX_TOTAL_DIALOG_CHARS = 12000  # 所有 session 对话总长上限

# ──────────────────────────────────────────────
#  Prompt
# ──────────────────────────────────────────────

CRYSTALLIZE_PROMPT = """你是一个 AI agent 的自我进化分析器。分析以下多个排障 session 的对话摘要，发现重复出现的排障模式，并为每种模式生成一个可复用的 SKILL.md。

## Session 摘要
{session_summaries}

## 已有 Skill 列表（避免重复生成）
{existing_skills}

## 任务
1. 识别跨 session 重复出现的排障模式（同类型问题在 ≥2 个 session 中出现）
2. 对每种模式生成一个 SKILL.md，包含：
   - YAML frontmatter（name, description, category, os, version）
   - 排障步骤（分阶段，使用 ```<<< 说明 >>>\ncommand``` 格式）
3. 如果所有 session 的模式都已有对应 skill，返回空列表

## 输出格式（严格 JSON）
```json
{{
  "patterns_found": true/false,
  "skills": [
    {{
      "name": "skill-名称（小写连字符）",
      "description": "一句话描述（中英文皆可）",
      "content": "完整的 SKILL.md 内容（包含 frontmatter 和 markdown 步骤）",
      "source_sessions": ["session_id_1", "session_id_2"],
      "rationale": "为什么这是一个新 pattern（与已有 skill 的区别）"
    }}
  ]
}}
```

## 注意事项
- 每个 skill 控制在 1500 字以内
- 排障步骤要具体可执行，不要泛泛而谈
- 如果模式和已有 skill 高度重叠，不要生成
- name 用小写连字符，英文或拼音
"""


# ──────────────────────────────────────────────
#  数据收集
# ──────────────────────────────────────────────

def _collect_recent_sessions(days: int = 7) -> List[Dict[str, Any]]:
    """收集近期排障 session 的对话摘要。

    Args:
        days: 回溯天数

    Returns:
        [{"session_id": str, "title": str, "dialog": str, "has_skill": bool}, ...]
    """
    try:
        from hermes_self_opt.harvest import harvest, list_recent_sessions
        from hermes_self_opt.filter import looks_like_troubleshooting
    except ImportError as e:
        logger.error("Cannot import harvest/filter: %s", e)
        return []

    sessions = list_recent_sessions(days=days, limit=50)
    results = []

    for s in sessions:
        sid = s["session_id"]
        try:
            dialog = harvest(sid)
        except Exception:
            continue

        if not dialog.strip() or not looks_like_troubleshooting(dialog):
            continue

        # 截取前 N 字符
        truncated = dialog[:MAX_DIALOG_CHARS_PER_SESSION]
        results.append({
            "session_id": sid,
            "title": s.get("title", sid[:16]),
            "dialog": truncated,
        })

        if len(results) >= 30:
            break

    return results


def _format_session_summaries(sessions: List[Dict[str, Any]]) -> str:
    """将 session 列表格式化为 LLM prompt 文本。"""
    parts = []
    total = 0
    for i, s in enumerate(sessions):
        header = f"## Session {i + 1}: {s['session_id'][:16]} ({s.get('title', '?')})"
        dialog = s.get("dialog", "")
        block = f"{header}\n{dialog}\n"

        if total + len(block) > MAX_TOTAL_DIALOG_CHARS:
            remaining = MAX_TOTAL_DIALOG_CHARS - total
            parts.append(block[:remaining] + "\n...[truncated]")
            break

        parts.append(block)
        total += len(block)

    return "\n---\n".join(parts)


def _get_existing_skill_list() -> str:
    """获取已有 skill 列表（名称 + 描述），供 LLM 去重参考。"""
    skills_dir = Path.home() / ".hermes" / "skills"
    if not skills_dir.exists():
        return "无已有 skill"

    import yaml
    lines = []
    for skill_md in sorted(skills_dir.rglob("SKILL.md")):
        try:
            content = skill_md.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm = yaml.safe_load(parts[1]) or {}
                    name = fm.get("name", skill_md.parent.name)
                    desc = fm.get("description", "")
                    lines.append(f"  - {name}: {desc}")
        except Exception:
            pass

    if not lines:
        return "无已有 skill"
    return "\n".join(lines)


# ──────────────────────────────────────────────
#  LLM 调用
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
    """从 LLM 响应中提取 JSON。"""
    text = text.strip()
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
        import re as _re
        match = _re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            raw = match.group()
            fixed = _re.sub(r'\\(?!["\\/bfnrtu])', '\\\\\\\\', raw)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
        return {}


# ──────────────────────────────────────────────
#  去重检查
# ──────────────────────────────────────────────

def _is_duplicate_skill(skill_name: str, skill_content: str, threshold: float = 0.6) -> bool:
    """用 Router 检查新 skill 是否与已有 skill 高度重叠。

    Args:
        skill_name: 新 skill 名称
        skill_content: 新 SKILL.md 内容
        threshold: 匹配分数阈值（≥ 此值视为重复）

    Returns:
        True 如果和已有 skill 重叠
    """
    try:
        from hermes_self_opt.router import query
        # 用 skill 名称 + 描述的前 200 字做查询
        # 提取 description 行
        desc_match = re.search(r'description:\s*"?([^"\n]+)"?', skill_content)
        query_text = skill_name
        if desc_match:
            query_text = f"{skill_name} {desc_match.group(1)}"

        results = query(query_text, top_k=3)
        for r in results:
            if r.get("score", 0) >= threshold:
                logger.info("Duplicate detected: '%s' matches '%s' (score=%.2f)",
                            skill_name, r["name"], r["score"])
                return True
        return False
    except Exception as e:
        logger.warning("Dedup check failed: %s", e)
        return False


def _skill_name_exists(skill_name: str) -> bool:
    """检查 skill 文件是否已存在（按 frontmatter name 或目录名）。"""
    try:
        from hermes_self_opt.skillopt import _find_skill_file
        return _find_skill_file(skill_name) is not None
    except ImportError:
        return False


# ──────────────────────────────────────────────
#  检测 + 生成
# ──────────────────────────────────────────────

def crystallize_detect(
    days: int = 7,
    *,
    auxiliary_client=None,
) -> Dict[str, Any]:
    """仅检测重复模式，不生成 skill。

    Args:
        days: 回溯天数
        auxiliary_client: LLM client

    Returns:
        {"session_count": int, "patterns": [...]}
    """
    sessions = _collect_recent_sessions(days=days)
    result = {
        "session_count": len(sessions),
        "min_sessions_for_pattern": MIN_SESSIONS_FOR_PATTERN,
        "enough_sessions": len(sessions) >= MIN_SESSIONS_FOR_PATTERN,
    }

    if not result["enough_sessions"]:
        result["reason"] = f"需要至少 {MIN_SESSIONS_FOR_PATTERN} 个排障 session，当前 {len(sessions)} 个"
        return result

    return result


def crystallize(
    days: int = 7,
    *,
    auxiliary_client=None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """跨 session 检测重复排障模式，自动生成新 skill。

    流程：
      1. 收集近期排障 session 对话
      2. 调 LLM 跨 session 检测模式 → 生成 SKILL.md
      3. 去重检查（对比已有 skill + Router 匹配）
      4. Gate-Lite 验证
      5. 写入 ~/.hermes/skills/self-opt/

    Args:
        days: 回溯天数
        auxiliary_client: LLM client
        dry_run: True 只报告不写入

    Returns:
        {
            "sessions_processed": int,
            "patterns_found": bool,
            "skills_generated": [{name, passed, written, gate_result}, ...],
        }
    """
    result = {
        "sessions_processed": 0,
        "patterns_found": False,
        "skills_generated": [],
    }

    # Step 1: 收集 sessions
    logger.info("Collecting recent troubleshooting sessions (last %d days)...", days)
    sessions = _collect_recent_sessions(days=days)
    result["sessions_processed"] = len(sessions)

    if len(sessions) < MIN_SESSIONS_FOR_PATTERN:
        result["reason"] = f"需要至少 {MIN_SESSIONS_FOR_PATTERN} 个排障 session，当前 {len(sessions)} 个"
        return result

    # Step 2: 调 LLM 检测模式 + 生成 skill
    logger.info("Running crystallization on %d sessions...", len(sessions))
    existing = _get_existing_skill_list()
    summaries = _format_session_summaries(sessions)

    prompt = CRYSTALLIZE_PROMPT.format(
        session_summaries=summaries,
        existing_skills=existing,
    )

    response_text = _call_llm(prompt, auxiliary_client=auxiliary_client)
    if not response_text.strip():
        result["error"] = "LLM returned empty response"
        return result

    parsed = _parse_json(response_text)
    if not parsed:
        result["error"] = "Failed to parse LLM response"
        return result

    result["patterns_found"] = parsed.get("patterns_found", False)
    skills = parsed.get("skills", [])

    if not skills:
        result["reason"] = "LLM found no new patterns worth generating"
        return result

    # Step 3-5: 对每个生成的 skill 做去重 → Gate-Lite → 写入
    for i, skill_data in enumerate(skills):
        skill_name = skill_data.get("name", f"auto-skill-{i+1}")
        skill_content = skill_data.get("content", "")
        description = skill_data.get("description", "")
        rationale = skill_data.get("rationale", "")
        source_sessions = skill_data.get("source_sessions", [])

        skill_result = {
            "name": skill_name,
            "description": description,
            "rationale": rationale,
            "source_sessions": source_sessions,
            "duplicate": False,
            "gate_passed": False,
            "gate_score": 0,
            "written": False,
        }

        logger.info("[%s] Checking for duplicates...", skill_name)

        # 去重 1: 文件名已存在
        if _skill_name_exists(skill_name):
            skill_result["duplicate"] = True
            skill_result["reason"] = f"Skill '{skill_name}' already exists"
            result["skills_generated"].append(skill_result)
            continue

        # 去重 2: Router 语义重叠
        if _is_duplicate_skill(skill_name, skill_content):
            skill_result["duplicate"] = True
            skill_result["reason"] = "Router detected semantic overlap with existing skill"
            result["skills_generated"].append(skill_result)
            continue

        # Gate-Lite 验证
        logger.info("[%s] Running Gate-Lite...", skill_name)
        try:
            from hermes_self_opt.gate import gate_skill
            gate_result = gate_skill(skill_content, auxiliary_client=auxiliary_client)
            skill_result["gate_passed"] = gate_result.get("decision") == "pass"
            skill_result["gate_score"] = gate_result.get("coverage_score", 0)

            if not skill_result["gate_passed"]:
                skill_result["reason"] = f"Gate-Lite rejected: {gate_result.get('reason', 'unknown')}"
                result["skills_generated"].append(skill_result)
                continue
        except Exception as e:
            skill_result["reason"] = f"Gate-Lite error: {e}"
            result["skills_generated"].append(skill_result)
            continue

        # 写入
        if not dry_run:
            logger.info("[%s] Writing skill...", skill_name)
            try:
                from hermes_self_opt.writer import write_skill
                write_result = write_skill(
                    skill_name,
                    skill_content,
                    source_session=",".join(source_sessions) if source_sessions else "crystallize",
                )
                skill_result["written"] = True
                skill_result["write_path"] = write_result.get("path", "")
            except Exception as e:
                skill_result["reason"] = f"Write failed: {e}"
        else:
            skill_result["written"] = False
            skill_result["dry_run_skill"] = skill_content if dry_run else ""

        result["skills_generated"].append(skill_result)

    result["total_generated"] = len(result["skills_generated"])
    result["total_passed"] = sum(1 for s in result["skills_generated"] if s.get("gate_passed"))
    result["total_written"] = sum(1 for s in result["skills_generated"] if s.get("written"))

    return result
