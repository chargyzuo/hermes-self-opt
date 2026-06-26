"""
pipeline.py — Step 5: 串联 Harvest → Mine → Gate-Lite → Write 全流程。

对外暴露 run() 和 run_session() 两个接口。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from hermes_self_opt.harvest import harvest, harvest_recent
from hermes_self_opt.mine import mine
from hermes_self_opt.gate import gate_memory, gate_skill
from hermes_self_opt.writer import write_memory, write_skill, write_log

logger = logging.getLogger(__name__)


def run_session(
    session_id: str,
    *,
    auxiliary_client=None,
    benchmark_path: Optional[str] = None,
    overwrite_skill: bool = False,
) -> Dict[str, Any]:
    """对单个 session 执行完整的 self-opt 流程。

    Args:
        session_id: Hermes session ID
        auxiliary_client: auxiliary LLM client（可选）
        benchmark_path: Benchmark 题库路径（可选）
        overwrite_skill: 是否覆盖已有同名 skill

    Returns:
        包含各步骤结果的字典
    """
    result = {
        "session_id": session_id,
        "steps": {},
    }

    # Step 1: Harvest
    logger.info("[%s] Harvesting...", session_id)
    try:
        dialog = harvest(session_id)
    except Exception as e:
        logger.error("[%s] Harvest failed: %s", session_id, e)
        result["error"] = f"Harvest failed: {e}"
        return result
    result["steps"]["harvest"] = {"dialog_chars": len(dialog)}

    if not dialog.strip():
        logger.info("[%s] Empty dialog, skipping", session_id)
        result["steps"]["mine"] = {"has_content": False}
        return result

    # Step 2: Mine
    logger.info("[%s] Mining...", session_id)
    try:
        mined = mine(dialog, auxiliary_client=auxiliary_client)
    except Exception as e:
        logger.error("[%s] Mine failed: %s", session_id, e)
        result["error"] = f"Mine failed: {e}"
        return result
    result["steps"]["mine"] = mined

    if not mined.get("has_content"):
        logger.info("[%s] No valuable content found", session_id)
        return result

    # Step 3: Gate (memory)
    memory_result = {"decision": "skip", "reason": "无 memory 内容"}
    if mined.get("memory_chunk"):
        memory_result = gate_memory(mined["memory_chunk"])
    result["steps"]["gate_memory"] = memory_result

    # Step 3: Gate (skill)
    skill_result = {"decision": "skip", "reason": "无 skill 内容"}
    skill_candidate = mined.get("skill_candidate", {})
    if skill_candidate and skill_candidate.get("content"):
        skill_result = gate_skill(
            skill_candidate["content"],
            auxiliary_client=auxiliary_client,
            benchmark_path=benchmark_path,
        )
    result["steps"]["gate_skill"] = skill_result

    # Step 4: Write
    write_results = {}
    if memory_result["decision"] == "pass":
        write_results["memory"] = write_memory(mined["memory_chunk"])
    if skill_result["decision"] == "pass" and skill_candidate.get("name"):
        write_results["skill"] = write_skill(
            skill_candidate["name"],
            skill_candidate["content"],
            source_session=session_id,
            overwrite=overwrite_skill,
        )
    result["steps"]["write"] = write_results

    # Write log
    log_path = write_log(result)
    result["log_path"] = log_path

    logger.info("[%s] Done. Log: %s", session_id, log_path)
    return result


def run(
    days: int = 1,
    *,
    session_id: Optional[str] = None,
    auxiliary_client=None,
    benchmark_path: Optional[str] = None,
    overwrite_skill: bool = False,
) -> List[Dict[str, Any]]:
    """批量运行 self-opt 流程。

    Args:
        days: 回溯天数（当 session_id 未指定时使用）
        session_id: 指定单个 session
        auxiliary_client: auxiliary LLM client
        benchmark_path: Benchmark 题库路径
        overwrite_skill: 是否覆盖已有 skill

    Returns:
        每个 session 的结果列表
    """
    if session_id:
        return [run_session(
            session_id,
            auxiliary_client=auxiliary_client,
            benchmark_path=benchmark_path,
            overwrite_skill=overwrite_skill,
        )]

    from hermes_self_opt.harvest import list_recent_sessions
    sessions = list_recent_sessions(days=days)
    logger.info("Found %d sessions in the last %d day(s)", len(sessions), days)

    results = []
    for s in sessions:
        result = run_session(
            s["session_id"],
            auxiliary_client=auxiliary_client,
            benchmark_path=benchmark_path,
            overwrite_skill=overwrite_skill,
        )
        results.append(result)

    return results
