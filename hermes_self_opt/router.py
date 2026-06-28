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

from hermes_self_opt.writer import write_log

try:
    import jieba
    _JIEBA = True
except ImportError:
    jieba = None  # type: ignore
    _JIEBA = False

logger = logging.getLogger(__name__)

from hermes_self_opt import SKILLS_ROOT

ROUTER_DB = Path.home() / ".hermes" / "self-opt" / "router.db"

# FTS5 匹配阈值——分数低于此值认为不匹配，丢给 LLM
MIN_SCORE = 0.2


def _has_cjk(text: str) -> bool:
    """检测是否包含 CJK 字符（中文等）。"""
    for ch in text:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            return True
    return False


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

    # 写入运行日志
    write_log({"phase": "router-build", "indexed": indexed, "skipped": skipped,
                "duration_ms": round(duration, 1), "source": "cron"})

    return {"indexed": indexed, "skipped": skipped, "duration_ms": round(duration, 1)}


def query(user_input: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """LIKE 子串 + CJK trigram 重叠匹配。139 条数据线性扫描 <5ms。"""
    if not ROUTER_DB.exists():
        return []

    conn = _get_conn()
    lower = user_input.lower()
    rows = conn.execute("SELECT name, description, path, name_lower, desc_lower FROM skill_index").fetchall()
    conn.close()

    terms = [t for t in lower.replace(",", " ").split() if len(t) >= 2]
    has_cjk = _has_cjk(user_input)
    # jieba 预分词（中文）
    jieba_tokens = []
    if has_cjk and _JIEBA:
        jieba_tokens = [t.lower() for t in jieba.cut(user_input) if len(t.strip()) >= 1]
    scored = []
    for row in rows:
        dl = row["desc_lower"] or ""
        nl = row["name_lower"] or ""
        score = 0.0
        # Space-separated term matching (English + mixed)
        for term in terms:
            if term in dl:
                score += 1.0 / len(terms)
            elif term in nl:
                score += 0.5 / len(terms)
        # Exact substring boost
        if lower in dl:
            score += 0.5
        # CJK: character-level overlap + jieba token matching
        if has_cjk:
            # 字符级重叠
            cjk_query_chars = [ch for ch in lower if '\u4e00' <= ch <= '\u9fff']
            cjk_desc_chars = set(ch for ch in dl if '\u4e00' <= ch <= '\u9fff')
            if cjk_query_chars and cjk_desc_chars:
                char_hits = sum(1 for ch in cjk_query_chars if ch in cjk_desc_chars)
                score += (char_hits / len(cjk_query_chars)) * 0.5
            # jieba 分词加分（多字词命中）
            if jieba_tokens:
                jieba_hits = 0.0
                for tok in jieba_tokens:
                    if len(tok) >= 2 and tok in dl:
                        jieba_hits += 1.0
                    elif len(tok) >= 2 and tok in nl:
                        jieba_hits += 0.5
                if jieba_hits > 0:
                    score += min(jieba_hits / len(jieba_tokens), 1.0) * 0.15
            # Reverse match
            desc_tokens = [t for t in dl.split() if len(t) >= 2]
            for tok in desc_tokens:
                if tok in lower:
                    score += 0.12 / max(len(desc_tokens), 1)
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
    score: float = 0.0,
    corrected: bool = False,
    correction_detail: str = "",
) -> None:
    """记录一次路由匹配事件，用于后续发现 description gap 和触发率监控。

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
            score REAL DEFAULT 0.0,
            corrected INTEGER DEFAULT 0,
            correction_detail TEXT DEFAULT '',
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)
    # 向后兼容：为旧表加新列
    for col, col_type in [("score", "REAL DEFAULT 0.0"), ("corrected", "INTEGER DEFAULT 0"),
                           ("correction_detail", "TEXT DEFAULT ''")]:
        try:
            conn.execute("ALTER TABLE router_events ADD COLUMN {} {}".format(col, col_type))
        except sqlite3.OperationalError:
            pass

    conn.execute(
        "INSERT INTO router_events (session_id, user_input, matched_skill, used, score, corrected, correction_detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (session_id, user_input, matched_skill, int(used), score, int(corrected), correction_detail),
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


def monitor(
    skill_name: Optional[str] = None,
    days: int = 7,
) -> Dict[str, Any]:
    """路由监控：按 skill 和时间维度统计触发率。

    Args:
        skill_name: 指定 skill 名，None 则返回所有 skill
        days: 统计最近 N 天

    Returns:
        {
            "period": "last 7 days",
            "total_events": N,
            "skills": [
                {
                    "name": "aruba-ap-troubleshooting",
                    "total_matches": 12,
                    "avg_score": 0.72,
                    "trigger_rate": 0.85,         # used / total
                    "correction_rate": 0.08,       # corrected / total
                    "recent_queries": ["...", ...], # 最近 3 条查询
                },
                ...
            ],
            "miss_rate": 0.15,        # 无匹配事件占比
            "overall_correction_rate": 0.05,
        }
    """
    if not ROUTER_DB.exists():
        return {"period": f"last {days} days", "total_events": 0, "skills": [],
                "miss_rate": 0.0, "overall_correction_rate": 0.0}

    conn = _get_conn()

    # 确保表存在
    conn.execute("""
        CREATE TABLE IF NOT EXISTS router_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, user_input TEXT, matched_skill TEXT,
            used INTEGER, score REAL DEFAULT 0.0,
            corrected INTEGER DEFAULT 0, correction_detail TEXT DEFAULT '',
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)

    # 时间过滤子句
    time_clause = "timestamp >= datetime('now', '-{} days')".format(days)
    skill_clause = "AND matched_skill = ?" if skill_name else ""

    # ── 总数 ──
    total_row = conn.execute(
        "SELECT COUNT(*) as n FROM router_events WHERE {}".format(time_clause)
    ).fetchone()
    total_events = total_row["n"] if total_row else 0

    if total_events == 0:
        conn.close()
        return {"period": "last {} days".format(days), "total_events": 0, "skills": [],
                "miss_rate": 0.0, "overall_correction_rate": 0.0}

    # ── 无匹配事件（matched_skill 为空） ──
    miss_row = conn.execute(
        "SELECT COUNT(*) as n FROM router_events WHERE {} AND (matched_skill = '' OR matched_skill IS NULL)".format(time_clause)
    ).fetchone()
    miss_count = miss_row["n"] if miss_row else 0
    miss_rate = round(miss_count / total_events, 3) if total_events else 0.0

    # ── 全局纠正率 ──
    corr_row = conn.execute(
        "SELECT COUNT(*) as n FROM router_events WHERE {} AND corrected = 1".format(time_clause)
    ).fetchone()
    overall_corr = round(corr_row["n"] / total_events, 3) if total_events else 0.0

    # ── 每 skill 统计 ──
    query = """
        SELECT matched_skill,
               COUNT(*) as total,
               AVG(score) as avg_score,
               SUM(CASE WHEN used = 1 THEN 1 ELSE 0 END) as used_count,
               SUM(CASE WHEN corrected = 1 THEN 1 ELSE 0 END) as corrected_count
        FROM router_events
        WHERE {} AND matched_skill != '' AND matched_skill IS NOT NULL
        {}
        GROUP BY matched_skill
        ORDER BY total DESC
    """.format(time_clause, skill_clause)

    params = (skill_name,) if skill_name else ()
    rows = conn.execute(query, params).fetchall()

    skills = []
    for row in rows:
        total = row["total"]
        used_count = row["used_count"]
        corrected_count = row["corrected_count"]
        avg_score = round(row["avg_score"], 3) if row["avg_score"] else 0.0
        trigger_rate = round(used_count / total, 3) if total else 0.0
        correction_rate = round(corrected_count / total, 3) if total else 0.0

        # 最近 3 条查询
        recent = conn.execute(
            "SELECT user_input FROM router_events WHERE matched_skill = ? ORDER BY timestamp DESC LIMIT 3",
            (row["matched_skill"],)
        ).fetchall()
        recent_queries = [r["user_input"] for r in recent]

        skills.append({
            "name": row["matched_skill"],
            "total_matches": total,
            "avg_score": avg_score,
            "trigger_rate": trigger_rate,
            "correction_rate": correction_rate,
            "recent_queries": recent_queries,
        })

    conn.close()

    return {
        "period": "last {} days".format(days),
        "total_events": total_events,
        "skills": skills,
        "miss_rate": miss_rate,
        "overall_correction_rate": overall_corr,
    }


