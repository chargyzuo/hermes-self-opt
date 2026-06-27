"""
gate_full.py — Step 3: Gate-Full validation (Phase 2).

Four rigid checks before a YAML entity can enter core/:
  1. Schema validation — JSON Schema (oneOf for three types)
  2. Reference integrity — all links in full must resolve
  3. Branch completeness — every flow step must have on_true AND on_false
  4. DFS cycle detection — no cycles between full documents via redirect
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path.home() / ".hermes" / "knowledge"
STAGING_DIR = KNOWLEDGE_DIR / "self-opt" / "staging"
CORE_DIR = KNOWLEDGE_DIR / "core"

# ── JSON Schema definitions for three types ────────────────────────

CHECK_SOURCE_SCHEMA = {
    "type": "object",
    "required": ["id", "type", "description", "device_type", "tags", "source"],
    "properties": {
        "id": {"type": "string", "pattern": "^check-"},
        "type": {"const": "check_source"},
        "description": {"type": "string", "minLength": 10},
        "command": {"type": "string"},
        "device_type": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "source": {"type": "string"},
        "added": {"type": "string", "format": "date"},
        "revised": {"type": "array", "items": {"type": "string"}},
    },
}

DECISION_SOURCE_SCHEMA = {
    "type": "object",
    "required": ["id", "type", "description", "tags", "confidence", "source"],
    "properties": {
        "id": {"type": "string", "pattern": "^decision-"},
        "type": {"const": "decision_source"},
        "description": {"type": "string", "minLength": 10},
        "action": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "confidence": {"enum": ["high", "medium", "low"]},
        "source": {"type": "string"},
        "added": {"type": "string", "format": "date"},
        "revised": {"type": "array", "items": {"type": "string"}},
    },
}

FULL_SCHEMA = {
    "type": "object",
    "required": ["id", "type", "tags", "triggers", "flow"],
    "properties": {
        "id": {"type": "string"},
        "type": {"const": "full"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "confidence": {"enum": ["high", "medium", "low"]},
        "source": {"type": "string"},
        "triggers": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "flow": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["step", "check"],
                "properties": {
                    "step": {"type": "integer", "minimum": 1},
                    "check": {"type": "string"},
                    "on_true": {"type": "object"},
                    "on_false": {"type": "object"},
                },
            },
        },
        "added": {"type": "string", "format": "date"},
        "revised": {"type": "array", "items": {"type": "string"}},
        "corrections": {"type": "array"},
    },
}

# Combined schema using oneOf
COMBINED_SCHEMA = {
    "oneOf": [
        CHECK_SOURCE_SCHEMA,
        DECISION_SOURCE_SCHEMA,
        FULL_SCHEMA,
    ],
}


# ── ValidationError ────────────────────────────────────────────────

class ValidationError(Exception):
    """Gate-Full validation error with details."""
    def __init__(self, message: str, check: str = "", path: str = ""):
        super().__init__(message)
        self.check_name = check
        self.file_path = path


# ── Schema validation ──────────────────────────────────────────────

def _validate_schema_jsonschema(data: Dict[str, Any]) -> List[str]:
    """Validate against JSON Schema using jsonschema if available."""
    errors: List[str] = []
    try:
        from jsonschema import validate, ValidationError as JSE
    except ImportError:
        return _validate_schema_manual(data)  # fallback

    try:
        validate(instance=data, schema=COMBINED_SCHEMA)
    except JSE as e:
        errors.append(f"Schema: {e.message} (path: {'/'.join(str(p) for p in e.absolute_path)})")
    return errors


def _validate_schema_manual(data: Dict[str, Any]) -> List[str]:
    """Manual schema validation (no deps)."""
    errors: List[str] = []
    ytype = data.get("type", "")
    yid = data.get("id", "?")

    if ytype == "check_source":
        schema = CHECK_SOURCE_SCHEMA
    elif ytype == "decision_source":
        schema = DECISION_SOURCE_SCHEMA
    elif ytype == "full":
        schema = FULL_SCHEMA
    else:
        errors.append(f"Schema: unknown type '{ytype}' in {yid}")
        return errors

    # Required fields
    for field in schema.get("required", []):
        if field not in data or data[field] is None:
            errors.append(f"Schema: {yid} missing required field '{field}'")

    # Type-specific patterns
    if ytype == "check_source":
        if not yid.startswith("check-"):
            errors.append(f"Schema: {yid} must start with 'check-'")
    elif ytype == "decision_source":
        if not yid.startswith("decision-"):
            errors.append(f"Schema: {yid} must start with 'decision-'")
    elif ytype == "full":
        flow = data.get("flow", [])
        if not isinstance(flow, list) or len(flow) == 0:
            errors.append(f"Schema: {yid} flow must be non-empty list")

        for step_item in flow:
            if not isinstance(step_item, dict):
                errors.append(f"Schema: {yid} flow item must be object")
                continue
            if "step" not in step_item:
                errors.append(f"Schema: {yid} flow item missing 'step'")
            if "check" not in step_item:
                errors.append(f"Schema: {yid} flow item missing 'check'")

    return errors


# ── Reference integrity ────────────────────────────────────────────

def _collect_all_ids(staging_dir: Path) -> Tuple[Set[str], Set[str], Set[str]]:
    """Collect all known IDs from staging + core.

    Returns:
        (check_source_ids, decision_source_ids, full_ids)
    """
    check_ids: Set[str] = set()
    decision_ids: Set[str] = set()
    full_ids: Set[str] = set()

    # staging/
    for f in staging_dir.rglob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                continue
            yid = data.get("id", "")
            ytype = data.get("type", "")
            if ytype == "check_source":
                check_ids.add(yid)
            elif ytype == "decision_source":
                decision_ids.add(yid)
            elif ytype == "full":
                full_ids.add(yid)
        except Exception:
            pass

    # core/
    for f in CORE_DIR.glob("check-source/*.yaml"):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("type") == "check_source":
                check_ids.add(data["id"])
        except Exception:
            pass
    for f in CORE_DIR.glob("decision-source/*.yaml"):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("type") == "decision_source":
                decision_ids.add(data["id"])
        except Exception:
            pass
    for f in CORE_DIR.glob("*.yaml"):
        if "check-source" in str(f) or "decision-source" in str(f):
            continue
        if f.name.startswith("_"):
            continue
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("type") == "full":
                full_ids.add(data["id"])
        except Exception:
            pass

    return check_ids, decision_ids, full_ids


def _check_reference_integrity(
    data: Dict[str, Any],
    check_ids: Set[str],
    decision_ids: Set[str],
    full_ids: Set[str],
) -> List[str]:
    """Verify all references in a full document resolve."""
    errors: List[str] = []
    ytype = data.get("type", "")
    yid = data.get("id", "?")

    if ytype != "full":
        return errors

    flow = data.get("flow", [])
    for step_item in flow:
        check_ref = step_item.get("check", "")
        if check_ref and check_ref not in check_ids:
            errors.append(f"Ref: {yid} step {step_item.get('step', '?')} "
                          f"references unknown check_source '{check_ref}'")

        for branch_key in ("on_true", "on_false"):
            branch = step_item.get(branch_key, {})
            if not isinstance(branch, dict):
                continue
            for link_type, link_target in branch.items():
                if link_type == "next_check" and link_target not in check_ids:
                    errors.append(f"Ref: {yid} step {step_item.get('step', '?')} "
                                  f"{branch_key}.next_check '{link_target}' not found")
                elif link_type == "decision" and link_target not in decision_ids:
                    errors.append(f"Ref: {yid} step {step_item.get('step', '?')} "
                                  f"{branch_key}.decision '{link_target}' not found")
                elif link_type == "redirect" and link_target not in full_ids:
                    errors.append(f"Ref: {yid} step {step_item.get('step', '?')} "
                                  f"{branch_key}.redirect '{link_target}' not found")

    return errors


# ── Branch completeness ────────────────────────────────────────────

def _check_branch_completeness(data: Dict[str, Any]) -> List[str]:
    """Verify every flow step has on_true and on_false fields (may be empty = terminal)."""
    errors: List[str] = []
    ytype = data.get("type", "")
    yid = data.get("id", "?")

    if ytype != "full":
        return errors

    flow = data.get("flow", [])
    for step_item in flow:
        step_num = step_item.get("step", "?")
        on_true = step_item.get("on_true")
        on_false = step_item.get("on_false")

        if on_true is None:
            errors.append(f"Branch: {yid} step {step_num} missing on_true field")
        if on_false is None:
            errors.append(f"Branch: {yid} step {step_num} missing on_false field")

    return errors


# ── DFS cycle detection ────────────────────────────────────────────

def _detect_cycles(full_docs: List[Dict[str, Any]]) -> List[str]:
    """Detect cycles between full documents via redirect links using DFS three-color algorithm.

    White (0) = unvisited, Gray (1) = in stack (back edge = cycle), Black (2) = fully processed.
    """
    # Build adjacency graph: full_id → set of redirect targets
    graph: Dict[str, Set[str]] = {}
    all_ids: Set[str] = set()

    for doc in full_docs:
        fid = doc["id"]
        all_ids.add(fid)
        graph.setdefault(fid, set())

        flow = doc.get("flow", [])
        for step_item in flow:
            for branch_key in ("on_true", "on_false"):
                branch = step_item.get(branch_key, {})
                if isinstance(branch, dict):
                    redirect = branch.get("redirect")
                    if redirect and redirect in all_ids.union({d["id"] for d in full_docs}):
                        graph[fid].add(redirect)

    # Three-color DFS
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {nid: WHITE for nid in graph}
    errors: List[str] = []

    def dfs(node: str, path: List[str]) -> None:
        color[node] = GRAY
        path.append(node)
        for neighbor in graph.get(node, set()):
            if color.get(neighbor) == GRAY:
                cycle_start = path.index(neighbor)
                cycle_path = " → ".join(path[cycle_start:] + [neighbor])
                errors.append(f"Cycle: {node} redirects to {neighbor}, cycle: {cycle_path}")
            elif color.get(neighbor) == WHITE:
                dfs(neighbor, path)
        path.pop()
        color[node] = BLACK

    for nid in list(graph.keys()):
        if color.get(nid) == WHITE:
            dfs(nid, [])

    return errors


# ── Main gate function ─────────────────────────────────────────────

def run_gate_checks(
    staging_dir: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run all four Gate-Full checks against staging/ YAML files.

    Args:
        staging_dir: override staging/ path
        verbose: print per-file results

    Returns:
        {
            "passed": int,
            "failed": int,
            "errors": [{"file": str, "check": str, "message": str}],
            "all_passed": bool,
        }
    """
    root = Path(staging_dir) if staging_dir else STAGING_DIR
    if not root.exists():
        logger.warning("staging/ not found: %s", root)
        return {"passed": 0, "failed": 0, "errors": [], "all_passed": False}

    # Collect all IDs for reference integrity check
    check_ids, decision_ids, full_ids = _collect_all_ids(root)

    all_errors: List[Dict[str, str]] = []
    passed = 0
    failed = 0

    # Load all full docs for DFS (also load individual files below)
    all_full_docs: List[Dict[str, Any]] = []

    yaml_files = sorted(root.rglob("*.yaml"))
    if not yaml_files:
        logger.warning("No YAML files found in staging/")
        return {"passed": 0, "failed": 1, "errors": [
            {"file": str(root), "check": "files", "message": "No YAML files in staging/"}
        ], "all_passed": False}

    for yf in yaml_files:
        try:
            data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                all_errors.append({"file": str(yf), "check": "parse", "message": "Not a YAML dict"})
                failed += 1
                continue
        except yaml.YAMLError as e:
            all_errors.append({"file": str(yf), "check": "parse", "message": str(e)})
            failed += 1
            continue

        if data.get("type") == "full":
            all_full_docs.append(data)

        file_errors: List[str] = []

        # 1. Schema
        schema_errs = _validate_schema_jsonschema(data)
        file_errors.extend(schema_errs)

        # 2. Reference integrity (full only)
        ref_errs = _check_reference_integrity(data, check_ids, decision_ids, full_ids)
        file_errors.extend(ref_errs)

        # 3. Branch completeness (full only)
        branch_errs = _check_branch_completeness(data)
        file_errors.extend(branch_errs)

        if file_errors:
            for err in file_errors:
                all_errors.append({"file": yf.name, "check": "gate", "message": err})
            failed += 1
            if verbose:
                print(f"❌ {yf.name}: {len(file_errors)} error(s)")
                for e in file_errors:
                    print(f"   {e}")
        else:
            passed += 1
            if verbose:
                print(f"✅ {yf.name}")

    # 4. DFS cycle detection (runs once across all full docs)
    cycle_errs = _detect_cycles(all_full_docs)
    for err in cycle_errs:
        all_errors.append({"file": "full/*.yaml", "check": "cycle", "message": err})
        failed += 1

    all_passed = len(all_errors) == 0 and passed > 0

    logger.info("Gate-Full: %d passed, %d failed, %d errors", passed, failed, len(all_errors))

    return {
        "passed": passed,
        "failed": failed,
        "errors": all_errors,
        "all_passed": all_passed,
    }


