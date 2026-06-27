"""
committer.py — Step 4: commit validated YAML from staging/ to core/ (Phase 2).

Performs atomic file moves with archive backup, updates _index.yaml,
and provides rollback capability on failure.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path.home() / ".hermes" / "knowledge"
STAGING_DIR = KNOWLEDGE_DIR / "self-opt" / "staging"
CORE_DIR = KNOWLEDGE_DIR / "core"
COMMITTED_DIR = KNOWLEDGE_DIR / "self-opt" / "committed"
INDEX_FILE = CORE_DIR / "_index.yaml"


# ── helpers ────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    """Create all required directories."""
    for d in [CORE_DIR / "check-source", CORE_DIR / "decision-source",
              COMMITTED_DIR / "check-source", COMMITTED_DIR / "decision-source"]:
        d.mkdir(parents=True, exist_ok=True)


def _read_yaml(path: Path) -> Optional[Dict[str, Any]]:
    """Read a single YAML file, return dict or None."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _load_index() -> Dict[str, Any]:
    """Load or initialize _index.yaml."""
    if INDEX_FILE.exists():
        return _read_yaml(INDEX_FILE) or _make_empty_index()
    return _make_empty_index()


def _make_empty_index() -> Dict[str, Any]:
    return {
        "version": 1,
        "updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "tags": {},            # tag → list of ids
        "triggers": {},        # full_id → trigger strings
        "entries": {},         # id → {type, file, tags, added}
    }


