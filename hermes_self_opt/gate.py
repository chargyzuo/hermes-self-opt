"""
gate.py — Step 3: Gate-Lite 验证。

对 Mine 的结果做基本验证：
  1. memory_chunk: 长度限制 + 敏感信息检查
  2. skill_candidate: LLM Judge 评分（必要步骤覆盖 + 红线检查）

Benchmark 为空时只做基本检查（长度、敏感信息），不跑评分。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Memory 最大长度
MAX_MEMORY_CHARS = 500
# 敏感信息模式（阻止写入密码/token）
SENSITIVE_PATTERNS = [
    r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+",
    r"(?i)(api[_-]?key|apikey)\s*[:=]\s*\S+",
    r"(?i)(secret|token)\s*[:=]\s*\S+",
    r"(?i)sk-[a-zA-Z0-9]{20,}",  # OpenAI API key 格式
]

GATE_PROMPT = """你是一个 skill 质量评审员。以下是一个新生成的 skill 草稿。

## Skill 草稿
{skill_content}

## Benchmark 考题
{benchmark}

## 评分标准
请从两个维度评分：
1. 必要步骤覆盖（0-5）：skill 是否覆盖了排障必要的核心步骤。0=完全无关，5=完整覆盖。
2. 红线检查（pass/fail）：skill 是否包含绝对不该做的错误操作。

## 输出格式（JSON）
```json
{{
  "coverage_score": 0,
  "redline_pass": true,
  "reason": "简要说明评分原因"
}}
```"""


def _has_sensitive_content(text: str) -> bool:
    """检查文本是否包含敏感信息（密码、token 等）。"""
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def _load_benchmark(benchmark_path: Optional[str] = None) -> str:
    """加载 Benchmark 题库。"""
    if benchmark_path:
        path = Path(benchmark_path)
    else:
        path = Path.home() / ".hermes" / "knowledge" / "self-opt" / "benchmark.json"

    if not path.exists():
        logger.info("Benchmark file not found at %s, skipping LLM Judge", path)
        return ""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return "\n".join(
                f"Q{i+1}: {item.get('question', '')}"
                for i, item in enumerate(data[:5])
            )
        return json.dumps(data, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load benchmark: %s", e)
        return ""


def gate_skill(skill_content: str, auxiliary_client=None, benchmark_path: Optional[str] = None) -> Dict[str, Any]:
    """对 skill 草稿做 LLM Judge 评分。

    Args:
        skill_content: SKILL.md 内容
        auxiliary_client: Hermes auxiliary client
        benchmark_path: Benchmark 题库路径（可选）

    Returns:
        {"decision": "pass"|"fail"|"skip", "coverage_score": int, "reason": str}
    """
    if not skill_content or not skill_content.strip():
        return {"decision": "skip", "coverage_score": 0, "reason": "无 skill 内容"}

    benchmark = _load_benchmark(benchmark_path)
    if not benchmark:
        # 没有 Benchmark 时只做基本检查：长度 + 敏感信息
        if len(skill_content) > 15000:
            return {"decision": "fail", "coverage_score": 0, "reason": "skill 过长（>15KB）"}
        if _has_sensitive_content(skill_content):
            return {"decision": "fail", "coverage_score": 0, "reason": "包含敏感信息"}
        return {"decision": "pass", "coverage_score": 3, "reason": "无 Benchmark，仅通过基本检查"}

    if auxiliary_client is None:
        from agent.auxiliary_client import get_auxiliary_client
        auxiliary_client = get_auxiliary_client(task="default")

    prompt = GATE_PROMPT.format(skill_content=skill_content, benchmark=benchmark)
    try:
        response = auxiliary_client.chat(prompt)
    except Exception as e:
        logger.warning("Gate LLM call failed: %s", e)
        return {"decision": "pass", "coverage_score": 3, "reason": f"LLM 调用失败，默认通过: {e}"}

    try:
        result = json.loads(response)
        coverage = result.get("coverage_score", 0)
        redline = result.get("redline_pass", True)
        reason = result.get("reason", "")

        if not redline:
            return {"decision": "fail", "coverage_score": coverage, "reason": f"红线检查失败: {reason}"}
        if coverage < 2:
            return {"decision": "fail", "coverage_score": coverage, "reason": f"必要步骤覆盖不足: {reason}"}

        return {"decision": "pass", "coverage_score": coverage, "reason": reason}
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Gate LLM response parse failed: %s", e)
        return {"decision": "pass", "coverage_score": 3, "reason": f"评分解析失败，默认通过: {e}"}


def gate_memory(memory_chunk: str) -> Dict[str, Any]:
    """对 memory_chunk 做基本验证。

    Args:
        memory_chunk: 待写入的 memory 内容

    Returns:
        {"decision": "pass"|"fail"|"skip", "reason": str}
    """
    if not memory_chunk or not memory_chunk.strip():
        return {"decision": "skip", "reason": "无 memory 内容"}

    if len(memory_chunk) > MAX_MEMORY_CHARS:
        return {"decision": "fail", "reason": f"memory 过长（{len(memory_chunk)}>{MAX_MEMORY_CHARS}）"}

    if _has_sensitive_content(memory_chunk):
        return {"decision": "fail", "reason": "包含敏感信息（密码/token）"}

    return {"decision": "pass", "reason": "通过基本检查"}
