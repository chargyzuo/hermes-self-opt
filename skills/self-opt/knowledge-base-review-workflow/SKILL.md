---
name: knowledge-base-review-workflow
version: 1.0
description: 确保知识库 YAML 写入 core 前经过用户审查的流程
steps:
  1. 运行 `hermes self-opt distill-knowledge` 生成 staging/
  2. 运行 `hermes self-opt review` 展示变更摘要，等待用户确认
  3. 用户输入 y：设置 review_state = approved
  4. 用户输入 n：删除 staging/ 或手动干预
  5. 运行 `hermes self-opt commit`（自动检查 review 状态）
  6. 若未 review：报错，提示先 review
  7. 若已 review：执行 commit_to_core，完成后同步导出 _schema.yaml
---
