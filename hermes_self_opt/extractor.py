"""
extractor.py — Step 1: parse normal/ Markdown files (Phase 2).

Walk normal/ directory, parse YAML frontmatter and structured sections
(现象 → 排查路径 → 根因 → 方案 → 操作), output structured dicts for
downstream distill_knowledge.py.
"""

from __future__ import annotations

import logging
import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

NORMAL_DIR = Path.home() / ".hermes" / "knowledge" / "normal"

# Markdown section headers we recognize (Chinese + English aliases)
SECTION_ALIASES: Dict[str, List[str]] = {
    "symptoms":    ["现象", "概述", "现象与背景", "问题描述", "Symptoms", "Overview"],
    "troubleshooting": ["排查路径", "排查步骤", "排查过程", "过程", "Troubleshooting", "Steps"],
    "root_cause":  ["原因分析", "根因", "根本原因", "原因", "Root Cause", "Cause"],
    "solution":    ["解决方案", "方案", "解决方法", "对策", "Solution", "Resolution"],
    "actions":     ["操作", "配置命令", "执行步骤", "操作步骤", "Actions", "Commands", "操作指引"],
    "notes":       ["备注", "注意事项", "其他问题", "附注", "Notes", "Caveats"],
}

SECTION_ORDER = ["symptoms", "troubleshooting", "root_cause", "solution", "actions", "notes"]


def _parse_frontmatter(text: str) -> Dict[str, Any]:
    """Parse YAML frontmatter between --- delimiters."""
    fm: Dict[str, Any] = {}
    if not text.startswith("---"):
        return fm

    end = text.find("---", 3)
    if end == -1:
        return fm

    yaml_str = text[3:end].strip()
    if not yaml_str:
        return fm

    try:
        fm = yaml.safe_load(yaml_str) or {}
    except yaml.YAMLError as e:
        logger.warning("Frontmatter parse error: %s", e)

    return fm


def _identify_section(line: str) -> Optional[str]:
    """Match a heading line to a logical section key."""
    # strip ## markers and whitespace
    stripped = re.sub(r"^#+\s*", "", line).strip().lower()
    for key, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            if stripped == alias.lower() or stripped.startswith(alias.lower()):
                return key
    return None


def _extract_sections(body: str) -> Dict[str, str]:
    """Extract named sections from Markdown body."""
    sections: Dict[str, str] = {}
    current_section: Optional[str] = None
    current_lines: List[str] = []

    for line in body.split("\n"):
        if line.startswith("##") or line.startswith("# "):
            new_sec = _identify_section(line)
            if new_sec:
                # save previous section
                if current_section and current_lines:
                    sections[current_section] = "\n".join(current_lines).strip()
                current_section = new_sec
                current_lines = []
                continue
        if current_section:
            current_lines.append(line)

    # flush last section
    if current_section and current_lines:
        sections[current_section] = "\n".join(current_lines).strip()

    return sections


def _extract_commands(text: str) -> List[str]:
    """Extract shell commands from code blocks and inline backticks."""
    commands: List[str] = []
    # code blocks
    for match in re.finditer(r"```(?:\w+)?\s*\n(.*?)```", text, re.DOTALL):
        for line in match.group(1).strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                commands.append(line)
    # inline backticks
    for match in re.finditer(r"`([^`]+)`", text):
        cmd = match.group(1).strip()
        if cmd and not cmd.startswith("#") and len(cmd) > 3:
            commands.append(cmd)
    return commands


def _infer_device_type(filepath: Path, tags: List[str]) -> str:
    """Infer device_type from file path and tags."""
    path_str = str(filepath).lower()
    if "arista" in path_str or any("arista" in t.lower() for t in tags):
        return "arista"
    if "huawei" in path_str or any("huawei" in t.lower() for t in tags):
        return "huawei"
    if "aruba" in path_str or any("aruba" in t.lower() for t in tags):
        return "aruba"
    if "velo" in path_str or any("velo" in t.lower() for t in tags):
        return "velo"
    if "radius" in path_str or any("radius" in t.lower() for t in tags):
        return "radius"
    return "general"


def extract_one(filepath: Path) -> Dict[str, Any]:
    """Extract structured data from one normal/ MD file.

    Returns:
        {
            "filepath": str,
            "frontmatter": {...},
            "sections": {...},
            "commands": [...],
            "device_type": str,
        }
    """
    text = filepath.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)

    # body is everything after frontmatter
    body = text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            body = text[end + 3:]

    sections = _extract_sections(body)
    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    result: Dict[str, Any] = {
        "filepath": str(filepath),
        "frontmatter": fm,
        "sections": sections,
        "commands": _extract_commands(body),
        "device_type": _infer_device_type(filepath, tags),
        "id": fm.get("id", filepath.stem),
        "tags": tags,
        "source_doc": fm.get("source_doc", ""),
        "source": str(filepath.relative_to(NORMAL_DIR)),
    }

    return result


def extract_all(normal_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Walk normal/ directory and extract all MD files.

    Args:
        normal_dir: override normal/ path (default: ~/.hermes/knowledge/normal/)

    Returns:
        List of structured dicts, one per MD file.
    """
    root = Path(normal_dir) if normal_dir else NORMAL_DIR
    if not root.exists():
        logger.warning("normal/ directory not found: %s", root)
        return []

    results: List[Dict[str, Any]] = []
    md_files = sorted(root.rglob("*.md"))

    for f in md_files:
        try:
            result = extract_one(f)
            results.append(result)
            logger.debug("Extracted: %s (tags=%d, cmds=%d)",
                         f.name, len(result["tags"]), len(result["commands"]))
        except Exception as e:
            logger.warning("Failed to extract %s: %s", f.name, e)

    logger.info("Extracted %d/%d files from normal/", len(results), len(md_files))
    return results
