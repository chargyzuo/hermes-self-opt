#!/usr/bin/env python3
"""
Self-Optimization pipeline runner for cron use.
Calls the pipeline modules directly (bypasses CLI registration).
"""
import json
import logging
import sys
from pathlib import Path

# Ensure the hermes-self-opt package root is on the path
SELF_OPT_ROOT = Path(__file__).resolve().parent
if str(SELF_OPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SELF_OPT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)

def run_pipeline(days: int = 1) -> dict:
    """Run Phase 1: Harvest → Mine → Gate-Lite → Write"""
    from hermes_self_opt.pipeline import run

    results = run(days=days)
    
    total_sessions = 0
    troubleshooting_count = 0
    skills_generated = 0
    skills_updated = 0
    memories_written = 0
    errors = []
    skipped = 0

    for r in results:
        total_sessions += 1
        steps = r.get("steps", {})
        
        # Check if it was a troubleshooting session (had content to mine)
        mined = steps.get("mine", {})
        if mined.get("has_content"):
            troubleshooting_count += 1
        
        # Check for errors
        error = r.get("error")
        if error:
            errors.append(f"[{r['session_id']}] {error}")
            continue
        
        # Check what was written
        write_results = steps.get("write", {})
        if write_results.get("skill"):
            skills_generated += 1
        if write_results.get("memory"):
            memories_written += 1
    
    return {
        "total_sessions_harvested": total_sessions,
        "troubleshooting_sessions": troubleshooting_count,
        "skills_generated_or_updated": skills_generated,
        "memories_written": memories_written,
        "errors": errors,
        "raw": results,
    }

def run_memory() -> dict:
    """Run Phase 3: memory distillation"""
    from hermes_self_opt.distill import distill_daily
    
    result = distill_daily()
    return {
        "distilled_count": result.get("distilled_count", 0),
        "daily_chars": result.get("daily_chars", 0),
        "reason": result.get("reason", ""),
    }

def main():
    print("=" * 60)
    print("Hermes Agent Self-Optimization Pipeline")
    print("=" * 60)
    
    # Phase 1: Process sessions
    print("\n📡 Phase 1: Harvesting & Processing Sessions...")
    pipeline_result = run_pipeline(days=1)
    
    print(f"  Sessions harvested:       {pipeline_result['total_sessions_harvested']}")
    print(f"  Troubleshooting sessions: {pipeline_result['troubleshooting_sessions']}")
    print(f"  Skills generated/updated: {pipeline_result['skills_generated_or_updated']}")
    print(f"  Memories written:         {pipeline_result['memories_written']}")
    
    if pipeline_result['errors']:
        print(f"  Errors ({len(pipeline_result['errors'])}):")
        for err in pipeline_result['errors']:
            print(f"    ❌ {err}")
    
    # Phase 3: Memory distillation
    print("\n🧠 Phase 3: Memory Distillation...")
    memory_result = run_memory()
    print(f"  Distilled memory entries: {memory_result['distilled_count']}")
    print(f"  Daily memory chars:       {memory_result['daily_chars']}")
    print(f"  Status:                   {memory_result['reason']}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Sessions harvested:                        {pipeline_result['total_sessions_harvested']}")
    print(f"  Troubleshooting sessions identified:       {pipeline_result['troubleshooting_sessions']}")
    print(f"  New/updated skills generated:              {pipeline_result['skills_generated_or_updated']}")
    print(f"  Memory entries added (distillation):       {memory_result['distilled_count']}")
    if pipeline_result['errors']:
        print(f"  Errors:                                    {len(pipeline_result['errors'])}")
        for err in pipeline_result['errors']:
            print(f"    - {err}")
    else:
        print(f"  Errors:                                    0")

if __name__ == "__main__":
    main()
