---
name: self-opt-auxiliary-config
description: "配置 self-opt 项目 cron 使用的 auxiliary LLM，用便宜模型替代主模型（deepseek-v4-pro）来降低 Mine/Gate/Classify 的 token 成本。"
category: self-opt
---

# Self-Opt Auxiliary Agent 配置

self-opt 项目的 cron 管线在 Mine（对话挖掘）和 Gate（质量校验）步骤中使用 Hermes 的 `auxiliary_client.call_llm` 调用 LLM，而不是主聊天模型。默认情况下没有配置 task-specific 模型，fall through 到主模型（deepseek-v4-pro），浪费 token。

## 涉及的 auxiliary task

| task | 使用者 | 用途 |
|------|--------|------|
| `default` | `mine.py` Step 2 | 从对话中提取 knowledge/memory/skill |
| `default` | `gate.py` gate_skill | skill 质量校验 |
| `monitor` | `classify_items.py` | 分类候选项紧急度 |

## 当前状态

所有 auxiliary task 配置均为 `provider: auto, model: ''`，最终解析到主模型 `deepseek-v4-pro`。

## 推荐配置

用 deepseek-v4-flash 做 auxiliary，比 V4 Pro 便宜很多，对于提取/分类任务够用：

```bash
hermes config set auxiliary.default.provider deepseek
hermes config set auxiliary.default.model deepseek-v4-flash

hermes config set auxiliary.monitor.provider deepseek
hermes config set auxiliary.monitor.model deepseek-v4-flash
```

如果 deepseek-chat 不可用，备选：
- `alibaba-coding-plan` + `qwen3.7-plus`（也便宜）
- `custom:fangzhou` + 火山方舟的便宜模型

## 验证

```bash
# 检查配置已写入
hermes config | grep -A3 "auxiliary:"

# 或者直接看 config.yaml
grep -A3 "default:" ~/.hermes/config.yaml | grep -A3 "auxiliary"

# 实际上可以手动触发一次 cron 跑一下验证
hermes cron run 249be072b03d
```

## 注意事项

- 配置修改后 cron 下个 tick 自动生效，无需重启
- `auxiliary.default` 不是内置 task，但 `_get_auxiliary_task_config` 支持任意 task name，直接用 `hermes config set` 写入即可
- mine.py 调的是 `call_llm(task="default")`，所以配 `auxiliary.default` 就生效
- 如果 deepseek-chat API 不可用，auxiliary_client 的 auto fallback 链会回退到主模型

## 回滚

```bash
hermes config set auxiliary.default.provider auto
hermes config set auxiliary.default.model ''
hermes config set auxiliary.monitor.provider auto
hermes config set auxiliary.monitor.model ''
```

## 相关文件

- `/Users/bytedance/script/hermes-self-opt/hermes_self_opt/mine.py` — 使用 `task="default"`
- `/Users/bytedance/script/hermes-self-opt/hermes_self_opt/gate.py` — gate_skill 用 auxiliary_client
- `/Users/bytedance/.hermes/hermes-agent/cron/scripts/classify_items.py` — 使用 `task="monitor"`
- `/Users/bytedance/.hermes/config.yaml` — auxiliary 配置
