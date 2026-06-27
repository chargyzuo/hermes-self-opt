"""
writer.py — Step 4: 将验证通过的内容写入目标位置。

职责：
  - 写入 Memory 到 ~/.hermes/memories/MEMORY.md
  - 写入 Skill 到 ~/.hermes/skills/self-opt/<name>/SKILL.md
  - 记录所有操作到 ~/.hermes/self-opt/logs/
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Memory 文件路径
MEMORY_FILE = Path.home() / ".hermes" / "memories" / "MEMORY.md"
# Skill 写入目录
SKILL_DIR = Path.home() / ".hermes" / "skills" / "self-opt"
# Log 目录
LOG_DIR = Path.home() / ".hermes" / "self-opt" / "logs"
# 变动日志（skill/knowledge 变更记录）
CHANGE_LOG = Path.home() / ".hermes" / "self-opt" / "change.log"
# Daily Memory 目录（Phase 3）
DAILY_DIR = Path.home() / ".hermes" / "memories" / "daily"
# Core Memory 目录（Phase 3）
CORE_DIR = Path.home() / ".hermes" / "memories" / "core"


def _ensure_dirs():
    """确保所有目标目录存在。"""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    CORE_DIR.mkdir(parents=True, exist_ok=True)


def write_memory(chunk: str) -> Dict[str, Any]:
    """将 memory_chunk 追加到 MEMORY.md。

    Args:
        chunk: Mine 提取的 memory 内容

    Returns:
        {"success": bool, "path": str, "chars_added": int}
    """
    if not chunk or not chunk.strip():
        return {"success": False, "path": str(MEMORY_FILE), "chars_added": 0, "reason": "空内容"}

    _ensure_dirs()

    # 确保 chunk 以换行结尾
    chunk = chunk.strip() + "\n"

    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n§\n{chunk}")

    chars = len(chunk)
    logger.info("Appended %d chars to %s", chars, MEMORY_FILE)
    return {"success": True, "path": str(MEMORY_FILE), "chars_added": chars}


def write_daily(chunk: str, *, source_session: str = "") -> Dict[str, Any]:
    """将 memory_chunk 写入当天的 Daily Memory 文件。

    Phase 3：替代 Phase 1 的 write_memory，从直接写 MEMORY.md
    改为写入 daily/<日期>.md，供后续 Deep Dream 蒸馏使用。

    Args:
        chunk: Mine 提取的 memory 内容
        source_session: 来源 session ID（用于日志）

    Returns:
        {"success": bool, "path": str, "chars_added": int}
    """
    if not chunk or not chunk.strip():
        return {"success": False, "path": "", "chars_added": 0, "reason": "空内容"}

    _ensure_dirs()

    today = datetime.now().strftime("%Y-%m-%d")
    daily_file = DAILY_DIR / f"{today}.md"

    timestamp = datetime.now().strftime("%H:%M")
    session_tag = f" [{source_session[:16]}]" if source_session else ""
    entry = f"§ [{today} {timestamp}]{session_tag}\n{chunk.strip()}\n\n"

    with open(daily_file, "a", encoding="utf-8") as f:
        f.write(entry)

    chars = len(entry)
    logger.info("Appended %d chars to %s", chars, daily_file)
    return {"success": True, "path": str(daily_file), "chars_added": chars}


def write_skill(
    name: str,
    content: str,
    *,
    source_session: str = "",
    overwrite: bool = False,
) -> Dict[str, Any]:
    """将 skill_candidate 写入 skill 目录。

    Args:
        name: skill 名称（小写连字符）
        content: SKILL.md 完整内容
        source_session: 来源 session ID（可选）
        overwrite: 是否覆盖已有同名 skill

    Returns:
        {"success": bool, "path": str, "action": "created"|"updated"|"skipped"}
    """
    if not name or not content:
        return {"success": False, "path": "", "action": "skipped", "reason": "无内容"}

    _ensure_dirs()

    skill_dir = SKILL_DIR / name
    skill_file = skill_dir / "SKILL.md"

    if skill_file.exists() and not overwrite:
        # 存在且不覆盖时，生成 v2 版本
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            # 检查 content hash 是否相同
            existing = skill_file.read_text(encoding="utf-8")
            if existing.strip() == content.strip():
                return {"success": True, "path": str(skill_file), "action": "skipped", "reason": "内容相同"}

        # 追加版本号
        version = 2
        while skill_dir.with_name(f"{name}-v{version}").exists():
            version += 1
        skill_dir = SKILL_DIR / f"{name}-v{version}"
        skill_file = skill_dir / "SKILL.md"

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file.write_text(content, encoding="utf-8")

    action = "updated" if skill_file.exists() else "created"
    logger.info("%s skill: %s", action, name)

    # 写入统一变动日志
    write_change_log("skill", action, name, path=str(skill_file),
                     source=source_session if source_session else "pipeline")

    return {"success": True, "path": str(skill_file), "action": action}


def write_log(entry: Dict[str, Any]) -> str:
    """将一次 self-opt 运行的记录写入 log 文件。

    Args:
        entry: 包含 session_id, memory_result, skill_result, gate_results 等

    Returns:
        log 文件路径
    """
    _ensure_dirs()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"{timestamp}.json"

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **entry,
    }

    log_file.write_text(
        json.dumps(log_entry, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("Wrote log: %s", log_file)
    return str(log_file)


def write_change_log(
    target: str,
    action: str,
    name: str,
    *,
    path: str = "",
    source: str = "",
    detail: str = "",
) -> str:
    """向统一变动日志追加一条记录。

    Args:
        target: 目标类型 — "skill" 或 "knowledge"
        action: 动作 — "created", "updated", "committed", "skipped"
        name: skill 名或 entry id
        path: 文件路径
        source: 来源（session_id 或 "cron"）
        detail: 额外描述

    Returns:
        change.log 路径
    """
    _ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [ts, target, action, name]
    if source:
        parts.append(f"source={source}")
    if path:
        parts.append(f"path={path}")
    if detail:
        parts.append(f"detail={detail}")
    line = " | ".join(parts) + "\n"

    with open(CHANGE_LOG, "a", encoding="utf-8") as f:
        f.write(line)

    logger.info("Change log: %s %s %s", target, action, name)
    return str(CHANGE_LOG)
