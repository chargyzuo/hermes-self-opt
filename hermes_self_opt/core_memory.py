"""
core_memory.py — Core Memory 读写（Phase 3）。

三层记忆的最顶层：从 Daily Memory 蒸馏而来的长期核心记忆。
存储格式为 YAML，按类别分文件存放。
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CORE_DIR = Path.home() / ".hermes" / "memories" / "core"

# Core Memory 的四个分类文件
CATEGORIES = {
    "facts": "facts.yaml",           # 核心事实（用户身份、环境等）
    "preferences": "preferences.yaml", # 用户偏好
    "patterns": "patterns.yaml",      # 重复出现的行为模式
    "environment": "environment.yaml", # 环境配置变更
}


def _read_yaml(path: Path) -> list:
    """安全读取 YAML 文件，返回列表。"""
    try:
        import yaml
        if not path.exists():
            return []
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_yaml(path: Path, data: list) -> None:
    """安全写入 YAML 文件。"""
    try:
        import yaml
        CORE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    except ImportError:
        # fallback: write JSON instead
        import json
        CORE_DIR.mkdir(parents=True, exist_ok=True)
        json_path = path.with_suffix(".json")
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def save_entry(category: str, content: str, confidence: str = "medium") -> Optional[str]:
    """保存一条 Core Memory 条目。

    Args:
        category: 类别（facts/preferences/patterns/environment）
        content: 条目内容（一句话描述）
        confidence: 可信度（high/medium/low）

    Returns:
        条目 ID，失败返回 None
    """
    if category not in CATEGORIES:
        logger.warning("Unknown category: %s", category)
        return None

    file_path = CORE_DIR / CATEGORIES[category]
    entries = _read_yaml(file_path)

    entry_id = f"{category}-{len(entries)+1}"
    entry = {
        "id": entry_id,
        "content": content.strip(),
        "confidence": confidence,
        "added": datetime.now().strftime("%Y-%m-%d"),
    }
    entries.append(entry)
    _write_yaml(file_path, entries)

    logger.info("Saved Core Memory: %s → %s", entry_id, content[:60])
    return entry_id


def load_all() -> str:
    """加载所有 Core Memory，格式化为 agent 可用的文本块。

    Returns:
        可注入 system prompt 的格式化文本
    """
    parts = []
    for category, filename in CATEGORIES.items():
        file_path = CORE_DIR / filename
        entries = _read_yaml(file_path)
        if entries:
            parts.append(f"## {category}")
            for e in entries[-10:]:  # 每种最多取最近 10 条
                content = e.get("content", str(e))
                parts.append(f"- {content}")
            parts.append("")

    return "\n".join(parts)


def stats() -> Dict[str, int]:
    """返回各类别的条目数量统计。"""
    s = {}
    for category, filename in CATEGORIES.items():
        entries = _read_yaml(CORE_DIR / filename)
        s[category] = len(entries)
    return s


def sync_to_memory_md() -> int:
    """将 Core Memory 同步回 MEMORY.md，保持 agent 兼容。

    过程：
      1. 读取 Core Memory 的 YAML 文件
      2. 渲染成跟 MEMORY.md 兼容的格式（用 § 分隔）
      3. 写入 ~/.hermes/memories/MEMORY.md

    Returns:
        写入的条目总数
    """
    from hermes_self_opt.writer import MEMORY_FILE

    parts = []
    total = 0

    for category, filename in CATEGORIES.items():
        entries = _read_yaml(CORE_DIR / filename)
        if not entries:
            continue
        for e in entries[-15:]:  # 每种最多保留 15 条
            content = e.get("content", "").strip()
            if content:
                parts.append(f"§\n{content}\n")
                total += 1

    if parts:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        MEMORY_FILE.write_text("".join(parts), encoding="utf-8")
        logger.info("Synced %d Core Memory entries to %s", total, MEMORY_FILE)

    return total
