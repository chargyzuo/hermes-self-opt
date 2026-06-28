"""
feedback.py — Phase 4: 用户反馈回流（反馈层）。

框架设计 Line 436-450:
  位置: 框架底部
  作用: 用户纠正信号，标记待审查项
  信号类型: 显式纠正 / 隐式信号
  处理: 标记 → 入队 → 空闲时优先处理 → 可查看待审查列表

存储结构:
  ~/.hermes/knowledge/self-opt/corrections/
  ├── pending/
  ├── processed/
  └── rejected/
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path.home() / ".hermes" / "knowledge"
CORRECTIONS_DIR = KNOWLEDGE_DIR / "self-opt" / "corrections"
PENDING_DIR = CORRECTIONS_DIR / "pending"
PROCESSED_DIR = CORRECTIONS_DIR / "processed"
REJECTED_DIR = CORRECTIONS_DIR / "rejected"

# 信号类型
SIGNAL_EXPLICIT = "explicit"   # 显式纠正: "不对，应该这样做"
SIGNAL_IMPLICIT = "implicit"   # 隐式信号: 用户手动回退/重复尝试


def _ensure_dirs() -> None:
    """确保 corrections 目录结构存在。"""
    for d in [PENDING_DIR, PROCESSED_DIR, REJECTED_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _generate_id() -> str:
    """生成 correction ID: correction-YYYYMMDD-NNN。"""
    _ensure_dirs()
    today = datetime.now().strftime("%Y%m%d")
    # 查找当天已有的 correction 数量
    existing = list(PENDING_DIR.glob(f"correction-{today}-*.json"))
    existing += list(PROCESSED_DIR.glob(f"correction-{today}-*.json"))
    existing += list(REJECTED_DIR.glob(f"correction-{today}-*.json"))
    seq = len(existing) + 1
    return f"correction-{today}-{seq:03d}"


def capture_feedback(
    target: str,
    correction: str,
    target_type: str = "skill",
    signal_type: str = SIGNAL_EXPLICIT,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """捕获用户纠正信号，存入 pending/。

    Args:
        target: 目标标识（skill 名或 knowledge id）
        correction: 用户的纠正内容
        target_type: 目标类型，"skill" 或 "knowledge"
        signal_type: 信号类型，"explicit" 或 "implicit"
        session_id: 关联的 session ID（可选）

    Returns:
        correction 记录字典
    """
    _ensure_dirs()

    record = {
        "id": _generate_id(),
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "target_type": target_type,
        "target": target,
        "correction": correction,
        "signal_type": signal_type,
        "session_id": session_id,
        "status": "pending",
        "applied_diff": None,
        "gate_result": None,
    }

    filepath = PENDING_DIR / f"{record['id']}.json"
    filepath.write_text(
        json.dumps(record, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("Captured correction %s → %s (type=%s, signal=%s)",
                record["id"], target, target_type, signal_type)

    return record


def list_pending(status: str = "pending") -> List[Dict[str, Any]]:
    """列出待处理的 correction。

    Args:
        status: 筛选状态，"pending" / "processed" / "rejected" / "all"

    Returns:
        correction 记录列表
    """
    _ensure_dirs()

    dirs = []
    if status in ("pending", "all"):
        dirs.append(PENDING_DIR)
    if status in ("processed", "all"):
        dirs.append(PROCESSED_DIR)
    if status in ("rejected", "all"):
        dirs.append(REJECTED_DIR)

    records = []
    for d in dirs:
        for f in sorted(d.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                records.append(data)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read correction %s: %s", f, e)

    return records


def load_correction(correction_id: str) -> Optional[Dict[str, Any]]:
    """从 pending/ 或 processed/ 或 rejected/ 加载单条 correction。

    Args:
        correction_id: correction ID（如 correction-20260628-001）

    Returns:
        correction 记录字典，未找到返回 None
    """
    for d in [PENDING_DIR, PROCESSED_DIR, REJECTED_DIR]:
        fpath = d / f"{correction_id}.json"
        if fpath.exists():
            try:
                return json.loads(fpath.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
    return None


def _move_correction(correction_id: str, from_dir: Path, to_dir: Path) -> bool:
    """在 corrections 目录之间移动记录。"""
    src = from_dir / f"{correction_id}.json"
    if not src.exists():
        return False
    to_dir.mkdir(parents=True, exist_ok=True)
    dst = to_dir / f"{correction_id}.json"
    src.rename(dst)
    return True


from hermes_self_opt import SKILLS_ROOT

def _find_skill_file(skill_name: str) -> Optional[Path]:
    """查找 skill 文件路径。

    支持两种位置：
      1. skills/**/<name>/SKILL.md
      2. skills/self-opt/<name>/SKILL.md
    """
    skills_root = SKILLS_ROOT
    if not skills_root.exists():
        return None

    for skf in sorted(skills_root.rglob("SKILL.md")):
        parent = skf.parent.name
        # 双匹配：目录名 == skill_name 或 frontmatter name == skill_name
        if parent == skill_name:
            return skf
        try:
            content = skf.read_text(encoding="utf-8")
            if _extract_frontmatter_name(content) == skill_name:
                return skf
        except Exception:
            continue

    return None


def _extract_frontmatter_name(content: str) -> Optional[str]:
    """从 SKILL.md frontmatter 中提取 'name' 字段。"""
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    fm = content[3:end]
    for line in fm.split("\n"):
        line = line.strip()
        if line.startswith("name:"):
            return line[5:].strip().strip('"').strip("'")
    return None


def _find_knowledge_file(knowledge_id: str) -> Optional[Path]:
    """在 core/ 和 staging/ 中查找 knowledge YAML 文件（按 id 匹配）。"""
    for base in [KNOWLEDGE_DIR / "core", KNOWLEDGE_DIR / "self-opt" / "staging"]:
        if not base.exists():
            continue
        for yf in base.rglob("*.yaml"):
            if yf.name == f"{knowledge_id}.yaml":
                return yf
            # 也按 id 字段匹配
            try:
                import yaml
                data = yaml.safe_load(yf.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("id") == knowledge_id:
                    return yf
            except Exception:
                continue
    return None


FEEDBACK_APPLY_PROMPT = """你是一个 skill/knowledge 编辑助手。以下是一个目标文件，用户提出了纠正意见。请根据纠正意见生成修改后的完整内容。

