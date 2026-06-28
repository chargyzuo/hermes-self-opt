---
name: self-opt-daily-bugfix
description: 每日自动检查 self-opt 日志，发现 bug 后逐个修复，记录到 Obsidian 更新记录，提交到 GitHub
version: 1.1.0
provider: deepseek
model_id: deepseek-v4-flash
---

# Self-Opt 每日 Bug 修复

每天在 self-opt-router cron 完成后运行，自动检查日志、发现并修复 bug。

## 执行时机

每天 06:00（self-opt-router 05:00 的 1 小时后）。

## 执行步骤

### Step 1: 加载 skill 并检查日志

加载 `self-opt-event-log` skill，获取最新一天的日志数据。

```bash
# 获取 eventlog
hermes self-opt eventlog --days 1 --json 2>&1

# 直接读取最新 cron 输出
ls -lt ~/.hermes/cron/output/5e8150bdbc75/ | head -1  # self-opt-router 最新输出
ls -lt ~/.hermes/cron/output/249be072b03d/ | head -1  # self-opt-nightly 最新输出
ls -lt ~/.hermes/cron/output/3fe034b67a26/ | head -1  # self-opt-distill 最新输出
```

### Step 2: 问题分类

| 严重级别 | 条件 | 处理方式 |
|----------|------|----------|
| 🔴 Critical | cron job 返回 error/failed 状态 | 必须修 |
| 🟡 Warning | Gate-Lite 评分解析失败、mine 失败等非致命问题 | LLM 评估是否修复 |
| 🟢 Info | 0 新内容、crystallize 无新模式 | 不修 |

### Step 3: 记录问题

在 Obsidian 中记录每个问题：

路径：`Agent学习/Agent self-optimization Frame/更新记录/<YYYY-MM-DD>.md`

格式：
```markdown
# Self-Opt 每日更新 — YYYY-MM-DD

## 问题

### 🔴 Bug 1: <标题>
- **来源**: <cron 名称 / phase>
- **现象**: <具体错误信息>
- **影响**: <对系统的影响>

## 修复

### ✅ Fix 1: <标题>
- **文件**: <修改的文件路径>
- **内容**: <修改了什么>
- **验证**: <如何验证修复>
```

### Step 4: 逐个修复

**🔴 Critical（必须修）**：
1. 定位根因：阅读相关代码（项目路径：`/Users/bytedance/script/hermes-self-opt/hermes_self_opt/`）
2. 若有需要可以查看项目文字介绍：`Agent学习/Agent self-optimization Frame/项目设计和实施/`
3. 编写修复：用 patch 或 write_file 修改代码
4. 验证修复：创建 ad-hoc 验证脚本（`/tmp/hermes-verify-*.py`），**必须直接 import 被修改的模块**（添加 `sys.path.insert(0, PROJECT)` + mock 外部依赖如 `agent.auxiliary_client`），不可用独立逻辑复现替代真实模块测试。运行验证脚本确认修复效果。
5. 记录修复到更新记录文件

**🟡 Warning（LLM 评估是否修复）**：
对每个 Warning 级别问题，用 LLM 评估：
- 是否影响系统正常运行？
- 是否会在未来恶化？
- 修复成本 vs 收益？
- 如果 LLM 判断应该修，按 Critical 流程处理；如果判断不修，记录到「已知问题（未修复）」并说明原因。

**🟢 Info（不修）**：记录到更新记录即可，不做修复。

### Step 5: 提交到 GitHub

```bash
cd /Users/bytedance/script/hermes-self-opt
git add -A
git status
# 只在有变更时提交
git diff --cached --stat | if [ $(wc -l) -gt 0 ]; then
  git commit -m "fix: daily bugfix $(date +%Y-%m-%d)"
  git push origin main
fi
```

## 当前已知问题（上次 run 发现）

### 1. 🟡 eventlog CLI 偶发无输出
- **现象**: `hermes self-opt eventlog` 返回空，但 `~/.hermes/self-opt/logs/` 有 83 个 JSON 文件
- **待排查**: eventlog.py 读取路径或聚合逻辑
- **注意**: 本次运行 (2026-06-28) 未复现 — eventlog 正常返回 477 条事件。可能为偶发问题。

## 辅助 LLM

使用 deepseek-v4-flash（通过 auxiliary_client.call_llm()）执行日志分析和方案生成，主模型负责执行修复。

## 注意事项

- 修复后必须 git commit
- 更新记录文件追加不覆盖（如果当天已有文件，追加新条目）
- 如果无新问题，生成一条「无新问题」记录即可
- core Knowledge 变更必须只生成报告，不自动写入
- 如果 cron job 无错误且日志无异常，可在报告中只输出一行「所有 cron 正常，无新问题」