# ── LLM Judge (P1-4) ────────────────────────────────────────────────

KNOWLEDGE_JUDGE_PROMPT = """你是一个网络排障知识库评审员。以下是一个知识库条目（full 类型排障流程）和 Benchmark 题库。

## 知识库条目（YAML 排障流程）
{knowledge_yaml}

## Benchmark 题库（每条都包含：问题 + 必要步骤 + 红线）
{benchmark}

## 评分标准

1. 匹配 (matched_benchmark): 知识库条目与哪条 Benchmark 最相关？返回 benchmark id 或 null。
2. 步骤覆盖 (coverage_score, 0-5): 知识库条目是否覆盖了 Benchmark 指定的必要步骤。
   - 0-1 = 基本不相关或漏掉大部分步骤
   - 2-3 = 覆盖了部分步骤但缺关键环节
   - 4-5 = 完整覆盖或超额覆盖
3. 红线检查 (redline_pass, true/false): 知识库条目是否包含红线操作？
   注意：除了 Benchmark 列出的红线，也要警惕跳过必经步骤的明显错误。

## 输出格式（严格 JSON）
```json
{{
  "matched_benchmark": "bench-001 或 null",
  "coverage_score": 0,
  "redline_pass": true,
  "reason": "简要说明"
}}
```"""


