"""
core_memory.py — Core Memory 读写（Phase 3）。

三层记忆的最顶层：从 Daily Memory 蒸馏而来的长期核心记忆。
存储格式为 YAML，按类别分文件存放。

v2.0: 新增去重、冲突解决、日期追踪（added/updated）。
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CORE_DIR = Path.home() / ".hermes" / "memories" / "core"

CATEGORIES = {
    "facts": "facts.yaml",
    "preferences": "preferences.yaml",
    "patterns": "patterns.yaml",
    "environment": "environment.yaml",
}

# 相似度阈值
SIMILARITY_DEDUP_THRESHOLD = 0.70   # >= 视为重复，合并
SIMILARITY_TOPIC_THRESHOLD = 0.35   # >= 视为同主题，检查冲突

# 冲突检测关键词对（中文）
CONTRADICTION_PAIRS = [
    # (模式 A, 模式 B) — 包含 A 和 B 中出现相反的视为冲突
    (["必须", "需要", "要求", "一定", "总是"], ["不要", "不", "拒绝", "禁止", "从不"]),
    (["偏好", "喜欢", "习惯"], ["不喜欢", "讨厌", "避免", "不偏好"]),
    (["是", "为"], ["不是", "不为", "非"]),
    (["已配置", "已添加"], ["未配置", "未添加", "没有"]),
    (["开启", "启用"], ["关闭", "禁用"]),
]


def _read_yaml(path: Path) -> list:
    try:
        import yaml
        if not path.exists():
            return []
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_yaml(path: Path, data: list) -> None:
    try:
        import yaml
        CORE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.dump(data, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
    except ImportError:
        import json
        CORE_DIR.mkdir(parents=True, exist_ok=True)
        json_path = path.with_suffix(".json")
        json_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


# ---------- 文本相似度 ----------

def _tokenize(text: str) -> set:
    """分词：中文用字符 bigram + 词级，英文用词级。"""
    tokens = set()

    # 英文单词
    words = re.findall(r"[a-zA-Z0-9._/-]+", text.lower())
    tokens.update(words)

    # 中文：字符级 bigram
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    for i in range(len(chinese_chars) - 1):
        tokens.add("".join(chinese_chars[i : i + 2]))
    # 单个汉字也加入
    tokens.update(chinese_chars)

    return tokens


def _text_similarity(a: str, b: str) -> float:
    """Jaccard 相似度，0.0 ~ 1.0。"""
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    if not tokens_a or not tokens_b:
        # 回退：子串检查
        if a in b or b in a:
            return 0.85
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    sim = intersection / union if union > 0 else 0.0

    # 子串加分
    if a in b or b in a:
        sim = max(sim, 0.85)

    return sim


# ---------- 冲突检测 ----------

def _is_contradiction(a: str, b: str) -> bool:
    """检测两条内存是否矛盾。"""
    for pos_patterns, neg_patterns in CONTRADICTION_PAIRS:
        a_pos = any(p in a for p in pos_patterns)
        a_neg = any(p in a for p in neg_patterns)
        b_pos = any(p in b for p in pos_patterns)
        b_neg = any(p in b for p in neg_patterns)
        # 一个正面一个负面
        if (a_pos and b_neg) or (a_neg and b_pos):
            return True
    return False


def _resolve_contradiction(
    existing: dict, new_entry: dict
) -> Tuple[dict, str]:
    """解决冲突：保留置信度高的；同置信度保留更新的。

    Returns:
        (winning_entry, reason)
    """
    existing_conf = _confidence_score(existing.get("confidence", "medium"))
    new_conf = _confidence_score(new_entry.get("confidence", "medium"))

    if new_conf > existing_conf:
        new_entry["id"] = existing["id"]
        new_entry["added"] = existing.get("added", new_entry.get("added"))
        return new_entry, "newer entry has higher confidence"
    elif existing_conf > new_conf:
        return existing, "existing entry has higher confidence"
    else:
        # 同置信度：保留日期更新的
        existing_date = existing.get("updated", existing.get("added", ""))
        new_date = new_entry.get("updated", new_entry.get("added", ""))
        if new_date > existing_date:
            new_entry["id"] = existing["id"]
            new_entry["added"] = existing.get("added", new_entry.get("added"))
            return new_entry, "same confidence, newer date wins"
        return existing, "same confidence, existing date is newer"


def _confidence_score(conf: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(conf, 2)


# ---------- 核心操作 ----------

def upsert_entry(
    category: str,
    content: str,
    confidence: str = "medium",
) -> Optional[str]:
    """保存/更新一条 Core Memory 条目。

    去重逻辑：
    1. 内容完全相同 → 跳过
    2. 高度相似 (>=0.70) → 更新 updated 日期，保留一条
    3. 同主题 (>=0.35) + 矛盾 → 冲突解决，只留一条
    4. 全新内容 → 追加

    Args:
        category: 类别（facts/preferences/patterns/environment）
        content: 条目内容
        confidence: 可信度

    Returns:
        条目 ID，跳过返回 None
    """
    if category not in CATEGORIES:
        logger.warning("Unknown category: %s", category)
        return None

    file_path = CORE_DIR / CATEGORIES[category]
    entries = _read_yaml(file_path)
    today = datetime.now().strftime("%Y-%m-%d")

    new_entry = {
        "content": content.strip(),
        "confidence": confidence,
        "added": today,
        "updated": today,
        "duplicate_count": 1,
    }

    for i, existing in enumerate(entries):
        existing_content = existing.get("content", "").strip()

        # 1. 完全一致 → 跳过（但记录重复次数）
        if existing_content == new_entry["content"]:
            existing.setdefault("duplicate_count", 1)
            existing["duplicate_count"] = existing.get("duplicate_count", 1) + 1
            existing["updated"] = today
            _write_yaml(file_path, entries)
            logger.debug("Duplicate (exact) count=%d: %s", existing["duplicate_count"], content[:40])
            return existing.get("id")

        sim = _text_similarity(existing_content, new_entry["content"])

        # 2. 高度相似 → 更新
        if sim >= SIMILARITY_DEDUP_THRESHOLD:
            entries[i]["updated"] = today
            entries[i]["content"] = new_entry["content"]  # 用新内容
            entries[i]["confidence"] = max(
                confidence,
                entries[i].get("confidence", "medium"),
                key=lambda c: _confidence_score(c),
            )
            entries[i].setdefault("duplicate_count", 1)
            entries[i]["duplicate_count"] = entries[i].get("duplicate_count", 1) + 1
            _write_yaml(file_path, entries)
            logger.info("Updated (similar %.2f, count=%d): %s", sim, entries[i]["duplicate_count"], existing.get("id", ""))
            return existing.get("id")

        # 3. 同主题 + 矛盾 → 解决
        if sim >= SIMILARITY_TOPIC_THRESHOLD and _is_contradiction(
            existing_content, new_entry["content"]
        ):
            winner, reason = _resolve_contradiction(existing, new_entry)
            entries[i] = winner
            winner["updated"] = today
            _write_yaml(file_path, entries)
            logger.info(
                "Resolved contradiction (sim=%.2f): %s — %s",
                sim,
                winner.get("id", ""),
                reason,
            )
            return winner.get("id")

    # 4. 全新条目
    entry_id = f"{category}-{len(entries) + 1}"
    new_entry["id"] = entry_id
    entries.append(new_entry)
    _write_yaml(file_path, entries)
    logger.info("Saved Core Memory: %s → %s", entry_id, content[:60])
    return entry_id


# 保留旧接口兼容
def save_entry(category: str, content: str, confidence: str = "medium") -> Optional[str]:
    """旧接口，转发到 upsert_entry。"""
    return upsert_entry(category, content, confidence)


def cleanup_core_memory() -> Dict[str, int]:
    """全局清理 Core Memory：类内去重 + 冲突解决。

    在 distill 完成后调用，清理蒸馏可能产生的新重复。

    Returns:
        {"merged": N, "resolved": N, "total_before": N, "total_after": N}
    """
    merged = 0
    resolved = 0
    total_before = 0

    for category, filename in CATEGORIES.items():
        file_path = CORE_DIR / filename
        entries = _read_yaml(file_path)
        total_before += len(entries)
        if len(entries) < 2:
            # 即使只有 1 条也补全 duplicate_count
            if len(entries) == 1:
                entries[0].setdefault("duplicate_count", 1)
                _write_yaml(file_path, entries)
            continue

        kept = []
        for i, entry in enumerate(entries):
            # 向后兼容：补全 duplicate_count
            entry.setdefault("duplicate_count", 1)
            content_i = entry.get("content", "").strip()
            should_skip = False

            for j, other in enumerate(kept):
                content_j = other.get("content", "").strip()
                sim = _text_similarity(content_i, content_j)

                # 高度相似 → 合并
                if sim >= SIMILARITY_DEDUP_THRESHOLD:
                    # 保留置信度更高的
                    conf_i = _confidence_score(entry.get("confidence", "medium"))
                    conf_j = _confidence_score(other.get("confidence", "medium"))
                    # 累加重复次数
                    entry_count = entry.get("duplicate_count", 1)
                    other_count = other.get("duplicate_count", 1)
                    if conf_i > conf_j:
                        # 用 entry 替换 other
                        entry["id"] = other["id"]
                        entry["added"] = other.get("added", entry.get("added", ""))
                        entry["duplicate_count"] = entry_count + other_count
                        kept[j] = entry
                    else:
                        kept[j]["updated"] = datetime.now().strftime("%Y-%m-%d")
                        kept[j]["duplicate_count"] = kept[j].get("duplicate_count", 1) + entry_count
                    merged += 1
                    should_skip = True
                    break

                # 同主题 + 矛盾 → 解决
                if sim >= SIMILARITY_TOPIC_THRESHOLD and _is_contradiction(
                    content_i, content_j
                ):
                    winner, reason = _resolve_contradiction(other, entry)
                    winner["updated"] = datetime.now().strftime("%Y-%m-%d")
                    kept[j] = winner
                    resolved += 1
                    should_skip = True
                    break

            if not should_skip:
                kept.append(entry)

        # 重新编号
        for idx, entry in enumerate(kept):
            entry["id"] = f"{category}-{idx + 1}"

        _write_yaml(file_path, kept)

    total_after = sum(
        len(_read_yaml(CORE_DIR / f)) for f in CATEGORIES.values()
    )

    logger.info(
        "Core Memory cleanup: %d → %d entries (merged=%d, resolved=%d)",
        total_before, total_after, merged, resolved,
    )

    return {
        "merged": merged,
        "resolved": resolved,
        "total_before": total_before,
        "total_after": total_after,
    }


# ---------- 查询 ----------

def load_all() -> str:
    parts = []
    for category, filename in CATEGORIES.items():
        file_path = CORE_DIR / filename
        entries = _read_yaml(file_path)
        if entries:
            parts.append(f"## {category}")
            for e in entries[-10:]:
                content = e.get("content", str(e))
                parts.append(f"- {content}")
            parts.append("")
    return "\n".join(parts)


def stats() -> Dict[str, int]:
    s = {}
    for category, filename in CATEGORIES.items():
        entries = _read_yaml(CORE_DIR / filename)
        s[category] = len(entries)
    return s


def sync_to_memory_md() -> int:
    from hermes_self_opt.writer import MEMORY_FILE

    parts = []
    total = 0

    for category, filename in CATEGORIES.items():
        entries = _read_yaml(CORE_DIR / filename)
        if not entries:
            continue
        for e in entries[-15:]:
            content = e.get("content", "").strip()
            if content:
                parts.append(f"\u00a7\n{content}\n")
                total += 1

    if parts:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        MEMORY_FILE.write_text("".join(parts), encoding="utf-8")
        logger.info("Synced %d Core Memory entries to %s", total, MEMORY_FILE)

    return total
