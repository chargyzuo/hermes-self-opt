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
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 单次 harvest 最大字符数（防止 Mine 步骤 token 爆炸）
MAX_DIALOG_CHARS = 8000


def _get_db() -> Any:
    """获取 SessionDB 实例。"""
    try:
        from hermes_state import SessionDB
    except ImportError:
        logger.error(
            "Cannot import hermes_state. Make sure you're running inside "
            "Hermes' Python environment (source venv/bin/activate)"
        )
        raise

    home = Path.home() / ".hermes"
    db_path = home / "state.db"
    if not db_path.exists():
        logger.error("Session DB not found at %s", db_path)
        raise FileNotFoundError(f"Session DB not found: {db_path}")

    return SessionDB(str(db_path), read_only=True)


def list_recent_sessions(days: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
    """获取最近 N 天的 session 列表。

    Args:
        days: 回溯天数
        limit: 最多返回条数

    Returns:
        每个 session 包含 id, title, created_at, message_count
    """
    db = _get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    sessions = db.list_sessions_rich(limit=limit)

    result = []
    for s in sessions:
        created_str = s.get("started_at", "")
        created = _parse_time(created_str)
        if created and created < cutoff:
            continue
        result.append({
            "session_id": s.get("id", ""),
            "title": s.get("title", s.get("id", "")[:16]),
            "created_at": created_str,
            "message_count": s.get("message_count", 0),
        })
    return result


def _parse_time(time_val) -> Optional[datetime]:
    """解析 Hermes 的时间值（可能是字符串或时间戳）。"""
    if time_val is None:
        return None
    if isinstance(time_val, (int, float)):
        return datetime.fromtimestamp(time_val, tz=timezone.utc)
    if isinstance(time_val, str):
        if not time_val:
            return None
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
        ]:
            try:
                return datetime.strptime(time_val, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    """获取指定 session 的所有消息。

    Args:
        session_id: Hermes session ID

    Returns:
        消息列表，每条包含 role, content, timestamp
    """
    db = _get_db()
    messages = db.get_messages(session_id)
    return messages if messages else []


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

        # 截取每条消息的前 500 字
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