def _load_benchmark_for_judge(benchmark_path: Optional[str] = None) -> str:
    """加载 Benchmark 题库，返回格式化的 LLM prompt 文本。

    复用 gate.py 的逻辑，但独立实现避免循环导入。
    """
    import json as _json

    if benchmark_path:
        path = Path(benchmark_path)
    else:
        path = KNOWLEDGE_DIR / "self-opt" / "benchmark.json"

    if not path.exists():
        logger.info("Benchmark not found at %s, skipping LLM Judge", path)
        return ""

    try:
        data = _json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or len(data) == 0:
            return ""

        parts = []
        for item in data:
            bid = item.get("id", "?")
            question = item.get("question", "")
            required = item.get("required_steps", [])
            redlines = item.get("redlines", [])

            parts.append(f"## {bid}: {question}")
            parts.append("必要步骤:")
            for s in required:
                parts.append(f"  - {s}")
            parts.append("红线:")
            for r in redlines:
                parts.append(f"  - {r}")
            parts.append("")

        return "\n".join(parts)
    except Exception as e:
        logger.warning("Failed to load benchmark: %s", e)
        return ""


def _run_llm_judge_for_doc(
    data: Dict[str, Any],
    benchmark_text: str,
    auxiliary_client=None,
) -> Dict[str, Any]:
    """对单个知识库条目做 LLM Judge 评分。

    Args:
        data: full 类型 YAML 数据
        benchmark_text: 格式化的 benchmark 文本
        auxiliary_client: Hermes auxiliary LLM client

    Returns:
        {"id": str, "matched_benchmark": str|null, "coverage_score": int,
         "redline_pass": bool, "reason": str, "error": str|null}
    """
    yaml_id = data.get("id", "?")

    # 只对 full 类型评分
    if data.get("type") != "full":
        return {
            "id": yaml_id,
            "matched_benchmark": None,
            "coverage_score": 3,
            "redline_pass": True,
            "reason": "非 full 类型，跳过",
            "error": None,
        }

    # 生成可读的 YAML 摘要
    summary_parts = []
    summary_parts.append(f"id: {yaml_id}")
    summary_parts.append(f"tags: {data.get('tags', [])}")
    triggers = data.get("triggers", [])
    if triggers:
        summary_parts.append(f"触发条件: {triggers[0][:200]}")
    summary_parts.append("排障步骤:")
    for step in data.get("flow", []):
        step_num = step.get("step", "?")
        check_id = step.get("check", "?")
        on_true = step.get("on_true", {})
        on_false = step.get("on_false", {})
        summary_parts.append(f"  step {step_num}: check={check_id}")
        if on_true:
            summary_parts.append(f"    on_true: {on_true}")
        if on_false:
            summary_parts.append(f"    on_false: {on_false}")

    knowledge_yaml = "\n".join(summary_parts[:60])  # 限制长度

    prompt = KNOWLEDGE_JUDGE_PROMPT.format(
        knowledge_yaml=knowledge_yaml,
        benchmark=benchmark_text,
    )

    if auxiliary_client is None:
        try:
            from agent.auxiliary_client import call_llm
            auxiliary_client = call_llm
        except ImportError:
            return {
                "id": yaml_id, "matched_benchmark": None,
                "coverage_score": 3, "redline_pass": True,
                "reason": "无法加载 LLM client",
                "error": "auxiliary_client unavailable",
            }

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
            return {
                "id": yaml_id, "matched_benchmark": None,
                "coverage_score": 3, "redline_pass": True,
                "reason": "LLM 返回空",
                "error": None,
            }

        # 尝试解析 JSON
        try:
            result = _json.loads(response_text)
        except (_json.JSONDecodeError, ValueError):
            fixed = _re.sub(r'\\(?!["\\/bfnrtu])', '\\\\\\\\', response_text)
            try:
                result = _json.loads(fixed)
            except Exception:
                return {
                    "id": yaml_id, "matched_benchmark": None,
                    "coverage_score": 3, "redline_pass": True,
                    "reason": f"JSON 解析失败: {response_text[:100]}",
                    "error": "parse_failed",
                }

        return {
            "id": yaml_id,
            "matched_benchmark": result.get("matched_benchmark"),
            "coverage_score": result.get("coverage_score", 3),
            "redline_pass": result.get("redline_pass", True),
            "reason": result.get("reason", ""),
            "error": None,
        }

    except Exception as e:
        logger.warning("LLM Judge failed for %s: %s", yaml_id, e)
        return {
            "id": yaml_id, "matched_benchmark": None,
            "coverage_score": 3, "redline_pass": True,
            "reason": f"调用失败: {e}",
            "error": str(e),
        }


