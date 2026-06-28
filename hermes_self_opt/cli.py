"""
cli.py — hermes self-opt CLI 子命令定义。

提供以下子命令：
  hermes self-opt harvest        --session-id <id>   测试 Harvest
  hermes self-opt mine           --session-id <id>   测试 Mine
  hermes self-opt process               --session-id <id>   处理 session → memory/skill
  hermes self-opt knowledge-build        [-y] [--dry-run] [--skip-gate]  P2 一键串联
  hermes self-opt knowledge                              知识库统计
  hermes self-opt export-schema       [--dry-run]        导出 _schema.yaml
  hermes self-opt judge               [-v]               LLM 评分
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
    gate_parser.add_argument("--skill-name", help="Skill name for matching Skill Execution Benchmark")

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
    rm = router_sub.add_parser("monitor", help="Monitor routing trigger rates")
    rm.add_argument("--skill", help="Filter by skill name")
    rm.add_argument("--days", type=int, default=7, help="Days to analyze (default: 7)")
    rm.add_argument("--json", action="store_true", help="Output as JSON")

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
    gf_parser.add_argument("--judge", action="store_true", help="Also run LLM Judge on full docs")

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

    # export-schema
    es_parser = sub.add_parser("export-schema", help="Phase 2: export JSON schema to core/_schema.yaml")
    es_parser.add_argument("--dry-run", action="store_true", help="Preview only")

    # judge
    jd_parser = sub.add_parser("judge", help="Phase 2: LLM Judge — score full docs against benchmark")
    jd_parser.add_argument("--verbose", "-v", action="store_true", help="Per-file results")
    jd_parser.add_argument("--benchmark", help="Benchmark JSON path (default: ~/.hermes/knowledge/self-opt/benchmark.json)")

    # process (P1: session → memory/skill)
    process_parser = sub.add_parser("process", help="Process session: Harvest → Mine → Gate-Lite")
    process_parser.add_argument("--session-id", help="Single session to process")
    process_parser.add_argument("--days", type=int, default=1, help="Days of history to process")
    process_parser.add_argument("--benchmark", help="Path to benchmark JSON")
    process_parser.add_argument("--overwrite-skill", action="store_true", help="Overwrite existing skills")
    process_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # knowledge-build (P2: one-click knowledge pipeline)
    kb_parser = sub.add_parser("knowledge-build", help="Phase 2: one-click extract→distill→review→gate→commit")
    kb_parser.add_argument("--yes", "-y", action="store_true", help="Auto-approve review")
    kb_parser.add_argument("--dry-run", action="store_true", help="Simulate, don't write/commit")
    kb_parser.add_argument("--skip-gate", action="store_true", help="Skip Gate-Full checks")
    kb_parser.add_argument("--judge", action="store_true", help="Run LLM Judge after Gate-Full")
    kb_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # optimize (P3: skill optimization loop)
    opt_parser = sub.add_parser("optimize", help="Phase 3: Rollout→Reflect→Edit→Gate-Lite skill optimization")
    opt_parser.add_argument("--skill-name", help="Optimize a single skill (omit for all)")
    opt_parser.add_argument("--dry-run", action="store_true", help="Simulate, don't write skills")
    opt_parser.add_argument("--max-iters", type=int, default=3, help="Max iterations per skill (default: 3)")
    opt_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # crystallize (P3: new skill generation)
    cry_parser = sub.add_parser("crystallize", help="Phase 3: detect recurring patterns → generate new skills")
    cry_parser.add_argument("--days", type=int, default=7, help="Days of sessions to analyze (default: 7)")
    cry_parser.add_argument("--dry-run", action="store_true", help="Simulate, don't write skills")
    cry_parser.add_argument("--detect-only", action="store_true", help="Only detect patterns, don't generate")
    cry_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # feedback (P4: user feedback loop)
    fb_parser = sub.add_parser("feedback", help="Phase 4: capture/list/process/reject user corrections")
    fb_sub = fb_parser.add_subparsers(dest="feedback_command")

    fb_capture = fb_sub.add_parser("capture", help="Capture a user correction")
    fb_capture.add_argument("--target", required=True, help="Target skill name or knowledge ID")
    fb_capture.add_argument("--correction", required=True, help="Correction text")
    fb_capture.add_argument("--type", default="skill", choices=["skill", "knowledge"],
                            help="Target type (default: skill)")
    fb_capture.add_argument("--signal", default="explicit", choices=["explicit", "implicit"],
                            help="Signal type (default: explicit)")
    fb_capture.add_argument("--session-id", help="Associated session ID")

    fb_list = fb_sub.add_parser("list", help="List corrections")
    fb_list.add_argument("--status", default="pending", choices=["pending", "processed", "rejected", "all"],
                         help="Filter by status (default: pending)")
    fb_list.add_argument("--json", action="store_true", help="Output as JSON")

    fb_process = fb_sub.add_parser("process", help="Process pending corrections")
    fb_process.add_argument("--id", dest="correction_id", help="Process a single correction by ID")
    fb_process.add_argument("--all", action="store_true", help="Process all pending corrections")
    fb_process.add_argument("--dry-run", action="store_true", help="Simulate, don't write")

    fb_reject = fb_sub.add_parser("reject", help="Reject a pending correction")
    fb_reject.add_argument("--id", required=True, dest="correction_id", help="Correction ID to reject")
    fb_reject.add_argument("--reason", default="", help="Rejection reason")

    # eventlog
    el_parser = sub.add_parser("eventlog", help="View all self-opt events (skill/knowledge/memory/cron changes)")
    el_parser.add_argument("--type", default="all", choices=["all", "skill", "knowledge", "memory", "cron"],
                           help="Filter by event type (default: all)")
    el_parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    el_parser.add_argument("--limit", type=int, default=50, help="Max events to show (default: 50)")
    el_parser.add_argument("--json", action="store_true", help="Output as JSON")

    for p in [harvest_parser, mine_parser, process_parser, distill_parser, mem_parser,
              router_parser, extract_parser, dk_parser, gf_parser, rv_parser, cm_parser, ks_parser, es_parser, jd_parser,
              kb_parser, opt_parser, cry_parser, fb_parser, el_parser]:
        p.set_defaults(func=cmd_self_opt)
    gate_parser.set_defaults(func=cmd_self_opt)


def handle_self_opt(args) -> int:
    """处理 hermes self-opt 命令。"""
    command = args.self_opt_command
    if not command:
        print("Usage: hermes self-opt <harvest|mine|process|distill|...> [options]")
        print("Run 'hermes self-opt <command> --help' for more info.")
        return 1

    if command == "harvest":
        return _handle_harvest(args)
    elif command == "mine":
        return _handle_mine(args)
    elif command == "gate":
        return _handle_gate(args)
    elif command == "process":
        return _handle_process(args)
    elif command == "run":
        # deprecated alias
        print("⚠️  'run' is deprecated, use 'process' instead")
        return _handle_process(args)
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
    elif command == "export-schema":
        return _handle_export_schema(args)
    elif command == "judge":
        return _handle_judge(args)
    elif command == "knowledge-build":
        return _handle_knowledge_build(args)
    elif command == "run-pipeline":
        # deprecated alias
        print("⚠️  'run-pipeline' is deprecated, use 'knowledge-build' instead")
        return _handle_knowledge_build(args)
    elif command == "optimize":
        return _handle_optimize(args)
    elif command == "crystallize":
        return _handle_crystallize(args)
    elif command == "feedback":
        return _handle_feedback(args)
    elif command == "eventlog":
        return _handle_eventlog(args)
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
        result = gate_skill(content, benchmark_path=args.benchmark, skill_name=getattr(args, "skill_name", None))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_process(args) -> int:
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
    from hermes_self_opt.router import (
        build_index, query, stats, monitor,
        find_description_gap, rewrite_description, rollback_skill,
    )
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
        elif sub == "gap":
            gap_result = find_description_gap(args.skill_name)
            if gap_result:
                print(f"⚠️  {args.skill_name}: 存在 description gap")
                print(f"  未覆盖的说法: {gap_result}")
            else:
                print(f"✅ {args.skill_name}: 无 description gap")
            return 0
        elif sub == "rewrite":
            rw_result = rewrite_description(
                args.skill_name,
                dry_run=getattr(args, "dry_run", False),
            )
            if rw_result["action"] == "rewrote":
                print(f"✅ 已重写 {args.skill_name}")
                print(f"  old: {rw_result['old'][:80]}")
                print(f"  new: {rw_result['new'][:80]}")
            elif rw_result["action"] == "dry_run":
                print(f"🔍 [dry-run] {args.skill_name}")
                print(f"  old: {rw_result['old'][:80]}")
                print(f"  new: {rw_result['new'][:80]}")
            else:
                print(f"⏭️  {args.skill_name}: {rw_result.get('reason', rw_result['action'])}")
            return 0
        elif sub == "rollback":
            rb_result = rollback_skill(args.skill_name)
            if rb_result["action"] == "rolled_back":
                print(f"✅ 已回滚 {args.skill_name} → {rb_result['path']}")
            else:
                print(f"⏭️  {args.skill_name}: {rb_result.get('reason', rb_result['action'])}")
            return 0
        elif sub == "monitor":
            m = monitor(skill_name=getattr(args, "skill", None), days=args.days)
            if getattr(args, "json", False):
                print(json.dumps(m, indent=2, ensure_ascii=False))
                return 0
            print(f"Router Monitor — {m['period']}")
            print(f"  总事件: {m['total_events']}")
            print(f"  无匹配率: {m['miss_rate']:.1%}")
            print(f"  全局纠正率: {m['overall_correction_rate']:.1%}")
            if m['skills']:
                print(f"\n  Skills ({len(m['skills'])}):")
                for sk in m['skills']:
                    triggers = f"{sk['trigger_rate']:.0%}" if sk['trigger_rate'] > 0 else "N/A"
                    corr = f"{sk['correction_rate']:.0%}" if sk['correction_rate'] > 0 else "0%"
                    recent = ", ".join(sk['recent_queries'][:2]) if sk['recent_queries'] else "-"
                    print(f"    {sk['name']}")
                    print(f"      匹配: {sk['total_matches']}  触发率: {triggers}  纠正率: {corr}  avg分: {sk['avg_score']}")
                    print(f"      最近: {recent[:60]}")
            else:
                print("\n  无匹配数据")
            return 0
        else:
            print("Usage: hermes self-opt router <build|query|stats|gap|rewrite|rollback|monitor>")
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
    from hermes_self_opt.gate_full import run_gate_checks, run_llm_judge
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

        # Optional LLM Judge
        if args.judge:
            print("\n── LLM Judge ──")
            judge = run_llm_judge(verbose=args.verbose)
            if judge.get("error"):
                print(f"  ⚠️  {judge['error']}")
            elif judge["results"]:
                s = judge["summary"]
                print(f"  {judge['total']} full docs scored")
                print(f"  avg score: {s['avg_score']}/5  |  redline fails: {s['redline_fails']}  |  top: {s['top_match']}")
                if args.verbose:
                    for r in judge["results"]:
                        status = "✅" if r["redline_pass"] else "❌"
                        bm = r["matched_benchmark"] or "-"
                        print(f"    {status} {r['id']}  score={r['coverage_score']}  bm={bm}  {r['reason'][:60]}")
            else:
                print("  No full docs in staging/")
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


def _handle_export_schema(args) -> int:
    from hermes_self_opt.gate_full import export_schema
    try:
        result = export_schema(dry_run=args.dry_run)
        path = result["path"]
        ver = result["schema_version"]
        if args.dry_run:
            print(f"Schema v{ver} — {result['lines']} lines → {path} (dry-run)")
        else:
            print(f"✅ Schema v{ver} exported → {path}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_judge(args) -> int:
    from hermes_self_opt.gate_full import run_llm_judge
    try:
        judge = run_llm_judge(benchmark_path=args.benchmark, verbose=args.verbose)
        if judge.get("error"):
            print(f"⚠️  {judge['error']}")
            return 1
        if not judge["results"]:
            print("No full docs found in staging/")
            return 0

        print(f"LLM Judge: {judge['total']} full docs scored\n")
        s = judge["summary"]
        print(f"  avg score:     {s['avg_score']}/5")
        print(f"  redline fails: {s['redline_fails']}")
        print(f"  top match:     {s['top_match']}")
        print()
        for r in judge["results"]:
            status = "✅" if r["redline_pass"] else "❌"
            bm = r["matched_benchmark"] or "-"
            print(f"  {status} {r['id']}")
            print(f"     score={r['coverage_score']}/5  bm={bm}")
            print(f"     {r['reason']}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_knowledge_build(args) -> int:
    """P2: one-click pipeline: extract → distill → review → gate → commit."""
    from hermes_self_opt.extractor import extract_all
    from hermes_self_opt.distill_knowledge import distill_and_generate
    from hermes_self_opt.reviewer import scan_staging, review_staging
    from hermes_self_opt.gate_full import run_gate_checks
    from hermes_self_opt.committer import commit_to_core

    try:
        # ── Stage 1: extract ──
        print("=" * 60)
        print("Phase 2 Pipeline — One-Click Knowledge Build")
        print("=" * 60)
        print()
        print("[1/5] Extract: normal/ MD → structured data ...")
        extracted = extract_all()
        if not extracted:
            print("❌ No files extracted from normal/ — pipeline stopped.")
            return 1
        print(f"✅ Extracted {len(extracted)} files")

        # ── Stage 2: distill ──
        print()
        print("[2/5] Distill: dedup + generate YAML → staging/ ...")
        distill_result = distill_and_generate(extracted, dry_run=args.dry_run)
        print(f"  Documents:        {distill_result['total_files']}")
        print(f"  New check_sources:{distill_result['new_check_sources']}")
        print(f"  New decision_src: {distill_result['new_decision_sources']}")
        print(f"  New full docs:    {distill_result['new_full_docs']}")
        print(f"  Duplicates:       {distill_result['duplicates_skipped']}")

        total_new = (distill_result['new_check_sources'] +
                     distill_result['new_decision_sources'] +
                     distill_result['new_full_docs'])
        if total_new == 0:
            print("✅ No new content — nothing to commit. Pipeline complete.")
            return 0

        if args.dry_run:
            print("  (dry-run, no files written)")

        # ── Stage 3: review ──
        print()
        print("[3/5] Review: staging/ changes ...")
        scan_result = scan_staging()
        if scan_result["total"] == 0:
            print("⚠️  No files in staging — pipeline stopped.")
            return 1

        approved, _ = review_staging(scan_result=scan_result, auto_approve=args.yes)
        if not approved:
            print("❌ Review rejected — pipeline stopped.")
            return 1

        if args.dry_run:
            print("✅ Pipeline complete (dry-run).")
            return 0

        # ── Stage 4: gate-full ──
        print()
        if not args.skip_gate:
            print("[4/5] Gate-Full: 4 rigid checks ...")
            gate_result = run_gate_checks(verbose=args.verbose)
            if not gate_result["all_passed"]:
                print(f"❌ Gate-Full: {gate_result['passed']} passed, {gate_result['failed']} failed")
                for e in gate_result["errors"]:
                    print(f"  [{e['check']}] {e['file']}: {e['message']}")
                print("Fix errors and retry, or use --skip-gate.")
                return 1
            print(f"✅ Gate-Full: {gate_result['passed']} passed")

            # ── Stage 4b: LLM Judge (optional) ──
            if args.judge:
                from hermes_self_opt.gate_full import run_llm_judge
                print()
                print("[4b/5] LLM Judge: evaluating full docs against benchmark ...")
                judge = run_llm_judge(verbose=args.verbose)
                if judge.get("error"):
                    print(f"  ⚠️  {judge['error']}")
                elif judge["results"]:
                    s = judge["summary"]
                    print(f"  {judge['total']} full docs scored")
                    print(f"  avg score: {s['avg_score']}/5  |  redline fails: {s['redline_fails']}  |  top: {s['top_match']}")
                    if args.verbose:
                        for r in judge["results"]:
                            status = "✅" if r["redline_pass"] else "❌"
                            print(f"    {status} {r['id']}  score={r['coverage_score']}  {r['reason'][:60]}")
        else:
            print("[4/5] Gate-Full: ⚠️  skipped (--skip-gate)")

        # ── Stage 5: commit ──
        print()
        print("[5/5] Commit: staging → core ...")
        commit_result = commit_to_core(dry_run=False)

        if commit_result.get("error"):
            print(f"❌ {commit_result['error']}")
            return 1

        print(f"✅ Committed: {commit_result['committed']} files")
        print(f"  check_sources:    {commit_result['check_sources']}")
        print(f"  decision_sources: {commit_result['decision_sources']}")
        print(f"  full docs:        {commit_result['full_docs']}")
        print()
        print("=" * 60)
        print("✅ Pipeline complete!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_optimize(args) -> int:
    """Phase 3: skill optimization loop (Rollout → Reflect → Edit → Gate-Lite)."""
    from hermes_self_opt.skillopt import optimize_skill, optimize_all, _load_all_benchmark_skills

    try:
        if args.skill_name:
            result = optimize_skill(
                args.skill_name,
                max_iterations=args.max_iters,
                dry_run=args.dry_run,
            )
            results = [result]
        else:
            results = optimize_all(
                max_iterations=args.max_iters,
                dry_run=args.dry_run,
            )

        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            for r in results:
                name = r.get("skill_name", "?")
                error = r.get("error")
                if error:
                    print(f"[{name}] ❌ {error}")
                    continue

                bm_count = r.get("benchmark_count", 0)
                its = r.get("iterations", [])
                passed = r.get("passed", False)
                written = r.get("written", False)
                final = r.get("final_score", "?")

                status = "✅" if passed else "❌"
                written_mark = " (written)" if written else (" (dry-run)" if args.dry_run else "")
                print(f"[{name}] {status} score={final} | {len(its)} iters | {bm_count} benchmarks{written_mark}")

                for it in its:
                    it_num = it.get("iteration", "?")
                    score = it.get("coverage_score", "?")
                    ok = it.get("all_passed", False)
                    tag = "✅" if ok else "🔄"
                    print(f"  iter {it_num}: {tag} score={score}")
                    for bm in it.get("benchmarks", []):
                        bid = bm.get("id", "?")
                        bm_score = bm.get("coverage_score", "?")
                        bm_rl = "✅" if bm.get("redline_pass") else "❌"
                        print(f"    {bid}: score={bm_score} redline={bm_rl}")

        total_passed = sum(1 for r in results if r.get("passed"))
        total = len(results)
        print(f"\nTotal: {total_passed}/{total} skills passed")
        return 0 if total_passed == total else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_crystallize(args) -> int:
    """Phase 3: cross-session pattern detection → new skill generation."""
    from hermes_self_opt.crystallize import crystallize, crystallize_detect

    try:
        if args.detect_only:
            result = crystallize_detect(days=args.days)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                sc = result.get("session_count", 0)
                enough = result.get("enough_sessions", False)
                reason = result.get("reason", "")
                print(f"Sessions found: {sc} (need ≥ {result.get('min_sessions_for_pattern', '?')})")
                print(f"Enough: {'✅' if enough else '❌'}")
                if reason:
                    print(f"  {reason}")
            return 0

        result = crystallize(days=args.days, dry_run=args.dry_run)

        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            sp = result.get("sessions_processed", 0)
            error = result.get("error")
            reason = result.get("reason")
            if error:
                print(f"❌ {error}")
                return 1
            if reason:
                print(f"⏭️  {reason} (sessions: {sp})")
                return 0

            pf = result.get("patterns_found", False)
            print(f"Sessions analyzed: {sp}")
            print(f"Patterns found: {'✅' if pf else '❌'}")

            skills = result.get("skills_generated", [])
            if not skills:
                print("No new skills generated.")
            else:
                print(f"\nSkills generated: {len(skills)}")
                for s in skills:
                    name = s.get("name", "?")
                    dup = s.get("duplicate", False)
                    passed = s.get("gate_passed", False)
                    written = s.get("written", False)
                    score = s.get("gate_score", "?")

                    if dup:
                        print(f"  ⏭️  {name}: duplicate ({s.get('reason', '')})")
                    elif passed:
                        mark = " (written)" if written else " (dry-run)"
                        print(f"  ✅ {name}: score={score}{mark}")
                        print(f"     {s.get('description', '')[:80]}")
                    else:
                        print(f"  ❌ {name}: score={score} ({s.get('reason', '')[:60]})")

                tg = result.get("total_generated", 0)
                tp = result.get("total_passed", 0)
                tw = result.get("total_written", 0)
                print(f"\nTotal: {tp}/{tg} passed, {tw} written")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_feedback(args) -> int:
    """Phase 4: 用户反馈回流 — capture/list/process/reject."""
    from hermes_self_opt.feedback import (
        capture_feedback, list_pending, process_feedback,
        process_all_feedback, reject_feedback,
    )

    sub = args.feedback_command
    if not sub:
        print("Usage: hermes self-opt feedback <capture|list|process|reject> [options]")
        return 1

    try:
        if sub == "capture":
            record = capture_feedback(
                target=args.target,
                correction=args.correction,
                target_type=args.type,
                signal_type=args.signal,
                session_id=getattr(args, "session_id", None),
            )
            print(f"✅ Captured: {record['id']}")
            print(f"   target: {record['target_type']}={record['target']}")
            print(f"   signal: {record['signal_type']}")
            print(f"   file:   {record['id']}.json (pending/)")
            return 0

        elif sub == "list":
            records = list_pending(args.status)
            if args.json:
                print(json.dumps(records, indent=2, ensure_ascii=False))
                return 0

            status_label = args.status.capitalize()
            print(f"Corrections ({status_label}): {len(records)}")
            if not records:
                return 0
            for r in records:
                sid = r.get("session_id", "-")
                ts = r.get("timestamp", "")[:16]
                print(f"  [{r['id']}] {r['target_type']}={r['target']} ({r['signal_type']})")
                print(f"     {ts}  session={sid}  status={r['status']}")
                print(f"     \"{r['correction'][:80]}\"")
            return 0

        elif sub == "process":
            if args.all:
                print(f"Processing all pending corrections...")
                summary = process_all_feedback(dry_run=args.dry_run)
                print(f"Total: {summary['total']}, processed: {summary['processed']}, rejected: {summary['rejected']}")
                for r in summary["results"]:
                    cid = r["correction_id"]
                    st = r["status"]
                    err = r.get("error", "")
                    mark = "✅" if st in ("processed", "dry_run") else "❌"
                    print(f"  {mark} {cid}: {st}" + (f" — {err}" if err else ""))
                return 0

            elif args.correction_id:
                result = process_feedback(args.correction_id, dry_run=args.dry_run)
                if result.get("error"):
                    print(f"❌ {result['correction_id']}: {result['error']}")
                    return 1
                print(f"✅ {result['correction_id']}: {result['status']}")
                if result.get("target_file"):
                    print(f"   target: {result['target_file']}")
                if result.get("gate_result"):
                    g = result["gate_result"]
                    print(f"   gate:   {g.get('decision', '?')} (score={g.get('coverage_score', '?')})")
                if result.get("applied_diff"):
                    print(f"   diff:   {result['applied_diff']}")
                return 0
            else:
                print("Specify --id <correction-id> or --all")
                return 1

        elif sub == "reject":
            result = reject_feedback(args.correction_id, args.reason)
            if result.get("error"):
                print(f"❌ {result['correction_id']}: {result['error']}")
                return 1
            print(f"✅ Rejected: {result['correction_id']}")
            if args.reason:
                print(f"   reason: {args.reason}")
            return 0

        else:
            print(f"Unknown feedback command: {sub}")
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_eventlog(args) -> int:
    """Handle hermes self-opt eventlog command."""
    from hermes_self_opt.eventlog import query, format_output
    try:
        result = query(
            target=args.type,
            days=args.days,
            limit=args.limit,
            json_output=args.json,
        )
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        else:
            print(format_output(result))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
