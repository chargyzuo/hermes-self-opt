"""
distill_knowledge.py — Step 2: dedup + generate three-type YAML entities (Phase 2).

Takes extracted data from extractor.py, performs three-layer dedup,
generates check_source / decision_source / full YAML files,
and writes them to self-opt/staging/.

P2-6: confidence evaluation uses LLM (with heuristic fallback).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path.home() / ".hermes" / "knowledge"
STAGING_DIR = KNOWLEDGE_DIR / "self-opt" / "staging"
CORE_DIR = KNOWLEDGE_DIR / "core"


# ── LLM Confidence Evaluation Prompt ──────────────────────────────

CONFIDENCE_EVAL_PROMPT = """\
你是一个排障知识质量评估专家。评估以下排障知识的置信度 (confidence)。

评估标准:
- high:   根因分析清晰、有验证步骤、方案可复现。高质量排障文档。
- medium: 逻辑合理但缺少验证步骤或部分细节。可用的排障参考。
- low:    分析不完整、缺少关键步骤、或仅仅是现象描述。需进一步验证。

返回 JSON:
{"confidence": "high|medium|low", "reason": "简要理由(<200字)"}

待评估知识:
tags: {tags}
root_cause: {root_cause}
solution: {solution}
actions: {actions}

只返回 JSON，不要任何其他内容。"""


# ── helpers ────────────────────────────────────────────────────────

def _id_slug(text: str, prefix: str) -> str:
    """Generate a safe YAML id from text."""
    slug = re.sub(r"[^\w\-]+", "-", text.lower()).strip("-")[:60]
    return f"{prefix}-{slug}"


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _load_existing_yaml(glob_pattern: str) -> Dict[str, Dict[str, Any]]:
    """Load all existing YAML files matching a glob, keyed by id."""
    existing: Dict[str, Dict[str, Any]] = {}
    for f in CORE_DIR.glob(glob_pattern):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict) and "id" in data:
                existing[data["id"]] = data
        except Exception:
            pass
    return existing


def _semantic_similarity(a: str, b: str) -> float:
    """Approximate semantic similarity via SequenceMatcher (fast, no deps)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _tags_overlap(a: List[str], b: List[str]) -> int:
    """Count of overlapping tags (case-insensitive)."""
    sa = {t.lower() for t in a}
    sb = {t.lower() for t in b}
    return len(sa & sb)


# ── dedup ──────────────────────────────────────────────────────────

def _dedup_check_source(
    candidate: Dict[str, Any],
    existing: Dict[str, Dict[str, Any]],
) -> Optional[str]:
    """Check if a check_source candidate duplicates an existing one.

    Returns:
        None if unique, "exact" if precise match, "candidate_duplicate" if fuzzy match.
    """
    cid = candidate["id"]

    # Layer 1: exact id match
    if cid in existing:
        return "exact"

    # Layer 1b: command + device_type match
    for eid, e in existing.items():
        if (candidate.get("command") == e.get("command") and
                candidate.get("device_type") == e.get("device_type")):
            return "exact"

    # Layer 2: semantic similarity
    for eid, e in existing.items():
        sim = _semantic_similarity(
            candidate.get("description", ""),
            e.get("description", ""),
        )
        overlap = _tags_overlap(
            candidate.get("tags", []),
            e.get("tags", []),
        )
        if sim > 0.92 and overlap >= 2:
            return f"candidate_duplicate:{eid}"

    return None


def _dedup_decision_source(
    candidate: Dict[str, Any],
    existing: Dict[str, Dict[str, Any]],
) -> Optional[str]:
    """Dedup for decision_source (same logic, uses action instead of command)."""
    cid = candidate["id"]

    if cid in existing:
        return "exact"

    for eid, e in existing.items():
        if (candidate.get("action") == e.get("action") and
                candidate.get("confidence") == e.get("confidence")):
            return "exact"

    for eid, e in existing.items():
        sim = _semantic_similarity(
            candidate.get("description", ""),
            e.get("description", ""),
        )
        overlap = _tags_overlap(
            candidate.get("tags", []),
            e.get("tags", []),
        )
        if sim > 0.92 and overlap >= 2:
            return f"candidate_duplicate:{eid}"

    return None