def run_llm_judge(
    benchmark_path: Optional[str] = None,
    staging_dir: Optional[Path] = None,
    auxiliary_client=None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """对所有 staging/ 中的 full 文档做 LLM Judge 评分。

    这是 Gate-Full 的可选第 5 步。评分结果仅供参考，不阻塞 commit。

    Returns:
        {
            "total": int,
            "results": [{id, matched_benchmark, coverage_score, redline_pass, reason}, ...],
            "summary": {"avg_score": float, "redline_fails": int, "top_match": str},
        }
    """
    benchmark_text = _load_benchmark_for_judge(benchmark_path)
    if not benchmark_text:
        return {"total": 0, "results": [], "summary": {}, "error": "No benchmark available"}

    root = staging_dir or STAGING_DIR
    if not root.exists():
        return {"total": 0, "results": [], "summary": {}, "error": "staging/ not found"}

    results = []
    for yf in sorted(root.glob("*.yaml")):
        try:
            data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict) or data.get("type") != "full":
                continue

            if verbose:
                print(f"  Judge: {yf.name} ...")

            r = _run_llm_judge_for_doc(data, benchmark_text, auxiliary_client)
            results.append(r)
        except Exception as e:
            logger.warning("Skipping %s: %s", yf.name, e)

    # Summary
    if results:
        avg = sum(r["coverage_score"] for r in results) / len(results)
        red_fails = sum(1 for r in results if not r["redline_pass"])
        top = max(results, key=lambda r: r["coverage_score"])
        summary = {"avg_score": round(avg, 1), "redline_fails": red_fails,
                    "top_match": top["id"]}
    else:
        summary = {}

    return {"total": len(results), "results": results, "summary": summary}


