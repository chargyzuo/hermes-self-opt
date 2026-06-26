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

    # run
    run_parser = sub.add_parser("run", help="Run full self-opt pipeline")
    run_parser.add_argument("--session-id", help="Single session to process")
    run_parser.add_argument("--days", type=int, default=1, help="Days of history to process")
    run_parser.add_argument("--benchmark", help="Path to benchmark JSON")
    run_parser.add_argument("--overwrite-skill", action="store_true", help="Overwrite existing skills")
    run_parser.add_argument("--json", action="store_true", help="Output as JSON")

    for p in [harvest_parser, mine_parser, run_parser]:
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
