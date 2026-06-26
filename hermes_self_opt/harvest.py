"""
harvest.py — Step 1: 从 Hermes Session DB 读取原始对话数据。

职责：
  - 从 Hermes 的 SQLite Session DB 中读取指定 session 或近期 session
  - 清洗数据：只保留 user 和 assistant 消息，去掉 tool 输出
  - 返回可供 Mine 步骤使用的纯文本对话

依赖：
  - Hermes 的 hermes_state 模块（get_session_db）
  - 需要在 Hermes 的 venv 中运行（或 Hermes 的包路径可用）
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 单次 harvest 最大字符数（防止 Mine 步骤 token 爆炸）
MAX_DIALOG_CHARS = 8000


def _import_hermes_state():
    """延迟导入 hermes_state，避免模块加载时 Hermes 环境未就绪。"""
    try:
        from hermes_state import get_session_db
        return get_session_db
    except ImportError:
        logger.error(
            "Cannot import hermes_state. Make sure you're running inside "
            "Hermes' Python environment (source venv/bin/activate)"
        )
        raise


def list_recent_sessions(days: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
    """获取最近 N 天的 session 列表。

    Args:
        days: 回溯天数
        limit: 最多返回条数

    Returns:
        每个 session 包含 id, title, created_at, message_count
    """
    get_db = _import_hermes_state()
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    sessions = db.get_recent_sessions(limit=limit)

    result = []
    for s in sessions:
        created = getattr(s, "created_at", None)
        if created and created < cutoff:
            continue
        result.append({
            "session_id": s.session_id if hasattr(s, "session_id") else getattr(s, "id", ""),
            "title": getattr(s, "title", ""),
            "created_at": str(getattr(s, "created_at", "")),
            "message_count": getattr(s, "message_count", 0),
        })
    return result


def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    """获取指定 session 的所有消息。

    Args:
        session_id: Hermes session ID

    Returns:
        消息列表，每条包含 role, content, timestamp
    """
    get_db = _import_hermes_state()
    db = get_db()
    messages = db.get_session_messages(session_id)
    return messages


def harvest(session_id: str) -> str:
    """从指定 session 中提取可读的对话文本。

    只保留 user 和 assistant 消息，按时间顺序拼接。
    总长度限制在 MAX_DIALOG_CHARS 以内。

    Args:
        session_id: Hermes session ID

    Returns:
        格式化的对话文本，供 Mine 步骤使用
    """
    raw_messages = get_session_messages(session_id)

    dialog_parts = []
    total_chars = 0

    for msg in raw_messages:
        role = msg.get("role", "")
        if role not in ("user", "assistant"):
            continue

        content = msg.get("content", "")
        if not content or not isinstance(content, str):
            continue

        # 截取每条消息的前 500 字（对话早期内容不重要）
        content = content[:500]
        line = f"[{role}] {content}"

        if total_chars + len(line) > MAX_DIALOG_CHARS:
            dialog_parts.append("...[truncated]")
            break

        dialog_parts.append(line)
        total_chars += len(line)

    return "\n\n".join(dialog_parts)


def harvest_recent(days: int = 1) -> List[Dict[str, Any]]:
    """批量 harvest 最近 N 天的所有 session。

    Args:
        days: 回溯天数

    Returns:
        每个元素: {"session_id": str, "dialog": str, "title": str}
    """
    sessions = list_recent_sessions(days=days)
    results = []
    for s in sessions:
        try:
            dialog = harvest(s["session_id"])
            if dialog.strip():
                results.append({
                    "session_id": s["session_id"],
                    "title": s["title"],
                    "dialog": dialog,
                })
        except Exception as e:
            logger.warning("Harvest failed for session %s: %s", s["session_id"], e)
    return results
