"""
router.py — 本地 FTS5 skill 路由（Phase 4）。

Build 时扫描所有 SKILL.md 的 description，建 SQLite FTS5 索引。
Query 时先走本地（<5ms），命中直接返回 skill 名，没命中兜底 LLM。

借鉴 selftune：记录每次匹配事件，后续用于发现 description gap。
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

ROUTER_DB = Path.home() / ".hermes" / "self-opt" / "router.db"
SKILLS_ROOT = Path.home() / ".hermes" / "skills"

# FTS5 匹配阈值——分数低于此值认为不匹配，丢给 LLM
MIN_SCORE = 0.3


def _get_conn() -> sqlite3.Connection:
    """获取 FTS5 数据库连接。"""
    ROUTER_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(ROUTER_DB))
    conn.row_factory = sqlite3.Row
    return conn


def build_index() -> Dict[str, Any]:
    """扫描所有 skill 的 description，建辅助索引表。"""
    start = time.time()
    conn = _get_conn()

    conn.execute("DROP TABLE IF EXISTS skill_index")
    conn.execute("""
        CREATE TABLE skill_index (
            name TEXT,
            description TEXT,
            path TEXT,
            name_lower TEXT,
            desc_lower TEXT
        )
    """)

    indexed = 0
    skipped = 0

    for skill_md in SKILLS_ROOT.rglob("SKILL.md"):
        try:
            content = skill_md.read_text(encoding="utf-8")
        except Exception:
            skipped += 1
            continue

        name = _extract_frontmatter(content, "name")
        description = _extract_frontmatter(content, "description")

        if not name:
            name = skill_md.parent.name

        if not description:
            skipped += 1
            continue

        conn.execute(
            "INSERT INTO skill_index (name, description, path, name_lower, desc_lower) VALUES (?, ?, ?, ?, ?)",
            (name, description, str(skill_md), name.lower(), description.lower()),
        )
        indexed += 1

    conn.commit()
    conn.close()

    duration = (time.time() - start) * 1000
    logger.info("Built skill index: %d indexed, %d skipped (%.1f ms)", indexed, skipped, duration)
    return {"indexed": indexed, "skipped": skipped, "duration_ms": round(duration, 1)}


def query(user_input: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """LIKE 子串匹配。139 条数据线性扫描 <5ms。"""
    if not ROUTER_DB.exists():
        return []

    conn = _get_conn()
    lower = user_input.lower()
    rows = conn.execute("SELECT name, description, path, name_lower, desc_lower FROM skill_index").fetchall()
    conn.close()

    terms = [t for t in lower.replace(",", " ").split() if len(t) >= 2]
    scored = []
    for row in rows:
        dl = row["desc_lower"] or ""
        nl = row["name_lower"] or ""
        score = 0.0
        for term in terms:
            if term in dl:
                score += 1.0 / len(terms)
            elif term in nl:
                score += 0.5 / len(terms)
        if lower in dl:
            score += 0.5
        if score >= MIN_SCORE:
            scored.append({
                "name": row["name"],
                "description": row["description"],
                "score": round(min(score, 1.0), 3),
                "path": row["path"],
            })
    scored.sort(key=lambda x: -x["score"])
    return scored[:top_k]


def record_match(
    user_input: str,
    matched_skill: str,
    *,
    session_id: str = "",
    used: bool = True,
) -> None:
    """记录一次路由匹配事件，用于后续发现 description gap。

    写入 router.db 中的 router_events 表。
    """
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS router_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_input TEXT,
            matched_skill TEXT,
            used INTEGER,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute(
        "INSERT INTO router_events (session_id, user_input, matched_skill, used) VALUES (?, ?, ?, ?)",
        (session_id, user_input, matched_skill, int(used)),
    )
    conn.commit()
    conn.close()


def get_recent_phrases(skill_name: str, limit: int = 20) -> List[str]:
    """获取某个 skill 最近被用户用什么说法匹配到的。

    用于发现 description gap——如果用户说"AP 连不上"匹配了这个 skill，
    但 description 里没有"连不上"这个词，就需要补充。
    """
    if not ROUTER_DB.exists():
        return []

    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS router_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_input TEXT,
            matched_skill TEXT,
            used INTEGER,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)

    try:
        rows = conn.execute(
            "SELECT DISTINCT user_input FROM router_events WHERE matched_skill = ? ORDER BY timestamp DESC LIMIT ?",
            (skill_name, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []

    conn.close()
    return [r["user_input"] for r in rows]


def stats() -> Dict[str, Any]:
    """返回路由统计信息。"""
    if not ROUTER_DB.exists():
        return {"indexed_skills": 0, "total_events": 0}

    conn = _get_conn()
    try:
        count = conn.execute("SELECT COUNT(*) as n FROM skill_index").fetchone()["n"]
    except sqlite3.OperationalError:
        count = 0
    try:
        events = conn.execute("SELECT COUNT(*) as n FROM router_events").fetchone()["n"]
    except sqlite3.OperationalError:
        events = 0
    conn.close()

    return {"indexed_skills": count, "total_events": events}


def _extract_frontmatter(content: str, key: str) -> str:
    """从 YAML frontmatter 中提取字段值。"""
    # 简单解析：查找 "key: value" 行
    import re
    pattern = rf"^{key}\s*:\s*(.+)$"
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"').strip("'")
    return ""