## 目标文件
```
{target_content}
```

## 用户纠正意见
{correction}

## 要求
1. 只修改纠正意见指出的部分，保留其他内容不变
2. 如果是 skill，保留 frontmatter 结构
3. 如果是 knowledge YAML，保留 YAML 结构
4. 不要添加新的章节或步骤
5. 直接输出修改后的完整文件内容（不要解释）
"""


def process_feedback(
    correction_id: str,
    auxiliary_client=None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """处理单条 pending correction。

    流程：
      1. load correction → 确认 target 存在
      2. apply correction via LLM（如有 auxiliary_client）
      3. Gate-Lite 验证（如目标是 skill）
      4. 通过 → 写回原文件，移到 processed/
      5. 失败 → 移到 rejected/

    Args:
        correction_id: correction ID
        auxiliary_client: LLM client（可选）
        dry_run: 只模拟不写

    Returns:
        处理结果字典
    """
    record = load_correction(correction_id)
    if record is None:
        return {"correction_id": correction_id, "error": "未找到该 correction"}

    status = record.get("status", "")
    if status != "pending":
        return {"correction_id": correction_id, "error": f"状态为 {status}，非 pending"}

    target_type = record["target_type"]
    target = record["target"]
    correction_text = record["correction"]

    result = {
        "correction_id": correction_id,
        "target_type": target_type,
        "target": target,
        "status": "pending",
        "gate_result": None,
    }

    # ── Step 1: 查找目标文件 ──
    if target_type == "skill":
        target_file = _find_skill_file(target)
    else:
        target_file = _find_knowledge_file(target)

    if target_file is None:
        result["status"] = "rejected"
        result["error"] = f"未找到目标: {target_type}={target}"
        if not dry_run:
            _move_correction(correction_id, PENDING_DIR, REJECTED_DIR)
            # 更新 record 状态
            _update_record_status(correction_id, "rejected", result["error"])
        return result

    result["target_file"] = str(target_file)

    # ── Step 2: 读取目标内容 ──
    try:
        original_content = target_file.read_text(encoding="utf-8")
    except OSError as e:
        result["status"] = "rejected"
        result["error"] = f"无法读取目标文件: {e}"
        if not dry_run:
            _move_correction(correction_id, PENDING_DIR, REJECTED_DIR)
            _update_record_status(correction_id, "rejected", result["error"])
        return result

    result["original_hash"] = _hash_content(original_content)

    # ── Step 3: 应用修正（LLM 或直接 patch） ──
    if auxiliary_client is not None:
        try:
            from agent.auxiliary_client import call_llm
            client = call_llm
        except ImportError:
            client = auxiliary_client

        prompt = FEEDBACK_APPLY_PROMPT.format(
            target_content=original_content,
            correction=correction_text,
        )
        try:
            messages = [{"role": "user", "content": prompt}]
            response = client(task="default", messages=messages)
            if hasattr(response, "choices"):
                new_content = response.choices[0].message.content or ""
            elif isinstance(response, dict):
                new_content = response.get("content", "")
            else:
                new_content = str(response)
            new_content = new_content.strip()
        except Exception as e:
            logger.warning("LLM call failed: %s", e)
            result["status"] = "rejected"
            result["error"] = f"LLM 调用失败: {e}"
            if not dry_run:
                _move_correction(correction_id, PENDING_DIR, REJECTED_DIR)
                _update_record_status(correction_id, "rejected", result["error"])
            return result
    else:
        # 无 LLM：标记为需要手动处理
        result["status"] = "rejected"
        result["error"] = "无 LLM client，需手动处理"
        if not dry_run:
            _move_correction(correction_id, PENDING_DIR, REJECTED_DIR)
            _update_record_status(correction_id, "rejected", result["error"])
        return result

    if not new_content:
        result["status"] = "rejected"
        result["error"] = "LLM 返回空内容"
        if not dry_run:
            _move_correction(correction_id, PENDING_DIR, REJECTED_DIR)
            _update_record_status(correction_id, "rejected", result["error"])
        return result

    result["new_hash"] = _hash_content(new_content)

    # ── Step 4: Gate-Lite 验证（仅对 skill） ──
    if target_type == "skill":
        try:
            from hermes_self_opt.gate import gate_skill
            gate = gate_skill(new_content, skill_name=target)
            result["gate_result"] = gate

            if gate.get("decision") == "fail":
                result["status"] = "rejected"
                result["error"] = f"Gate-Lite 未通过: {gate.get('reason', '')}"
                if not dry_run:
                    _move_correction(correction_id, PENDING_DIR, REJECTED_DIR)
                    _update_record_status(correction_id, "rejected", result["error"])
                return result
        except ImportError:
            logger.warning("gate module not available, skipping Gate-Lite")
            result["gate_result"] = {"decision": "pass", "reason": "gate module not available"}
        except Exception as e:
            logger.warning("Gate-Lite failed: %s", e)
            result["gate_result"] = {"decision": "pass", "reason": f"Gate-Lite error, proceeding: {e}"}

    # ── Step 5: 写回文件 ──
    if not dry_run:
        try:
            # 先备份
            backup_path = target_file.with_suffix(".bak")
            backup_path.write_text(original_content, encoding="utf-8")

            # 写新内容
            target_file.write_text(new_content, encoding="utf-8")
            result["status"] = "processed"
            result["backup_path"] = str(backup_path)

            # 移到 processed/
            _move_correction(correction_id, PENDING_DIR, PROCESSED_DIR)
            _update_record_status(correction_id, "processed", "", result.get("gate_result"))

            logger.info("Applied correction %s → %s", correction_id, target_file)
        except OSError as e:
            result["status"] = "rejected"
            result["error"] = f"写入失败: {e}"
            if not dry_run:
                _move_correction(correction_id, PENDING_DIR, REJECTED_DIR)
                _update_record_status(correction_id, "rejected", result["error"])
            return result
    else:
        result["status"] = "dry_run"
        result["note"] = "模拟处理成功，未实际写入"

    # 记录 diff
    result["applied_diff"] = _generate_diff_summary(original_content, new_content)

    return result


def process_all_feedback(
    auxiliary_client=None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """处理所有 pending correction。

    Args:
        auxiliary_client: LLM client
        dry_run: 只模拟不写

    Returns:
        {"total": N, "processed": N, "rejected": N, "results": [...]}
    """
    pending = list_pending("pending")
    summary = {
        "total": len(pending),
        "processed": 0,
        "rejected": 0,
        "dry_run": dry_run,
        "results": [],
    }

    for record in pending:
        cid = record["id"]
        result = process_feedback(
            cid,
            auxiliary_client=auxiliary_client,
            dry_run=dry_run,
        )
        summary["results"].append(result)

        if result.get("status") in ("processed", "dry_run"):
            summary["processed"] += 1
        else:
            summary["rejected"] += 1

    return summary


def reject_feedback(correction_id: str, reason: str = "") -> Dict[str, Any]:
    """标记一条 pending correction 为 rejected。

    Args:
        correction_id: correction ID
        reason: 拒绝原因

    Returns:
        操作结果
    """
    record = load_correction(correction_id)
    if record is None:
        return {"correction_id": correction_id, "error": "未找到该 correction"}

    if record.get("status") != "pending":
        return {"correction_id": correction_id, "error": f"状态为 {record.get('status')}，非 pending"}

    _move_correction(correction_id, PENDING_DIR, REJECTED_DIR)
    _update_record_status(correction_id, "rejected", reason)

    return {"correction_id": correction_id, "status": "rejected", "reason": reason}


def _update_record_status(
    correction_id: str,
    new_status: str,
    reason: str = "",
    gate_result: Optional[Dict[str, Any]] = None,
) -> None:
    """更新 correction record 的状态字段。"""
    for d in [PENDING_DIR, PROCESSED_DIR, REJECTED_DIR]:
        fpath = d / f"{correction_id}.json"
        if fpath.exists():
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                data["status"] = new_status
                if reason:
                    data.setdefault("reject_reason", reason)
                if gate_result:
                    data["gate_result"] = gate_result
                fpath.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                break
            except (json.JSONDecodeError, OSError):
                break


def _hash_content(content: str) -> str:
    """内容 SHA256 hash。"""
    import hashlib
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _generate_diff_summary(original: str, new: str) -> str:
    """生成简洁的 diff 摘要。"""
    olines = original.split("\n")
    nlines = new.split("\n")

    added = 0
    removed = 0
    for line in nlines:
        if line not in original:
            added += 1
    for line in olines:
        if line not in new:
            removed += 1

    return f"+{added}/-{removed} lines"
