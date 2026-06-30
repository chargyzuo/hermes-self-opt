---
name: reduce-initial-prompt-overhead
description: 系统分析和缩减 agent 初始系统提示（system prompt）的大小，包括配置调整和技能禁用。
author: assistant
platforms: [cli]
---
# 系统提示精简工作流

## 步骤

1. **分析 prompt 组成**
   - 识别所有构建 prompt 的模块：身份、hermes指引、任务完成指引、并行工具调用指引、工具指引（memory/session/skills）、steer通道、环境探测、技能索引等。
   - 建议使用脚本或内部API获取各块字符数。

2. **检查当前技能启用列表**
   - 查看总技能数和当前平台禁用的技能数（`hermes skill list --enabled` 或通过配置）。
   - 标记可禁用的技能：一次性配置类、非核心排障类、用户已不再使用的技能。

3. **调整配置项**
   - 设置 `agent.tool_use_enforcement: false`（若命中deepseek规则可节省约800 chars）。
   - 设置 `agent.environment_probe: false`（节省约200 chars）。
   - 降低 `memory.memory_char_limit` 至合理值（如500，原2200）。
   - 若适用，关闭 `agent.task_completion_guidance` 和 `agent.parallel_tool_call_guidance`。

4. **禁用非必要技能**
   - 逐项确认技能名称，将其加入 `cli.disabled_skills` 列表。
   - 通过修改 `config.yaml` 或使用 `hermes config set` 命令。

5. **验证效果**
   - 在新会话或使用脚本（需设置 `HERMES_PLATFORM=cli`）重新构建 prompt，对比优化前后的总字符数和技能索引占比。
   - 确保不低于核心功能所需的最小提示（身份、hermes指引、steer指引、已加载工具的指引）。

## 预期结果
- 初始 prompt 减少 40-60%，技能索引显著缩短。
- 不影响 agent 的核心行为和工具使用。