REWRITE_PROMPT = """优化以下 skill 的描述，使其更准确地覆盖用户的真实说法。

## 当前描述
{description}

## 用户最近的说法（未被当前描述覆盖）
{gaps}

## 要求
- 保留原始描述的核心含义
- 加入用户常用的关键词，让描述覆盖这些说法
- 不要改变 skill 的职责范围
- 新增关键词不超过 30 字
- 只输出新的 description 文本，不要输出其他内容"""


def find_description_gap(skill_name: str) -> Optional[str]:
    """检查 skill 的 description 是否覆盖了用户常用说法。

    Args:
        skill_name: skill 名称

    Returns:
        gap 描述字符串（如 "未覆盖: AP连不上, 无线掉线"），无 gap 返回 None
    """
    if not ROUTER_DB.exists():
        return None

    conn = _get_conn()
    # 获取当前 description
    row = conn.execute(
        "SELECT description FROM skill_index WHERE name = ? LIMIT 1", (skill_name,)
    ).fetchone()
    conn.close()

    if not row:
        return None

    current_desc = (row["description"] or "").lower()
    phrases = get_recent_phrases(skill_name, limit=10)

    if not phrases:
        return None

    # 找出 description 没覆盖的说法
    gaps = []
    for phrase in phrases:
        phrase_lower = phrase.lower()
        # 检查是否在 description 里（允许部分匹配）
        covered = any(word in current_desc for word in phrase_lower.split() if len(word) >= 2)
        if not covered:
            gaps.append(phrase)

    if len(gaps) >= 2:
        return ", ".join(gaps[:5])
    return None


