# Handover Workflow & Pending Items Tracking

## Handover Processing Workflow

When receiving a session handover document:

1. **Verify git state**: `git log --oneline -5` to confirm commits match
2. **Verify key files**: `wc -l` on modified files, verify specific code patterns exist
3. **Verify benchmark files**: `python3 -c "import json; ..."` to inspect JSON structure
4. **Save handover to Obsidian**: `Agent学习/Agent self-optimization Frame/交接文档/<date>_<topic>.md`
5. **Update memory**: Merge new facts into Hermes memory (batch operations preferred)
6. **Cross-reference pending items**: Compare against framework document, identify gaps

## Current Pending Items (as of 2026-06-27)

| # | 缺口 | 优先级 | 说明 |
|---|------|--------|------|
| 1 | Router 中文准确率 41% | 🟡 中 | 短查询（<10 字）字符少，分数爬不上 MIN_SCORE=0.3。可降阈值、加 jieba 分词。但框架标注路由层「暂不深入研究」 |
| 2 | Phase 4 路由层无自动监控 | 🔵 低 | selftune 参考「监控触发率，regression 自动回滚」，当前只实现手动 rollback |
| 3 | run-pipeline 不包含 --judge | 🔵 低 | run-pipeline 跳过了 LLM Judge 步骤 |
| 4 | run vs run-pipeline 命名混淆 | 🔵 低 | Phase 1 `run` 和 Phase 2 `run-pipeline` 容易搞混 |
| 5 | Execution Benchmark 未接入 SkillOpt 优化循环 | 🔵 低 | 基准已建，Rollout→Reflect→Edit 循环还没实现 |

## Framework Gaps (Missing from Pending Items)

| # | 框架内容 | 说明 |
|---|---------|------|
| A | 新 Skill 生成 Crystallization | 从 session 发现重复排障模式 → 自动生成新 skill（借鉴 GenericAgent）。完全未实现 |
| B | Gate-Full Staging→Review→Commit 完整流程 | gate_full.py 存在但待核实是否完整实现了框架的暂存→审核→验证→提交流程 |
| C | 用户反馈回流 | 纠正信号 → 标记待审查 → 空闲时优先处理。完全未实现 |

## Framework Document Path

```
Agent学习/Agent self-optimization Frame/Agent self-optimization框架构思.md
```

## Priority Alignment Rule

When reviewing pending items, always cross-reference with the framework document. If the framework says a component is "预留，暂不深入研究" (reserved, not deep research), downgrade its priority. Conversely, if the framework specifies a module that has no pending item, add it.
