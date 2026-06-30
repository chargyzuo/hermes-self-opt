---
name: check-initial-prompt-script
version: 1.0
description: 创建用于查看当前 AI 会话初始系统提示词（system prompt）完整内容的 Shell 脚本
author: assistant
triggers:
  - 用户请求 “写一个查看初始会话prompt内容的脚本”
steps:
  - 1. 在用户目录下创建脚本文件（如 ~/script/check_prompt_content.sh）
  - 2. 脚本核心逻辑：调用 Hermes Agent 的内部函数或通过 API 获取当前 session 的 build_system_prompt_parts() 输出
  - 3. 输出应包括三层级（Stable/Context/Volatile）的字符数、token 数，以及每个段落的全文
  - 4. 支持参数：--less 分页查看、--save=<file> 保存到文件
  - 5. 确保脚本可执行（chmod +x）
  - 6. 提示用户使用方法并展示示例