def rewrite_description(
    skill_name: str,
    *,
    auxiliary_client=None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """用 LLM 重写 skill description，覆盖用户的真实说法。

    Args:
        skill_name: skill 名称
        auxiliary_client: auxiliary LLM client
        dry_run: True 只返回建议，不写入

    Returns:
        {"action": "rewrote"|"no_gap"|"skipped", "old": str, "new": str}
    """
    gap = find_description_gap(skill_name)
    if not gap:
        return {"action": "no_gap", "reason": "无需优化"}

    # 获取当前描述和 skill 文件路径
    conn = _get_conn()
    row = conn.execute(
        "SELECT description, path FROM skill_index WHERE name = ? LIMIT 1", (skill_name,)
    ).fetchone()
    conn.close()

    if not row:
        return {"action": "skipped", "reason": "skill 不在索引中"}

    old_desc = row["description"]
    skill_path = Path(row["path"])

    if not skill_path.exists():
        return {"action": "skipped", "reason": "skill 文件不存在"}

    # 调 LLM 重写
    if auxiliary_client is None:
        from agent.auxiliary_client import call_llm
        auxiliary_client = call_llm

    prompt = REWRITE_PROMPT.format(description=old_desc, gaps=gap)
    messages = [{"role": "user", "content": prompt}]

    try:
        response = auxiliary_client(task="default", messages=messages)
        if hasattr(response, "choices"):
            new_desc = response.choices[0].message.content or ""
        elif isinstance(response, dict):
            new_desc = response.get("content", "")
        else:
            new_desc = str(response)
    except Exception as e:
        logger.warning("Rewrite LLM call failed: %s", e)
        return {"action": "skipped", "reason": f"LLM 调用失败: {e}"}

    new_desc = new_desc.strip()
    if not new_desc or len(new_desc) < 10:
        return {"action": "skipped", "reason": "LLM 返回空或太短"}

    # 如果跟旧的一样就不改
    if new_desc == old_desc:
        return {"action": "no_gap", "reason": "新描述和旧描述相同"}

    if dry_run:
        return {"action": "dry_run", "old": old_desc, "new": new_desc}

    # 备份旧版本
    _backup_skill(skill_path)

    # 写入新描述
    content = skill_path.read_text(encoding="utf-8")
    import re
    new_content = re.sub(
        rf"(^description\s*:\s*).+$",
        rf"\1{new_desc}",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    skill_path.write_text(new_content, encoding="utf-8")

    logger.info("Rewrote description for %s: %s → %s", skill_name, old_desc[:60], new_desc[:60])
    return {"action": "rewrote", "old": old_desc, "new": new_desc}


def _backup_skill(skill_path: Path) -> None:
    """备份 skill 文件到 router.db 中的 backup 表。"""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skill_backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT,
            content TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)
    content = skill_path.read_text(encoding="utf-8")
    conn.execute(
        "INSERT INTO skill_backups (path, content) VALUES (?, ?)",
        (str(skill_path), content),
    )
    conn.commit()
    conn.close()


def rollback_skill(skill_name: str) -> Dict[str, Any]:
    """回滚 skill 到上一个备份版本。

    Returns:
        {"action": "rolled_back"|"no_backup", ...}
    """
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skill_backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT,
            content TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)
    row = conn.execute(
        "SELECT path, content FROM skill_backups WHERE path LIKE ? ORDER BY id DESC LIMIT 1",
        (f"%{skill_name}%",),
    ).fetchone()
    conn.close()

    if not row:
        return {"action": "no_backup", "reason": "无备份可回滚"}

    skill_path = Path(row["path"])
    skill_path.write_text(row["content"], encoding="utf-8")
    logger.info("Rolled back skill: %s", skill_name)
    return {"action": "rolled_back", "path": str(skill_path)}


def _extract_frontmatter(content: str, key: str) -> str:
    """从 YAML frontmatter 中提取字段值。"""
    # 简单解析：查找 "key: value" 行
    import re
    pattern = rf"^{key}\s*:\s*(.+)$"
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"').strip("'")
    return ""
