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


def _ensure_dirs():
    """确保所有目标目录存在。"""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


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
