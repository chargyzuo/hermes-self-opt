---
name: self-opt-daily-bugfix
description: 每日读取 self-opt 日志，分类问题并修复，记录至 Obsidian，提交 GitHub
input:
  - self-opt-event-log 日志内容
  - 项目介绍文档（可选）
output:
  - 修复后的代码
  - 更新记录文件
steps:
  1. 加载 self-opt-event-log，读取最新 cron 输出
  2. 按严重级别分类问题：🔴 Critical（必须修复）、🟡 Warning（LLM 评估是否修复）、🟢 Info（仅记录不修复）
  3. 对于每个待修复问题，定位根因（查看日志、代码、配置）
  4. 若有需要，查看项目介绍文字（Agent学习/Agent self-optimization Frame/项目设计和实施/）
  5. 编写修复，验证通过后记录修复内容及日期
  6. 整理更新记录：将问题与修复写入 Obsidian 目录“Agent学习/Agent self-optimization Frame/更新记录/<日期>.md”
  7. git add → git commit → git push
  8. 如使用辅助代理，调用 auxiliary agent deepseek-v4-flash
