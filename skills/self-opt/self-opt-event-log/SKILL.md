---
name: self-opt-event-log
description: 查看 self-opt 项目所有事件日志（skills 变动、knowledge 变动、cron 运行记录）
---

# Self-Opt 事件日志查看

查看 Agent Self-Optimization 项目的全部事件记录，覆盖三个数据源：

| 数据源 | 路径 | 内容 |
|--------|------|------|
| change.log | `~/.hermes/self-opt/change.log` | skill/knowledge 变动（created/updated/committed） |
| logs/*.json | `~/.hermes/self-opt/logs/` | Phase 1/3/4 cron 运行日志 |
| pipeline_watchdog.log | `~/.hermes/knowledge/self-opt/pipeline_watchdog.log` | Phase 2 watchdog 日志 |

## CLI 命令

```bash
# 查看全部事件（最近 7 天，最多 50 条）
hermes self-opt eventlog

# 只看 skill 变动
hermes self-opt eventlog --type skill

# 只看 knowledge 变动
hermes self-opt eventlog --type knowledge

# 只看 cron 运行事件
hermes self-opt eventlog --type cron

# 最近 30 天
hermes self-opt eventlog --days 30

# JSON 输出（供脚本消费）
hermes self-opt eventlog --json
```

## 输出格式

```
Self-Opt 事件日志 — 共 N 条（显示 M 条）
============================================================
📋 2026-06-27 18:01 | skill/updated | huawei-mab-pre-auth-troubleshoot | source=...
📚 2026-06-27 17:00 | knowledge/committed | full-xxx | type=full
⏱ 2026-06-28 02:00 | cron/distill | Phase3-distill | date=2026-06-28 entries=10
⏱ 2026-06-28 02:00 | cron/router-build | Phase4-router | indexed=145 ms=227.1
⏱ 2026-06-27 22:57 | cron/watchdog | Phase2-watchdog | detected 1 changed files...
============================================================
数据源: change.log + logs/*.json + pipeline_watchdog.log
```

## change.log 格式

每行一个事件，字段用 ` | ` 分隔：
```
timestamp | target | action | name | source=... | path=... | detail=...
```

- target: `skill` 或 `knowledge`
- action: `created` / `updated` / `committed` / `skipped`
- 写入时机：`write_skill()` 或 `commit_to_core()` 调用时自动追加

## 直接读取（不用 CLI）

```bash
# change.log 全量
cat ~/.hermes/self-opt/change.log

# 最近日志文件
ls -lt ~/.hermes/self-opt/logs/ | head -5

# 某天的 Phase 1 运行日志
cat ~/.hermes/self-opt/logs/20260627_175304.json | python3 -m json.tool

# watchdog 日志
cat ~/.hermes/knowledge/self-opt/pipeline_watchdog.log
```