# ── YAML generation ────────────────────────────────────────────────

def _evaluate_confidence_llm(
    root_cause: str,
    solution: str,
    actions: str,
    tags: List[str],
    auxiliary_client=None,
) -> Tuple[str, str]:
    """Use LLM to evaluate confidence of a decision_source.

    Falls back to heuristic if LLM is unavailable.

    Returns:
        (confidence: str, reason: str)
    """
    # Heuristic fallback (kept for when LLM unavailable)
    filled = sum(1 for v in [root_cause, solution, actions] if v)
    default_confidence = "high" if filled >= 3 else ("medium" if filled >= 2 else "low")

    if auxiliary_client is None:
        try:
            from agent.auxiliary_client import call_llm
            auxiliary_client = call_llm
        except ImportError:
            return default_confidence, "heuristic (no LLM client)"

    prompt = CONFIDENCE_EVAL_PROMPT.format(
        tags=", ".join(tags[:8]) if tags else "(none)",
        root_cause=root_cause[:500] or "(none)",
        solution=solution[:500] or "(none)",
        actions=actions[:500] or "(none)",
    )

    try:
        import json as _json
        import re as _re

        messages = [{"role": "user", "content": prompt}]
        response = auxiliary_client(task="default", messages=messages)

        if hasattr(response, "choices"):
            response_text = response.choices[0].message.content or ""
        elif isinstance(response, dict):
            response_text = response.get("content", "") or response.get("text", "")
        else:
            response_text = str(response)

        if not response_text.strip():
            return default_confidence, "LLM returned empty, used heuristic"

        # Parse JSON
        try:
            result = _json.loads(response_text)
        except (_json.JSONDecodeError, ValueError):
            # Try extracting JSON block
            m = _re.search(r'\{[^{}]*"confidence"[^{}]*\}', response_text, _re.DOTALL)
            if m:
                try:
                    result = _json.loads(m.group())
                except Exception:
                    return default_confidence, f"JSON parse failed: {response_text[:80]}"
            else:
                return default_confidence, f"JSON parse failed: {response_text[:80]}"

        conf = result.get("confidence", default_confidence)
        if conf not in ("high", "medium", "low"):
            conf = default_confidence
        reason = result.get("reason", "LLM evaluated")

        return conf, reason

    except Exception as e:
        logger.debug("LLM confidence eval failed: %s", e)
        return default_confidence, f"LLM error, used heuristic: {e}"


def _generate_check_source(extracted: Dict[str, Any], step_idx: int) -> Optional[Dict[str, Any]]:
    """Generate a check_source entry from a troubleshooting step.

    Each step in 排查路径 can become a check_source if it contains actionable commands.
    """
    # Try to extract a meaningful command from the troubleshooting text
    troubleshooting = extracted.get("sections", {}).get("troubleshooting", "")
    if not troubleshooting:
        return None

    # Split into numbered steps
    steps = re.split(r"\n?(?:\d+[\.\、\)）]\s*)", troubleshooting)
    steps = [s.strip() for s in steps if s.strip()]
    if step_idx >= len(steps):
        return None

    step_text = steps[step_idx]
    if len(step_text) < 20:
        return None

    # Extract commands from this step
    cmd_matches = re.findall(r"`([^`]+)`", step_text)
    command = cmd_matches[0] if cmd_matches else step_text[:120]

    # Build description from the step text
    desc = step_text[:200].strip()
    if len(step_text) > 200:
        desc += "..."

    tags = [t for t in extracted.get("tags", []) if isinstance(t, str)][:8]
    device_type = extracted.get("device_type", "general")

    check_id = _id_slug(f"{extracted['id']}-step{step_idx+1}", "check")

    return {
        "id": check_id,
        "type": "check_source",
        "description": desc,
        "command": command,
        "device_type": device_type,
        "tags": tags,
        "source": extracted.get("source", ""),
        "added": _today(),
        "revised": [],
    }


