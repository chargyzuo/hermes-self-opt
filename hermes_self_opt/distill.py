"""
distill.py — Deep Dream 蒸馏（Phase 3, Day 2）。

将 Daily Memory（当天零散的 memory 片段）用辅助 LLM 压缩成 Core Memory 条目。

借鉴 CowAgent 的设计：把分散的经验连接成模式，压缩比 10:1 ~ 50:1。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from hermes_self_opt.core_memory import save_entry, cleanup_core_memory
from hermes_self_opt.writer import DAILY_DIR, write_log

logger = logging.getLogger(__name__)

DISTILL_PROMPT = """你是记忆蒸馏器。以下是今日的 Daily Memory——当天 agent 使用过程中收集到的零散记忆片段。

请提取其中的核心信息，去掉重复，合并相关条目：

## Daily Memory（当天片段）
{daily_content}

## 输出格式（严格 JSON）
```json
{{
  "has_content": true,
  "facts": [
    {{"content": "核心事实（一句话）", "confidence": "high"}}
  ],
  "preferences": [
    {{"content": "用户偏好（一句话）", "confidence": "high"}}
  ],
  "patterns": [
    {{"content": "排障模式（一句话）", "confidence": "medium"}}
  ],
  "environment": [
    {{"content": "环境变更（一句话）", "confidence": "high"}}
  ]
}}
```

## 规则
- confidence 取 high/medium/low
- 每类最多 5 条，只保留近期最有价值的
- 如果某类无内容，返回空数组 []
- 合并相似条目（如"左佳杰是运维工程师"和"用户是运维"合并为一条）
- 忽略纯工具性记忆（如"查看模型、打开页面"等一次性操作）
"""


def distill_daily(
    date_str: Optional[str] = None,
    *,
    auxiliary_client=None,
    sync: bool = False,
) -> Dict[str, Any]:
    """将指定日期的 Daily Memory 蒸馏为 Core Memory 条目。

    Args:
        date_str: 日期字符串 "YYYY-MM-DD"，默认今天
        auxiliary_client: auxiliary LLM client（可选）
        sync: 是否同步回 MEMORY.md（默认不，MEMORY.md 已废弃）

    Returns:
        {"distilled_count": int, "daily_chars": int, "path": str, "reason": str}
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    daily_file = DAILY_DIR / f"{date_str}.md"
    if not daily_file.exists():
        return {"distilled_count": 0, "daily_chars": 0, "path": "", "reason": "no daily file"}

    daily_content = daily_file.read_text(encoding="utf-8")
    daily_chars = len(daily_content)

    if daily_chars < 50:
        return {"distilled_count": 0, "daily_chars": daily_chars, "path": str(daily_file), "reason": "daily too short"}

    # 调 LLM 蒸馏
    if auxiliary_client is None:
        from agent.auxiliary_client import call_llm
        auxiliary_client = call_llm

    prompt = DISTILL_PROMPT.format(daily_content=daily_content[:8000])
    messages = [{"role": "user", "content": prompt}]

    try:
        response = auxiliary_client(task="default", messages=messages)
        if hasattr(response, "choices"):
            response_text = response.choices[0].message.content or ""
        elif isinstance(response, dict):
            response_text = response.get("content", "")
        else:
            response_text = str(response)

        if not response_text.strip():
            return {"distilled_count": 0, "daily_chars": daily_chars, "path": str(daily_file), "reason": "LLM 返回空"}

        result = _parse_json(response_text)
    except Exception as e:
        logger.warning("Distill LLM call failed: %s", e)
        return {"distilled_count": 0, "daily_chars": daily_chars, "path": str(daily_file), "reason": f"LLM 调用失败: {e}"}

    if not result or not result.get("has_content"):
        return {"distilled_count": 0, "daily_chars": daily_chars, "path": str(daily_file), "reason": "无有价值内容"}

    # 按类别写入 Core Memory
    count = _save_distilled(result)
    result = {"distilled_count": count, "daily_chars": daily_chars, "path": str(daily_file), "reason": "ok"}

    # 蒸馏后全局清理：去重 + 冲突解决
    cleanup_stats = cleanup_core_memory()
    result["cleanup"] = cleanup_stats

    # 写入运行日志
    write_log({"phase": "distill", "date": date_str, "daily_chars": daily_chars,
                "distilled_count": count, "source": "cron"})

    # 同步回 MEMORY.md
    if sync and count > 0:
        from hermes_self_opt.core_memory import sync_to_memory_md
        synced = sync_to_memory_md()
        result["synced"] = synced

    return result


def _save_distilled(result: dict) -> int:
    """把蒸馏结果写入 Core Memory。"""
    categories = {
        "facts": "facts",
        "preferences": "preferences",
        "patterns": "patterns",
        "environment": "environment",
    }
    count = 0
    for key, category in categories.items():
        items = result.get(key, [])
        if not isinstance(items, list):
            continue
        for item in items[:5]:
            content = item.get("content", "") if isinstance(item, dict) else str(item)
            confidence = item.get("confidence", "medium") if isinstance(item, dict) else "medium"
            if content.strip():
                eid = save_entry(category, content, confidence)
                if eid:
                    count += 1
    return count


def _parse_json(text: str) -> dict:
    """解析 LLM 返回的 JSON，三层容错。"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        kept = []
        in_block = False
        for line in lines:
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                kept.append(line)
        cleaned = "\n".join(kept)

    # 直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 找 JSON 块
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        raw = match.group()
        # 修复非法转义
        fixed = re.sub(r'\\(?!["\\/bfnrtu])', '\\\\', raw)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            stripped = re.sub(r'\\(.)', r'\1', raw)
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass

    logger.warning("Cannot parse distill JSON from: %s", text[:200])
    return {}


def cleanup_daily(max_days: int = 30) -> int:
    """删除超过 max_days 的 Daily Memory 文件。

    Returns:
        删除的文件数
    """
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=max_days)
    deleted = 0
    for f in DAILY_DIR.glob("*.md"):
        try:
            date = datetime.strptime(f.stem, "%Y-%m-%d")
            if date < cutoff:
                f.unlink()
                deleted += 1
                logger.info("Cleaned daily: %s", f.name)
        except ValueError:
            pass
    return deleted
