"""
mine.py — Step 2: 用 auxiliary LLM 从对话中提取有价值的信息。

职责：
  - 接收 Harvest 输出的对话文本
  - 调 auxiliary LLM 提取三样东西：
    1. knowledge_chunk（排障逻辑 YAML）
    2. memory_chunk（用户偏好/习惯）
    3. skill_candidate（可复用的 workflow）
  - 输出结构化 JSON
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

MINE_PROMPT = """你是一个 AI agent 的自我进化分析器。分析以下对话内容，提取三条信息。

## 对话内容
{dialog}

## 输出要求
以 JSON 格式输出，严格遵循以下结构：

```json
{{
  "has_content": true/false,
  "knowledge_chunk": "排障逻辑的 YAML 格式，包含 triggers/checks/decisions 字段；如果没有排障内容则为空字符串",
  "memory_chunk": "关于用户的一句话偏好/习惯/环境变更；如果没有则为空字符串",
  "skill_candidate": {{
    "name": "skill 名称（小写连字符），如果能提炼出可复用 workflow 的话；否则为空字符串",
    "content": "SKILL.md 完整内容，包含 YAML frontmatter 和 markdown 步骤；否则为空字符串"
  }}
}}
```

## 注意事项
- 普通对话（没有排障内容）请返回 has_content=false，三个字段都为空
- 每条信息控制在 500 字以内
- knowledge_chunk 只保留逻辑骨架，不要背景描述
- memory_chunk 只记录关于用户的事实（偏好、习惯、环境）
- skill_candidate 只在发现明确的可复用 workflow 时才填写
"""


def mine(
    dialog: str,
    *,
    auxiliary_client=None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """用 LLM 从对话中提取知识、记忆和 skill。

    Args:
        dialog: Harvest 步骤输出的对话文本
        auxiliary_client: Hermes 的 auxiliary client 实例（可选）
        model: 指定模型名（可选）

    Returns:
        包含 knowledge_chunk, memory_chunk, skill_candidate 的字典

    Raises:
        RuntimeError: auxiliary LLM 调用失败
        json.JSONDecodeError: LLM 输出非合法 JSON
    """
    if auxiliary_client is None:
        auxiliary_client = _get_default_auxiliary_client()

    prompt = MINE_PROMPT.format(dialog=dialog)

    kwargs = {}
    if model:
        kwargs["model"] = model

    try:
        response = auxiliary_client.chat(prompt, **kwargs)
    except Exception as e:
        raise RuntimeError(f"Auxiliary LLM call failed: {e}") from e

    result = _parse_response(response)
    return result


def _get_default_auxiliary_client():
    """获取默认 auxiliary client。"""
    try:
        from agent.auxiliary_client import get_auxiliary_client
        return get_auxiliary_client(task="default")
    except ImportError:
        logger.error(
            "Cannot import get_auxiliary_client. Make sure you're running "
            "inside Hermes' Python environment (source venv/bin/activate)"
        )
        raise


def _parse_response(response: str) -> Dict[str, Any]:
    """解析 LLM 返回的文本，提取 JSON。"""
    # 尝试直接解析
    text = response.strip()
    if text.startswith("```"):
        # 去掉 markdown 代码块标记
        lines = text.split("\n")
        cleaned = []
        in_code = False
        for line in lines:
            if line.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                cleaned.append(line)
        text = "\n".join(cleaned)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # 第一次失败：尝试找 JSON 块
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(
                    f"Cannot parse LLM response as JSON: {e}",
                    text,
                    e.pos,
                )
        else:
            raise json.JSONDecodeError(
                "No JSON found in LLM response",
                text,
                0,
            )

    # 确保字段都存在
    return {
        "has_content": result.get("has_content", False),
        "knowledge_chunk": result.get("knowledge_chunk", ""),
        "memory_chunk": result.get("memory_chunk", ""),
        "skill_candidate": result.get("skill_candidate", {"name": "", "content": ""}),
    }
