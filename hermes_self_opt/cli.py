"""
cli.py — hermes self-opt CLI 子命令定义。

提供以下子命令：
  hermes self-opt harvest    --session-id <id>   测试 Harvest
  hermes self-opt mine       --session-id <id>   测试 Mine
  hermes self-opt run        [--session-id <id>] 全流程
                             [--days 1]
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Callable

logger = logging.getLogger(__name__)


def build_self_opt_parser(subparsers, *, cmd_self_opt: Callable) -> None:
    """注册 hermes self-opt 子命令。"""
    parser = subparsers.add_parser(
        "self-opt",
        help="Agent self-optimization: Harvest → Mine → Gate-Lite",
        description=(
            "Run the Agent Self-Optimization pipeline. "
            "Harvests recent sessions, mines them for knowledge/memory/skills, "
            "validates changes through Gate-Lite, and writes approved updates."
        ),
    )

    sub = parser.add_subparsers(dest="self_opt_command")

    # harvest
    harvest_parser = sub.add_parser("harvest", help="Test Harvest: read session dialog")
    harvest_parser.add_argument("--session-id", required=True, help="Session ID to harvest")

    # mine
    mine_parser = sub.add_parser("mine", help="Test Mine: extract from session dialog")
    mine_parser.add_argument("--session-id", required=True, help="Session ID to mine")
    mine_parser.add_argument("--model", help="LLM model override")

    # gate
    gate_parser = sub.add_parser("gate", help="Test Gate-Lite: validate a skill file")
    gate_parser.add_argument("--skill-file", required=True, help="Path to SKILL.md to validate")
    gate_parser.add_argument("--benchmark", help="Path to benchmark JSON")

    # distill
    distill_parser = sub.add_parser("distill", help="Phase 3: distill daily → core memory")
    distill_parser.add_argument("--date", help="Date to distill (default: today)")
    distill_parser.add_argument("--cleanup", action="store_true", help="Clean old daily files after")

    # memory
    mem_parser = sub.add_parser("memory", help="Show Core Memory stats")
    mem_parser.add_argument("--show", action="store_true", help="Show full Core Memory content")

    # router
    router_parser = sub.add_parser("router", help="Skill router: build/query/stats/gap/rewrite/rollback")
    router_sub = router_parser.add_subparsers(dest="router_command")
    router_sub.add_parser("build", help="Rebuild FTS5 skill index")
    rq = router_sub.add_parser("query", help="Query the skill index")
    rq.add_argument("query_text", help="Search phrase")
    router_sub.add_parser("stats", help="Router statistics")
    rg = router_sub.add_parser("gap", help="Check description gaps for a skill")
    rg.add_argument("skill_name", help="Skill name to check")
    rw = router_sub.add_parser("rewrite", help="Rewrite skill description (LLM)")
    rw.add_argument("skill_name", help="Skill name to rewrite")
    rw.add_argument("--dry-run", action="store_true", help="Preview only, don't write")
    rb = router_sub.add_parser("rollback", help="Rollback skill to last backup")
    rb.add_argument("skill_name", help="Skill name to rollback")

    # ── Phase 2: Knowledge pipeline ──

    # extract
    extract_parser = sub.add_parser("extract", help="Phase 2: extract normal/ MD → structured data")
    extract_parser.add_argument("--json", action="store_true", help="Output as JSON")
    extract_parser.add_argument("--file", help="Extract a single MD file instead of all")

    # distill-knowledge
    dk_parser = sub.add_parser("distill-knowledge", help="Phase 2: dedup + generate YAML → staging/")
    dk_parser.add_argument("--dry-run", action="store_true", help="Simulate, don't write files")

    # gate-full
    gf_parser = sub.add_parser("gate-full", help="Phase 2: four-rigid checks on staging/")
    gf_parser.add_argument("--verbose", action="store_true", help="Print per-file results")

    # review (P0)
    rv_parser = sub.add_parser("review", help="Phase 2: review staging changes before commit")
    rv_parser.add_argument("--yes", "-y", action="store_true", help="Auto-approve (skip prompt)")

    # commit
    cm_parser = sub.add_parser("commit", help="Phase 2: commit passed YAML from staging → core")
    cm_parser.add_argument("--dry-run", action="store_true", help="Simulate, don't move files")
    cm_parser.add_argument("--skip-gate", action="store_true", help="Skip Gate-Full, commit directly")
    cm_parser.add_argument("--skip-review", action="store_true", help="Skip review requirement")

    # knowledge stats
    ks_parser = sub.add_parser("knowledge", help="Phase 2: knowledge base statistics")

    # run
    run_parser = sub.add_parser("run", help="Run full self-opt pipeline")
    run_parser.add_argument("--session-id", help="Single session to process")
    run_parser.add_argument("--days", type=int, default=1, help="Days of history to process")
    run_parser.add_argument("--benchmark", help="Path to benchmark JSON")
    run_parser.add_argument("--overwrite-skill", action="store_true", help="Overwrite existing skills")
    run_parser.add_argument("--json", action="store_true", help="Output as JSON")

    for p in [harvest_parser, mine_parser, run_parser, distill_parser, mem_parser,
              router_parser, extract_parser, dk_parser, gf_parser, rv_parser, cm_parser, ks_parser]:
        p.set_defaults(func=cmd_self_opt)
    gate_parser.set_defaults(func=cmd_self_opt)


def handle_self_opt(args) -> int:
    """处理 hermes self-opt 命令。"""
    command = args.self_opt_command
    if not command:
        print("Usage: hermes self-opt <harvest|mine|gate|run> [options]")
        print("Run 'hermes self-opt <command> --help' for more info.")
        return 1

    if command == "harvest":
        return _handle_harvest(args)
    elif command == "mine":
        return _handle_mine(args)
    elif command == "gate":
        return _handle_gate(args)
    elif command == "run":
        return _handle_run(args)
    elif command == "distill":
        return _handle_distill(args)
    elif command == "memory":
        return _handle_memory(args)
    elif command == "router":
        return _handle_router(args)
    elif command == "extract":
        return _handle_extract(args)
    elif command == "distill-knowledge":
        return _handle_distill_knowledge(args)
    elif command == "gate-full":
        return _handle_gate_full(args)
    elif command == "review":
        return _handle_review(args)
    elif command == "commit":
        return _handle_commit(args)
    elif command == "knowledge":
        return _handle_knowledge_stats(args)
    else:
        print(f"Unknown command: {command}")
        return 1


def _handle_harvest(args) -> int:
    from hermes_self_opt.harvest import harvest
    try:
        dialog = harvest(args.session_id)
        print(dialog[:2000])
        print(f"\n---\nTotal: {len(dialog)} chars")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_mine(args) -> int:
    from hermes_self_opt.harvest import harvest
    from hermes_self_opt.mine import mine

    try:
        dialog = harvest(args.session_id)
        kwargs = {}
        if args.model:
            kwargs["model"] = args.model
        result = mine(dialog, **kwargs)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_gate(args) -> int:
    from pathlib import Path
    from hermes_self_opt.gate import gate_skill

    try:
        content = Path(args.skill_file).read_text(encoding="utf-8")
        result = gate_skill(content, benchmark_path=args.benchmark)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_run(args) -> int:
    from hermes_self_opt.pipeline import run

    try:
        results = run(
            days=args.days,
            session_id=args.session_id,
            benchmark_path=args.benchmark,
            overwrite_skill=args.overwrite_skill,
        )
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            for r in results:
                sid = r.get("session_id", "?")
                error = r.get("error")
                if error:
                    print(f"[{sid}] ❌ {error}")
                    continue
                mined = r.get("steps", {}).get("mine", {})
                if mined.get("has_content"):
                    print(f"[{sid}] ✅ 发现内容")
                    print(f"  memory:    {r['steps'].get('gate_memory', {}).get('decision', '?')}")
                    print(f"  skill:     {r['steps'].get('gate_skill', {}).get('decision', '?')}")
                else:
                    print(f"[{sid}] ⏭️  无有价值内容")
                log = r.get("log_path", "")
                if log:
                    print(f"  log:       {log}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_distill(args) -> int:
    from hermes_self_opt.distill import distill_daily, cleanup_daily
    try:
        result = distill_daily(args.date)
        if result["distilled_count"] > 0:
            print(f"✅ 蒸馏完成: {result['distilled_count']} 条记忆从 {result['daily_chars']} 字符的 Daily 中提取")
            if result.get("synced", 0) > 0:
                print(f"📝 已同步 {result['synced']} 条到 MEMORY.md")
        else:
            print(f"⏭️  {result['reason']} (daily: {result.get('daily_chars', 0)} chars)")
        if args.cleanup:
            deleted = cleanup_daily()
            if deleted:
                print(f"🧹 清理了 {deleted} 个过期的 Daily 文件")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_memory(args) -> int:
    from hermes_self_opt.core_memory import stats, load_all
    try:
        s = stats()
        print(f"Core Memory ({sum(s.values())} 条):")
        for cat, count in s.items():
            print(f"  {cat}: {count} 条")
        if args.show:
            print(f"\n{load_all()}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_router(args) -> int:
    from hermes_self_opt.router import build_index, query, stats
    sub = args.router_command
    try:
        if sub == "build":
            r = build_index()
            print(f"✅ 索引完成: {r['indexed']} 个 skill, {r['duration_ms']}ms")
            return 0
        elif sub == "query":
            results = query(args.query_text)
            if results:
                for r in results:
                    print(f"  {r['name']} (score={r['score']}) — {r['description'][:80]}")
            else:
                print("无匹配结果")
            return 0
        elif sub == "stats":
            s = stats()
            print(f"已索引: {s['indexed_skills']} 个 skill")
            print(f"匹配事件: {s['total_events']} 次")
            return 0
        else:
            print("Usage: hermes self-opt router <build|query|stats>")
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


# ── Phase 2 handlers ─────────────────────────────────────────────


def _handle_extract(args) -> int:
    from pathlib import Path
    from hermes_self_opt.extractor import extract_one, extract_all
    try:
        if args.file:
            result = extract_one(Path(args.file))
            results = [result]
        else:
            results = extract_all()

        if args.json:
            import json
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print(f"Extracted {len(results)} files:")
            for r in results:
                sid = r.get("id", "?")
                tags = r.get("tags", [])
                cmds = len(r.get("commands", []))
                device = r.get("device_type", "?")
                print(f"  {sid}  [{device}]  tags={len(tags)}  cmds={cmds}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_distill_knowledge(args) -> int:
    from hermes_self_opt.extractor import extract_all
    from hermes_self_opt.distill_knowledge import distill_and_generate
    try:
        print("Extracting normal/ MD files...")
        extracted = extract_all()
        if not extracted:
            print("No files extracted from normal/")
            return 1

        print(f"Distilling {len(extracted)} files → staging/ ...")
        result = distill_and_generate(extracted, dry_run=args.dry_run)

        print(f"\nResults:")
        print(f"  Documents processed:  {result['total_files']}")
        print(f"  New check_sources:    {result['new_check_sources']}")
        print(f"  New decision_sources: {result['new_decision_sources']}")
        print(f"  New full docs:        {result['new_full_docs']}")
        print(f"  Duplicates skipped:   {result['duplicates_skipped']}")
        if not args.dry_run:
            print(f"  Files written to:     {result['staging_dir']}")
        else:
            print(f"  (dry-run, no files written)")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_gate_full(args) -> int:
    from hermes_self_opt.gate_full import run_gate_checks
    try:
        result = run_gate_checks(verbose=args.verbose)
        print(f"Gate-Full: {result['passed']} passed, {result['failed']} failed")
        if result["errors"]:
            print(f"\nErrors ({len(result['errors'])}):")
            for e in result["errors"]:
                print(f"  [{e['check']}] {e['file']}: {e['message']}")
        if result["all_passed"]:
            print("\n✅ All checks passed — ready to commit")
        else:
            print("\n❌ Gate-Full failed — fix errors before commit")
        return 0 if result["all_passed"] else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_review(args) -> int:
    from hermes_self_opt.reviewer import scan_staging, review_staging
    try:
        scan_result = scan_staging()
        approved, _ = review_staging(scan_result=scan_result, auto_approve=args.yes)

        if not approved:
            return 1
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_commit(args) -> int:
    from hermes_self_opt.gate_full import run_gate_checks
    from hermes_self_opt.committer import commit_to_core
    from hermes_self_opt.reviewer import load_review_state, staging_changed_since_review
    try:
        # ── Review gate ──
        if not args.skip_review:
            state = load_review_state()
            if not state:
                print("❌ Not reviewed. Run 'hermes self-opt review' first.")
                print("   Or use --skip-review to bypass.")
                return 1
            if not state.get("approved"):
                print("❌ Review was rejected. Run 'hermes self-opt review' to re-review.")
                return 1
            if staging_changed_since_review(state):
                print("❌ Staging changed since last review. Run 'hermes self-opt review' to re-review.")
                return 1
            reviewed_at = state.get("reviewed_at", "unknown")
            print(f"✅ Review approved ({reviewed_at})")
        else:
            print("⚠️  Skipping review gate (--skip-review)")

        # ── Gate-Full ──
        gate_result = None
        if not args.skip_gate:
            print("Running Gate-Full checks...")
            gate_result = run_gate_checks()
            if not gate_result["all_passed"]:
                print(f"❌ Gate-Full: {gate_result['passed']} passed, {gate_result['failed']} failed")
                for e in gate_result["errors"]:
                    print(f"  [{e['check']}] {e['file']}: {e['message']}")
                print("\nFix errors or use --skip-gate to commit anyway.")
                return 1
            print(f"✅ Gate-Full: {gate_result['passed']} passed")
        else:
            print("⚠️  Skipping Gate-Full (--skip-gate)")

        result = commit_to_core(gate_result=gate_result, dry_run=args.dry_run)

        if result.get("error"):
            print(f"Error: {result['error']}")
            return 1

        print(f"\nCommitted: {result['committed']} files")
        print(f"  check_sources:    {result['check_sources']}")
        print(f"  decision_sources: {result['decision_sources']}")
        print(f"  full docs:        {result['full_docs']}")
        print(f"  dry-run:          {result['dry_run']}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_knowledge_stats(args) -> int:
    from hermes_self_opt.committer import stats
    try:
        s = stats()
        print("Knowledge Base Statistics:")
        print(f"  normal/ MD files:       {s['normal_md_files']}")
        print(f"  core/ check_sources:    {s['core_check_sources']}")
        print(f"  core/ decision_sources: {s['core_decision_sources']}")
        print(f"  core/ full docs:        {s['core_full_docs']}")
        print(f"  staging/ YAML files:    {s['staging_files']}")
        print(f"  index entries:          {s['index_entries']}")
        print(f"  index tags:             {s['index_tags']}")
        total = s['core_check_sources'] + s['core_decision_sources'] + s['core_full_docs']
        print(f"  ─────────────────────────────")
        print(f"  core/ total:            {total}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
