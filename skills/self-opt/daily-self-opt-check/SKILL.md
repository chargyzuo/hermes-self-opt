---
name: daily-self-opt-check
description: "每日自我优化检查流程：检查 cron 运行状态、排障 git 问题、生成报告。"
version: 1.0.0
tags: [self-opt, daily, check, git, report]
---
# Daily Self-Opt Check

## 步骤

1. **检查 cron 状态**
   - 读取各 cron（self-opt-distill、self-opt-router、self-opt-nightly）最新输出文件，确认运行时间和正常结束。
   - 检查 watchdog 和 sync-memory 日志是否为 silent（无异常）。

2. **检查 git 推送状态**
   - 执行 `git status` 和 `git push --dry-run`，确认远程可达。
   - 若遇到 HTTP 401 等 token 过期错误，尝试重新认证或重试推送。

3. **记录当日更新**
   - 将当日变更提交至 git，并创建 Obsidian 格式的更新记录。

4. **清理临时文件**
   - 删除过程中生成的临时文件。

5. **输出报告**
   - 汇总各 cron 运行状态、已知问题及处理结果。