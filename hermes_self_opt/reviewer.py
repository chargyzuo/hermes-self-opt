"""
reviewer.py — P0: staging/ review + commit gate (Phase 2).

Hard requirement: knowledge base writes MUST pass user approval.
This module provides:
  1. scan_staging() — snapshot staging/ contents for human review
  2. save_review_state() / load_review_state() — persist approval state
  3. staging_changed_since_review() — detect if staging was modified after review
  4. review_staging() — interactive CLI: show summary + ask y/n
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path.home() / ".hermes" / "knowledge"
STAGING_DIR = KNOWLEDGE_DIR / "self-opt" / "staging"
CORE_DIR = KNOWLEDGE_DIR / "core"
REVIEW_STATE_FILE = KNOWLEDGE_DIR / "self-opt" / ".review_state.json"


# ── scan staging ────────────────────────────────────────────────────

def _hash_file(path: Path) -> str:
    """SHA256 of file contents for change detection."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_yaml(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _exists_in_core(yaml_path: Path) -> bool:
    """Check if a staging YAML file already exists in core/ (same relative path)."""
    rel = yaml_path.relative_to(STAGING_DIR)
    core_path = CORE_DIR / rel
    return core_path.exists()


def _exists_in_core_by_id(entry_id: str, entry_type: str) -> Optional[Path]:
    """Check if an entry with this id already exists in core (any subdirectory)."""
    # check_source and decision_source go in subdirectories
    if entry_type in ("check_source", "decision_source"):
        subdir = CORE_DIR / entry_type.replace("_", "-")
        candidate = subdir / f"{entry_id}.yaml"
        if candidate.exists():
            return candidate
    # full docs at root
    candidate = CORE_DIR / f"{entry_id}.yaml"
    if candidate.exists():
        return candidate
    return None


def scan_staging() -> Dict[str, Any]:
    """Scan staging/ and return a structured summary for human review.

    Returns:
        {
            "total": int,
            "new": int,           # not in core
            "existing": int,      # already in core (id match)
            "files": [            # per-file details
                {
                    "path": "check-source/check-foo.yaml",
                    "type": "check_source",
                    "id": "check-foo",
                    "status": "new" | "existing",
                    "core_path": null | "core/check-source/check-foo.yaml",
                    "hash": "abc123",
                },
                ...
            ],
            "breakdown": {"check_source": int, "decision_source": int, "full": int},
            "timestamp": "2026-06-27T22:00:00",
        }
    """
    if not STAGING_DIR.exists():
        return {
            "total": 0, "new": 0, "existing": 0,
            "files": [],
            "breakdown": {"check_source": 0, "decision_source": 0, "full": 0},
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }

    files = []
    breakdown = {"check_source": 0, "decision_source": 0, "full": 0}
    new_count = 0
    existing_count = 0

    for yf in sorted(STAGING_DIR.rglob("*.yaml")):
        data = _read_yaml(yf)
        if not data:
            continue

        entry_type = data.get("type", "")
        if entry_type not in ("check_source", "decision_source", "full"):
            continue

        entry_id = data.get("id", "")
        rel = str(yf.relative_to(STAGING_DIR))

        core_match = _exists_in_core_by_id(entry_id, entry_type)
        status = "existing" if core_match else "new"

        file_info = {
            "path": rel,
            "type": entry_type,
            "id": entry_id,
            "status": status,
            "core_path": str(core_match.relative_to(CORE_DIR)) if core_match else None,
            "hash": _hash_file(yf),
        }
        files.append(file_info)

        if status == "new":
            new_count += 1
        else:
            existing_count += 1

        if entry_type == "check_source":
            breakdown["check_source"] += 1
        elif entry_type == "decision_source":
            breakdown["decision_source"] += 1
        else:
            breakdown["full"] += 1

    return {
        "total": len(files),
        "new": new_count,
        "existing": existing_count,
        "files": files,
        "breakdown": breakdown,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ── review state persistence ─────────────────────────────────────

def save_review_state(scan_result: Dict[str, Any], approved: bool) -> None:
    """Persist review state to .review_state.json.

    Stores: approved flag + staging snapshot (file list with hashes)
    so commit can verify staging hasn't changed since review.
    """
    state = {
        "approved": approved,
        "reviewed_at": scan_result["timestamp"],
        "snapshot": {
            "total": scan_result["total"],
            "files": [
                {"path": f["path"], "hash": f["hash"]}
                for f in scan_result["files"]
            ],
        },
    }
    REVIEW_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                                 encoding="utf-8")