# ── Schema export ───────────────────────────────────────────────────

def export_schema(dry_run: bool = False) -> Dict[str, Any]:
    """Export combined JSON Schema to core/_schema.yaml.

    Kept in sync with the in-code schema definitions so external
    consumers (CLI, cron, other agents) can reference a single
    authoritative schema file.

    Returns:
        {"written": bool, "path": str, "schema_version": str}
    """
    import json
    from datetime import datetime

    schema_doc = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Hermes Knowledge Base v4 — Three-Type Atomic Schema",
        "description": (
            "Defines the three core knowledge types: check_source (reusable "
            "check atom), decision_source (reusable conclusion atom), and "
            "full (routing graph linking atoms)."
        ),
        "version": "1.0.0",
        "exported_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "definitions": {
            "check_source": CHECK_SOURCE_SCHEMA,
            "decision_source": DECISION_SOURCE_SCHEMA,
            "full": FULL_SCHEMA,
        },
        **COMBINED_SCHEMA,  # oneOf
    }

    dest = CORE_DIR / "_schema.yaml"

    if dry_run:
        return {
            "written": False,
            "path": str(dest),
            "schema_version": schema_doc["version"],
            "lines": len(yaml.dump(schema_doc, allow_unicode=True).splitlines()),
        }

    CORE_DIR.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        yaml.dump(schema_doc, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    logger.info("Schema exported to %s", dest)

    return {
        "written": True,
        "path": str(dest),
        "schema_version": schema_doc["version"],
    }
