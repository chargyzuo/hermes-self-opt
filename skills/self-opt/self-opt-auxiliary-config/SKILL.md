---
name: self-opt-auxiliary-config
description: 配置 self-opt 项目所用的 auxiliary agent（模型），将低价模型分配给不需要强推理的辅助任务
version: 1.0.0
---

# self-opt-auxiliary-config

## 目标
修改 `~/.hermes/config.yaml` 中的 auxiliary 配置，将 `default` 和 `monitor` task 的 provider/model 从 auto 改为更便宜的模型（如 deepseek-v4-flash）。

## 触发条件
- 用户要求更改 self-opt 相关 auxiliary agent
- 检测到 current config 中 auxiliary 任务使用了高成本模型（如 V4 Pro）但任务本身不需要强推理

## 步骤

1. **读取当前配置**
   ```bash
   cat ~/.hermes/config.yaml | yq '.auxiliary'
   ```
   确认 `default` 和 `monitor` 的 provider/model 值。

2. **确定目标模型**
   推荐使用 `deepseek-v4-flash`（或同等低价模型）。若模型名未知，可查询可用模型列表。

3. **写入新配置**
   ```bash
   yq eval -i '
     .auxiliary.default.provider = "deepseek" |
     .auxiliary.default.model = "deepseek-v4-flash" |
     .auxiliary.monitor.provider = "deepseek" |
     .auxiliary.monitor.model = "deepseek-v4-flash"
   ' ~/.hermes/config.yaml
   ```

4. **验证配置生效**
   ```bash
   cat ~/.hermes/config.yaml | yq '.auxiliary'
   ```
   确保输出包含正确的 provider 和 model 值。

5. **记录变更**（可选）
   创建/更新技能文档（SKILL.md），记录本次变更以便后续查阅。

## 影响范围
- `self-opt-nightly` cron（mine.py / gate.py 步骤）
- `self-opt-distill` cron（mine.py / gate.py 步骤）
- `knowledge-pipeline-watchdog` 中的 classify_items.py（仅 monitor 任务）

## 注意事项
- 若以后有新的 auxiliary task 出现，需单独配置其 provider/model
- 确保目标模型的价格与任务复杂度匹配，避免过度设计