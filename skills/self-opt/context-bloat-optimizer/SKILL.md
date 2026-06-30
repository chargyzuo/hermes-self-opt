---
name: context-bloat-optimizer
version: 1.0
description: 分析并优化AI agent新session的上下文膨胀，通过禁用多余技能和裁剪prompt来节省token
---
# Context Bloat Optimizer

## 步骤
1. 获取当前config.yaml中的技能列表和agent prompt配置
2. 识别上下文膨胀的主要来源（技能描述、agent guidance prompts等）
3. 根据用户核心需求（如网络/开发/笔记），确定需要保留的技能类别，生成disabled列表
4. 应用禁用配置，同时裁剪agent guidance prompts中不必要的guidance
5. 验证配置生效，计算token节省量
6. 输出优化总结，包括更改文件和预估节省token数