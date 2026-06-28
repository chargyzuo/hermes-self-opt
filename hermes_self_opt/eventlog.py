"""
eventlog.py — 统一查看 self-opt 所有事件日志（Phase 4 补充模块）。

数据源：
  - ~/.hermes/self-opt/change.log          skill/knowledge/memory 变动
  - ~/.hermes/self-opt/logs/*.json          Phase 1/3/4 运行日志
  - ~/.hermes/knowledge/self-opt/pipeline_watchdog.log  Phase 2 watchdog
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SELF_OPT_DIR = Path.home() / ".hermes" / "self-opt"
LOG_DIR = SELF_OPT_DIR / "logs"
CHANGE_LOG = SELF_OPT_DIR / "change.log"
WATCHDOG_LOG = Path.home() / ".hermes" / "knowledge" / "self-opt" / "pipeline_watchdog.log"


# ── change.log 解析 ─────────────────────────────────────────────────

def _parse_change_log(days: int) -> List[Dict[str, Any]]:
    """解析 change.log，返回 skill/knowledge 变动事件列表。"""
    if not CHANGE_LOG.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events = []
    for line in CHANGE_LOG.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(" | ")
        if len(parts) < 4:
            continue
        ts_str = parts[0]
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts < cutoff:
            continue
        event = {
            "timestamp": ts_str,
            "target": parts[1],
            "action": parts[2],
            "name": parts[3],
            "source": "",
            "path": "",
            "detail": "",
        }
        for kv in parts[4:]:
            if "=" in kv:
                k, v = kv.split("=", 1)
                if k in ("source", "path", "detail"):
                    event[k] = v
        events.append(event)
    return events


# ── JSON 日志解析 ───────────────────────────────────────────────────

def _parse_json_logs(days: int) -> List[Dict[str, Any]]:
    """解析 logs/*.json，返回 cron 运行事件列表。"""
    if not LOG_DIR.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events = []
    for f in sorted(LOG_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue

        ts_str = data.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            continue
        if ts < cutoff:
            continue

        phase = data.get("phase", "pipeline")
        event = {"timestamp": ts_str, "target": "cron", "action": phase, "name": phase, "detail": ""}

        if phase == "pipeline":
            event["name"] = "Phase1-pipeline"
            event["detail"] = f"session={data.get('session_id', '?')[:24]}"
        elif phase == "distill":
            event["name"] = "Phase3-distill"
            event["detail"] = f"date={data.get('date','?')} entries={data.get('distilled_count',0)}"
        elif phase == "router-build":
            event["name"] = "Phase4-router"
            event["detail"] = f"indexed={data.get('indexed',0)} skipped={data.get('skipped',0)} ms={data.get('duration_ms',0)}"
        else:
            event["detail"] = json.dumps(data, default=str)[:120]
        events.append(event)
    return events


# ── watchdog.log 解析 ───────────────────────────────────────────────

def _parse_watchdog_log(days: int) -> List[Dict[str, Any]]:
    """解析 pipeline_watchdog.log。"""
    if not WATCHDOG_LOG.exists():
        return []
    cutoff = datetime.now() - timedelta(days=days)
    events = []
    pattern = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+(.*)")
    for line in WATCHDOG_LOG.read_text(encoding="utf-8").strip().split("\n"):
        m = pattern.match(line)
        if not m:
            continue
        try:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if ts < cutoff:
            continue
        msg = m.group(2)
        events.append({
            "timestamp": m.group(1),
            "target": "cron",
            "action": "watchdog",
            "name": "Phase2-watchdog",
            "source": "",
            "path": "",
            "detail": msg[:120],
        })
    return events


# ── 聚合查询 ───────────────────────────────────────────────────────

def query(
    target: str = "all",
    days: int = 7,
    limit: int = 50,
    json_output: bool = False,
) -> Dict[str, Any]:
    """查询 self-opt 事件。

    Args:
        target: "skill" | "knowledge" | "cron" | "all"
        days: 回溯天数
        limit: 最大返回条数
        json_output: 返回 JSON

    Returns:
        {"events": [...], "total": N}
    """
    all_events: List[Dict[str, Any]] = []

    if target in ("skill", "knowledge", "memory", "all"):
        changes = _parse_change_log(days)
        if target in ("skill", "knowledge", "memory"):
            changes = [e for e in changes if e["target"] == target]
        for e in changes:
            e["source"] = "change.log"
        all_events.extend(changes)

    if target in ("cron", "all"):
        all_events.extend(_parse_json_logs(days))
        all_events.extend(_parse_watchdog_log(days))

    # 按时间降序
    all_events.sort(key=lambda e: e["timestamp"], reverse=True)
    total = len(all_events)
    all_events = all_events[:limit]

    result = {"total": total, "shown": len(all_events), "events": all_events}

    if json_output:
        return result

    return result


def format_output(data: Dict[str, Any]) -> str:
    """格式化输出。"""
    events = data.get("events", [])
    total = data.get("total", 0)
    shown = data.get("shown", 0)

    if not events:
        return f"无事件（最近 {data.get('days', 7)} 天）"

    lines = [f"Self-Opt 事件日志 — 共 {total} 条（显示 {shown} 条）", "=" * 60]

    for e in events:
        ts = e["timestamp"][:19].replace("T", " ")
        target = e["target"]
        action = e["action"]
        name = e.get("name", "-")

        # 彩色标记
        if target == "skill":
            icon = "📋"
        elif target == "knowledge":
            icon = "📚"
        elif target == "memory":
            icon = "🧠"
        else:
            icon = "⏱"

        line = f"{icon} {ts} | {target}/{action} | {name}"
        detail = e.get("detail", "")
        if detail:
            line += f" | {detail}"
        lines.append(line)

    lines.append("=" * 60)
    lines.append(f"数据源: change.log + logs/*.json + pipeline_watchdog.log")
    return "\n".join(lines)