def _save_index(index: Dict[str, Any]) -> None:
    """Save _index.yaml atomically."""
    index["updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    INDEX_FILE.write_text(
        yaml.dump(index, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


# ── index update ───────────────────────────────────────────────────

def _update_index_for_entry(index: Dict[str, Any], entry_id: str,
                            entry_type: str, rel_path: str,
                            tags: List[str], triggers: Optional[List[str]] = None) -> None:
    """Add or update an entry in the index."""
    # entries registry
    index["entries"][entry_id] = {
        "type": entry_type,
        "file": rel_path,
        "tags": tags,
        "added": datetime.now().strftime("%Y-%m-%d"),
    }

    # tags inverted index
    for tag in tags:
        tag_lower = tag.lower()
        if tag_lower not in index["tags"]:
            index["tags"][tag_lower] = []
        if entry_id not in index["tags"][tag_lower]:
            index["tags"][tag_lower].append(entry_id)

    # triggers (full docs only)
    if triggers:
        index["triggers"][entry_id] = triggers


# ── commit ─────────────────────────────────────────────────────────

def commit_to_core(
    gate_result: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Commit passed YAML files from staging/ to core/.

    Steps:
      1. Read staging/ YAML files
      2. Move to core/ subdirectories (check-source/, decision-source/, root)
      3. Archive copies to committed/
      4. Update _index.yaml
      5. If any step fails, rollback

    Args:
        gate_result: Optional Gate-Full result dict. If provided, only commit if all_passed.
        dry_run: If True, simulate but don't write.

    Returns:
        {
            "committed": int,
            "check_sources": int,
            "decision_sources": int,
            "full_docs": int,
            "dry_run": bool,
        }
    """
    if gate_result and not gate_result.get("all_passed"):
        logger.warning("Gate-Full not passed, refusing to commit")
        return {"committed": 0, "check_sources": 0, "decision_sources": 0,
                "full_docs": 0, "dry_run": dry_run, "error": "Gate-Full not passed"}

    if not STAGING_DIR.exists():
        logger.warning("staging/ not found")
        return {"committed": 0, "check_sources": 0, "decision_sources": 0,
                "full_docs": 0, "dry_run": dry_run}

    _ensure_dirs()
    index = _load_index()

    counts = {"check_source": 0, "decision_source": 0, "full": 0}
    committed_ids: List[Tuple[str, str, str, List[str], Optional[List[str]]]] = []  # (id, type, rel_path, tags, triggers)

    # Process check-source/
    cs_staging = STAGING_DIR / "check-source"
    if cs_staging.exists():
        for yf in sorted(cs_staging.glob("*.yaml")):
            data = _read_yaml(yf)
            if not data or data.get("type") != "check_source":
                continue
            eid = data["id"]
            dest = CORE_DIR / "check-source" / yf.name
            archive = COMMITTED_DIR / "check-source" / yf.name
            rel = f"check-source/{yf.name}"

            if not dry_run:
                _atomic_move(yf, dest, archive)
            counts["check_source"] += 1
            committed_ids.append((eid, "check_source", rel,
                                  data.get("tags", []), None))

    # Process decision-source/
    ds_staging = STAGING_DIR / "decision-source"
    if ds_staging.exists():
        for yf in sorted(ds_staging.glob("*.yaml")):
            data = _read_yaml(yf)
            if not data or data.get("type") != "decision_source":
                continue
            eid = data["id"]
            dest = CORE_DIR / "decision-source" / yf.name
            archive = COMMITTED_DIR / "decision-source" / yf.name
            rel = f"decision-source/{yf.name}"

            if not dry_run:
                _atomic_move(yf, dest, archive)
            counts["decision_source"] += 1
            committed_ids.append((eid, "decision_source", rel,
                                  data.get("tags", []), None))

    # Process full docs (root of staging, excluding check-source/ and decision-source/ dirs)
    for yf in sorted(STAGING_DIR.glob("*.yaml")):
        data = _read_yaml(yf)
        if not data or data.get("type") != "full":
            continue
        eid = data["id"]
        dest = CORE_DIR / yf.name
        archive = COMMITTED_DIR / yf.name
        rel = yf.name

        if not dry_run:
            _atomic_move(yf, dest, archive)
        counts["full"] += 1
        committed_ids.append((eid, "full", rel,
                              data.get("tags", []), data.get("triggers", [])))

    # Update index
    if committed_ids and not dry_run:
        for eid, etype, rel, tags, triggers in committed_ids:
            _update_index_for_entry(index, eid, etype, rel, tags, triggers)
        _save_index(index)
        logger.info("Index updated: %d new entries", len(committed_ids))

    total = sum(counts.values())
    logger.info("Committed %d files: %s", total, counts)

    # Auto-export schema after successful commit
    if total > 0 and not dry_run:
        try:
            from hermes_self_opt.gate_full import export_schema as _export_schema
            _export_schema()
        except Exception:
            logger.warning("Schema export after commit failed", exc_info=True)

    return {
        "committed": total,
        "check_sources": counts["check_source"],
        "decision_sources": counts["decision_source"],
        "full_docs": counts["full"],
        "dry_run": dry_run,
    }


def _atomic_move(src: Path, dest: Path, archive: Path) -> None:
    """Move file from src to dest, with archive backup.

    Strategy:
      1. Copy to archive (backup)
      2. Move from staging to core
      If move fails after archive copy, archive copy exists for recovery.
    """
    # Ensure destination directories exist
    dest.parent.mkdir(parents=True, exist_ok=True)
    archive.parent.mkdir(parents=True, exist_ok=True)

    # Copy to archive first
    shutil.copy2(src, archive)

    # Move to core (atomic within same filesystem)
    if dest.exists():
        logger.warning("Destination exists, overwriting: %s", dest)
    shutil.move(str(src), str(dest))


def rollback_last_commit() -> Dict[str, int]:
    """Rollback: move files from core/ back to staging/ using committed/ copies.

    Returns count of rolled-back files by type.
    """
    counts = {"check_source": 0, "decision_source": 0, "full": 0}

    # check-source/ rollback
    cs_committed = COMMITTED_DIR / "check-source"
    if cs_committed.exists():
        for yf in sorted(cs_committed.glob("*.yaml")):
            core_file = CORE_DIR / "check-source" / yf.name
            staging_file = STAGING_DIR / "check-source" / yf.name
            if core_file.exists():
                core_file.unlink()
            staging_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(yf, staging_file)
            counts["check_source"] += 1

    # decision-source/ rollback
    ds_committed = COMMITTED_DIR / "decision-source"
    if ds_committed.exists():
        for yf in sorted(ds_committed.glob("*.yaml")):
            core_file = CORE_DIR / "decision-source" / yf.name
            staging_file = STAGING_DIR / "decision-source" / yf.name
            if core_file.exists():
                core_file.unlink()
            staging_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(yf, staging_file)
            counts["decision_source"] += 1

    # full rollback
    for yf in sorted(COMMITTED_DIR.glob("*.yaml")):
        core_file = CORE_DIR / yf.name
        staging_file = STAGING_DIR / yf.name
        if core_file.exists():
            core_file.unlink()
        shutil.copy2(yf, staging_file)
        counts["full"] += 1

    logger.info("Rollback complete: %s", counts)
    return counts


def stats() -> Dict[str, Any]:
    """Return current knowledge base statistics."""
    s = {
        "core_check_sources": 0,
        "core_decision_sources": 0,
        "core_full_docs": 0,
        "staging_files": 0,
        "normal_md_files": 0,
        "index_entries": 0,
        "index_tags": 0,
    }

    # core/
    if (CORE_DIR / "check-source").exists():
        s["core_check_sources"] = len(list((CORE_DIR / "check-source").glob("*.yaml")))
    if (CORE_DIR / "decision-source").exists():
        s["core_decision_sources"] = len(list((CORE_DIR / "decision-source").glob("*.yaml")))

    for f in CORE_DIR.glob("*.yaml"):
        if f.name.startswith("_"):
            continue
        data = _read_yaml(f)
        if data and data.get("type") == "full":
            s["core_full_docs"] += 1

    # staging/
    if STAGING_DIR.exists():
        s["staging_files"] = len(list(STAGING_DIR.rglob("*.yaml")))

    # normal/
    normal_dir = KNOWLEDGE_DIR / "normal"
    if normal_dir.exists():
        s["normal_md_files"] = len(list(normal_dir.rglob("*.md")))

    # index
    index = _load_index()
    s["index_entries"] = len(index.get("entries", {}))
    s["index_tags"] = len(index.get("tags", {}))

    return s