def _generate_decision_source(
    extracted: Dict[str, Any],
    auxiliary_client=None,
) -> Optional[Dict[str, Any]]:
    """Generate a decision_source from root cause + solution.

    Args:
        extracted: Output from extractor
        auxiliary_client: Optional LLM client for confidence evaluation.
                          If None, auto-loads from agent.auxiliary_client.
    """
    sections = extracted.get("sections", {})
    root_cause = sections.get("root_cause", "")
    solution = sections.get("solution", "")
    actions = sections.get("actions", "")

    if not root_cause and not solution:
        return None

    description = f"{root_cause} {solution}".strip()[:300]
    action_text = actions or solution or root_cause[:200]
    tags = [t for t in extracted.get("tags", []) if isinstance(t, str)][:8]
    dec_id = _id_slug(f"decision-{extracted['id']}", "decision")

    # LLM confidence evaluation (falls back to heuristic if unavailable)
    confidence, confidence_reason = _evaluate_confidence_llm(
        root_cause, solution, actions, tags, auxiliary_client,
    )

    return {
        "id": dec_id,
        "type": "decision_source",
        "description": description,
        "action": action_text,
        "tags": tags,
        "confidence": confidence,
        "source": extracted.get("source", ""),
        "added": _today(),
        "revised": [],
    }