def load_review_state() -> Optional[Dict[str, Any]]:
    """Load persisted review state, or None if no review has been done."""
    if not REVIEW_STATE_FILE.exists():
        return None
    try:
        return json.loads(REVIEW_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def staging_changed_since_review(review_state: Dict[str, Any]) -> bool:
    """Check if staging/ has been modified since the last review.

    Returns True if staging changed (need re-review), False if unchanged.
    """
    snapshot = review_state.get("snapshot", {})
    snapshot_files = snapshot.get("files", [])
    snapshot_hash_map = {f["path"]: f["hash"] for f in snapshot_files}

    current = scan_staging()
    current_files = current["files"]

    # Different file count = changed
    if len(current_files) != len(snapshot_files):
        return True

    # Check each file matches
    current_hash_map = {f["path"]: f["hash"] for f in current_files}

    for path, h in snapshot_hash_map.items():
        if current_hash_map.get(path) != h:
            return True

    return False


# ── interactive review ──────────────────────────────────────────────

def review_staging(scan_result: Optional[Dict[str, Any]] = None,
                   auto_approve: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """Interactive CLI: show staging summary and ask for approval.

    Args:
        scan_result: Pre-computed scan (optional). If None, runs scan_staging().
        auto_approve: If True, skip prompt and auto-approve (for --yes flag).

    Returns:
        (approved: bool, scan_result: dict)
    """
    if scan_result is None:
        scan_result = scan_staging()

    total = scan_result["total"]
    breakdown = scan_result["breakdown"]

    # ── Display summary ──
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           Staging Review — Knowledge Base Changes        ║")
    print("╠══════════════════════════════════════════════════════════╣")

    if total == 0:
        print("║  No files in staging. Nothing to review.                ║")
        print("╚══════════════════════════════════════════════════════════╝")
        return False, scan_result

    print(f"║  Total files:   {total:<3d}                                      ║")
    print(f"║    New:         {scan_result['new']:<3d}  (not in core)                         ║")
    print(f"║    Existing:    {scan_result['existing']:<3d}  (update existing)                  ║")
    print(f"║                                                          ║")
    print(f"║  Breakdown:                                              ║")
    print(f"║    check_source:   {breakdown['check_source']:<3d}                                ║")
    print(f"║    decision_source:{breakdown['decision_source']:<3d}                                ║")
    print(f"║    full:           {breakdown['full']:<3d}                                ║")
    print(f"╠══════════════════════════════════════════════════════════╣")

    # ── File list ──
    max_show = 30
    for i, f in enumerate(scan_result["files"]):
        if i >= max_show:
            remaining = total - max_show
            print(f"║  ... and {remaining} more files                            ║")
            break
        status_mark = "🆕" if f["status"] == "new" else "✏️ "
        path = f"  {status_mark} {f['path']}"
        # Truncate if too long for display
        if len(path) > 56:
            path = path[:53] + "..."
        print(f"║{path:<58}║")

    print("╚══════════════════════════════════════════════════════════╝")

    if auto_approve:
        print("\n✅ Auto-approved (--yes)")
        save_review_state(scan_result, approved=True)
        return True, scan_result

    # ── Ask for confirmation ──
    print()
    try:
        answer = input("Approve these changes and commit to core? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"

    approved = answer in ("y", "yes")
    save_review_state(scan_result, approved)

    if approved:
        print("✅ Approved. Ready to commit.")
    else:
        print("❌ Review rejected. Changes will NOT be committed.")

    return approved, scan_result
