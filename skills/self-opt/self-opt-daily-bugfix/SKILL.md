---
name: self-opt-daily-bugfix
description: 每日自动检查 self-opt 日志，发现 bug 后逐个修复，记录到 Obsidian 更新记录，提交到 GitHub
version: 1.2.0
provider: deepseek
model_id: deepseek-v4-flash
---

# Self-Opt 每日 Bug 修复

每天在 self-opt-router cron 完成后运行，自动检查日志、发现并修复 bug。

## 执行时机

每天 06:00（self-opt-router 05:00 的 1 小时后）。

## 执行步骤

### Step 0: 前置环境检查

```bash
# 确认 hermes-self-opt 项目可导入
python3 -c "import sys; sys.path.insert(0,'/Users/bytedance/script/hermes-self-opt'); from hermes_self_opt.eventlog import query; print('eventlog OK')" 2>&1

# 确认 git 远端可达
curl -s --max-time 5 https://api.github.com/repos/chargyzuo/hermes-self-opt 2>&1 | head -1
```

> ⚠️ `hermes self-opt` CLI 子命令未在 Hermes 主二进制注册。self-opt 管线通过 Python 模块直接调用。如果 `hermes self-opt eventlog` 报 `invalid choice: 'self-opt'`，使用 Python 回退。

### Step 1: 加载 skill 并检查日志

加载 `self-opt-event-log` skill，获取最新一天的日志数据。

```bash
# 优先尝试 CLI（hermes 插件已加载时有效）
hermes self-opt eventlog --days 1 --json 2>&1

# CLI 不可用时的 Python 回退
python3 -c "
import sys, json
sys.path.insert(0, '/Users/bytedance/script/hermes-self-opt')
from hermes_self_opt.eventlog import query, format_output
data = query(target='all', days=1, limit=50)
print(format_output(data))
" 2>&1

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
CHANGED=$(git diff --cached --stat | wc -l)
if [ "$CHANGED" -gt 0 ]; then
  git commit -m "fix: daily bugfix $(date +%Y-%m-%d)"
  # ⚠️ GitHub HTTPS push 在中国网络下可能超时（60s+）
  # 使用 http.postBuffer 和长 timeout 来应对
  git -c http.postBuffer=524288000 push origin main
fi
```

> ⚠️ **GitHub push 超时处理**: HTTPS push 到 github.com 在中国网络环境下经常超时（默认 30-60s）。三个缓解措施：
> 1. `git -c http.postBuffer=524288000 push origin main` — 增大 post buffer 减少分片协商延迟
> 2. 配合 `terminal(..., timeout=120)` 或更高 timeout 值
> 3. 如果 push 超时但远程仓库已包含该 commit（报 `cannot lock ref ... is at <sha>`），说明推送实际已成功，只需 `git fetch origin` 同步即可
>
> 验证：`hermes self-opt eventlog --days 1 | grep -E "(Error|FAILED|Traceback|401)"`

## 当前已知问题（上次 run 发现）

### 1. 🟡 GitHub HTTPS push 超时
- **现象**: `git push origin main` 在 30s-60s 超时，或报 `HTTP 401: invalid access token or token expired`
- **根因**: GitHub HTTPS git 协议在中国网络下延迟高，非 token 过期问题（`gh auth status` 始终有效）
- **缓解**: `git -c http.postBuffer=524288000 push origin main` + 120s terminal timeout
- **验证**: push 超时后 `git fetch origin` → 如果远程已包含本地 commit，说明推送实际成功
- **注意**: 2026-06-30 实测 — 120s timeout 最终成功推送

### 2. 🟡 eventlog CLI 偶发无输出
- **现象**: `hermes self-opt eventlog` 返回空，但 `~/.hermes/self-opt/logs/` 有 83 个 JSON 文件
- **待排查**: eventlog.py 读取路径或聚合逻辑
- **注意**: 本次运行 (2026-06-28) 未复现 — eventlog 正常返回 477 条事件。可能为偶发问题。
- **回退**: 使用 Python 直接调用 `eventlog.query(days=1, target='all')`

### 3. 🟡 Cron 调度漂移
- **现象**: self-opt 定时任务（03:00→nightly, 04:00→distill, 05:00→router）实际执行时间漂移 2-4 小时（2026-06-30 实测：07:03-07:12）
- **影响**: daily-bugfix（06:00）可能在 nightly 之前执行，读到过时数据
- **暂缓**: 不影响功能，优先级低。确认定时器本体原因后再修复。

## 辅助 LLM

使用 deepseek-v4-flash（通过 auxiliary_client.call_llm()）执行日志分析和方案生成，主模型负责执行修复。

## 注意事项

- 修复后必须 git commit
- 更新记录文件追加不覆盖（如果当天已有文件，追加新条目）
- 如果无新问题，生成一条「无新问题」记录即可
- core Knowledge 变更必须只生成报告，不自动写入
- 如果 cron job 无错误且日志无异常，可在报告中只输出一行「所有 cron 正常，无新问题」
