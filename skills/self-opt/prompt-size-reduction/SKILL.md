---
name: prompt-size-reduction
description: 分析和减少 Hermes Agent 初始系统提示的大小
---

# Prompt Size Reduction

## 适用场景
初始会话系统提示过大，影响上下文窗口或响应速度时。

## 步骤

### 1. 分析当前提示构成
- 使用 `python3 -c "..."` 脚本或 `agent.system_prompt.build_system_prompt_parts` 获取各块字符数。
- 识别 Skills 索引、工具指引、环境探测等大块。

### 2. 调整配置项
- `agent.tool_use_enforcement: false`（若不需要强制工具使用指导）
- `agent.environment_probe: false`（若不需要 Python 环境探测）
- `memory.memory_char_limit: 500`（降低记忆上限）
- 关闭其他非必要指引如 `task_completion_guidance`、`parallel_tool_call_guidance`。

### 3. 禁用非核心技能
- 列出当前启用技能，排除一次性配置、不常用的排障技能。
- 在 `config.yaml` 的 `skills.disabled` 列表中添加技能名（如 `obsidian`、`aruba-ap-troubleshooting`）。
- 注意：禁用后技能从索引中移除，但可通过 `/skill` 手动加载。

### 4. 验证结果
- 设置环境变量 `HERMES_PLATFORM=cli`，再运行大小分析脚本。
- 确认缩减量和各块占比，确保目标达成。

### 5. 新会话生效
- 执行 `/reset` 或新开会话以应用新的系统提示。