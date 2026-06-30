---
name: create-agent-prompt-inspection-script
description: 为 Hermes Agent 创建一个 bash 脚本，用于查看初始会话 system prompt 的完整内容（三级层级结构）。需要知道代理的配置文件路径和脚本存放目录。
triggers:
  - user 要求“写一个查看初始会话prompt内容的脚本”
steps:
  - 确定脚本存放路径（通常为 ~/script/check_prompt_content.sh）
  - 编写脚本：调用 `build_system_prompt_parts()` 函数或模拟其输出，打印 Stable / Context / Volatile 三层内容，并包含概要统计（模型、Provider、各层级 token 数、配置开关状态）
  - 添加可选参数：--less（分页）、--save=<file>（保存到文件）
  - 给脚本可执行权限：chmod +x ~/script/check_prompt_content.sh
  - 告知用户用法示例