def _generate_full(
    extracted: Dict[str, Any],
    check_ids: List[str],
    decision_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Generate a full routing diagram that links check_source and decision_source nodes."""
    if not check_ids and not decision_id:
        return None

    tags = [t for t in extracted.get("tags", []) if isinstance(t, str)][:8]
    symptoms = extracted.get("sections", {}).get("symptoms", "")
    triggers = [symptoms[:200]] if symptoms else []

    flow: List[Dict[str, Any]] = []
    for i, cid in enumerate(check_ids):
        step: Dict[str, Any] = {
            "step": i + 1,
            "check": cid,
        }
        # If this is the last check and we have a decision, route to it on_true
        is_last = (i == len(check_ids) - 1)
        if is_last and decision_id:
            step["on_true"] = {"decision": decision_id}
            step["on_false"] = {}  # terminal: check failed, no further path
        elif i + 1 < len(check_ids):
            step["on_true"] = {"next_check": check_ids[i + 1]}
            step["on_false"] = {}  # terminal: no known fallback
        else:
            step["on_true"] = {}  # terminal: last check, no decision
            step["on_false"] = {}
        flow.append(step)

    full_id = _id_slug(f"full-{extracted['id']}", "full")

    return {
        "id": full_id,
        "type": "full",
        "tags": tags,
        "confidence": "medium",
        "source": extracted.get("source", ""),
        "triggers": triggers,
        "flow": flow,
        "added": _today(),
        "revised": [],
        "corrections": [],
    }


# ── main pipeline ──────────────────────────────────────────────────

def distill_and_generate(
    extracted_list: List[Dict[str, Any]],
    dry_run: bool = False,
    auxiliary_client=None,
) -> Dict[str, Any]:
    """Run the full distill pipeline: dedup → generate → write staging.

    Args:
        extracted_list: Output from extractor.extract_all()
        dry_run: If True, don't write files, just return summary.
        auxiliary_client: Optional LLM client for confidence evaluation.

    Returns:
        {
            "total_files": int,
            "new_check_sources": int,
            "new_decision_sources": int,
            "new_full_docs": int,
            "duplicates_skipped": int,
            "staging_dir": str,
        }
    """
    # Load existing core entries for dedup
    existing_checks = _load_existing_yaml("check-source/*.yaml")
    existing_decisions = _load_existing_yaml("decision-source/*.yaml")
    existing_full = _load_existing_yaml("*.yaml")

    new_checks: List[Dict[str, Any]] = []
    new_decisions: List[Dict[str, Any]] = []
    new_full: List[Dict[str, Any]] = []
    duplicates = 0

    for extracted in extracted_list:
        # Generate check_sources from troubleshooting steps
        troubleshooting = extracted.get("sections", {}).get("troubleshooting", "")
        steps = re.split(r"\n?(?:\d+[\.\、\)）]\s*)", troubleshooting)
        steps = [s.strip() for s in steps if s.strip()]
        check_ids: List[str] = []

        for i in range(len(steps)):
            cs = _generate_check_source(extracted, i)
            if cs is None:
                continue

            dup_result = _dedup_check_source(cs, existing_checks)
            if dup_result == "exact":
                # Duplicate — do NOT add to flow (command already covered)
                duplicates += 1
                continue
            if dup_result and dup_result.startswith("candidate_duplicate"):
                # Flag as candidate but still generate for review
                cs["_dedup_note"] = dup_result

            new_checks.append(cs)
            existing_checks[cs["id"]] = cs  # add to in-memory for this batch
            check_ids.append(cs["id"])

        # Generate decision_source
        ds = _generate_decision_source(extracted, auxiliary_client=auxiliary_client)
        decision_id: Optional[str] = None
        if ds:
            dup_result = _dedup_decision_source(ds, existing_decisions)
            if dup_result == "exact":
                decision_id = ds["id"]
                duplicates += 1
            else:
                if dup_result and dup_result.startswith("candidate_duplicate"):
                    ds["_dedup_note"] = dup_result
                new_decisions.append(ds)
                existing_decisions[ds["id"]] = ds
                decision_id = ds["id"]

        # Generate full
        full = _generate_full(extracted, check_ids, decision_id)
        if full:
            fid = full["id"]
            if fid in existing_full:
                duplicates += 1
                continue
            new_full.append(full)
            existing_full[fid] = full

    # Write to staging
    if not dry_run:
        written = _write_staging(new_checks, new_decisions, new_full)
    else:
        written = 0

    logger.info(
        "Distill complete: %d docs → %d checks + %d decisions + %d full (%d dups skipped, %d written)",
        len(extracted_list),
        len(new_checks), len(new_decisions), len(new_full),
        duplicates, written,
    )

    return {
        "total_files": len(extracted_list),
        "new_check_sources": len(new_checks),
        "new_decision_sources": len(new_decisions),
        "new_full_docs": len(new_full),
        "duplicates_skipped": duplicates,
        "staging_dir": str(STAGING_DIR),
        "files_written": written,
    }


def _write_staging(
    checks: List[Dict[str, Any]],
    decisions: List[Dict[str, Any]],
    full_docs: List[Dict[str, Any]],
) -> int:
    """Write generated YAML entities to self-opt/staging/."""
    written = 0

    # check-source/
    cs_dir = STAGING_DIR / "check-source"
    cs_dir.mkdir(parents=True, exist_ok=True)
    for cs in checks:
        path = cs_dir / f"{cs['id']}.yaml"
        _write_yaml(path, cs)
        written += 1

    # decision-source/
    ds_dir = STAGING_DIR / "decision-source"
    ds_dir.mkdir(parents=True, exist_ok=True)
    for ds in decisions:
        path = ds_dir / f"{ds['id']}.yaml"
        _write_yaml(path, ds)
        written += 1

    # full (root of staging)
    root_dir = STAGING_DIR
    root_dir.mkdir(parents=True, exist_ok=True)
    for full in full_docs:
        path = root_dir / f"{full['id']}.yaml"
        _write_yaml(path, full)
        written += 1

    return written


def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
    """Write a YAML file with consistent formatting."""
    # remove internal metadata fields
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    path.write_text(
        yaml.dump(clean, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    logger.debug("Wrote: %s", path.name)
