# Skill Benchmark 设计

## 背景

现有的 `~/.hermes/knowledge/self-opt/benchmark.json` 是**知识库 Benchmark**（5 条排障考题），用于 Gate-Lite / Gate-Full 对知识库条目做 LLM 评分（必要步骤覆盖 + 红线检查）。

但它不是 Skill Benchmark。SkillOpt 框架中的 Skills 优化流程（Rollout → Reflect → Edit → Gate-Lite）需要两类独立的 benchmark。

## 两层 Benchmark 结构

### Layer 1: Skill Router Benchmark（路由准确性）

测试 Phase 4 Router 在自然语言查询 → skill 名称映射上的准确率。

**用途**：
- 测量当前 Router 准确率（query() 返回的 top-1 是否等于 expected_skill）
- 检测 skill description 变化后的 regression
- 校准 `MIN_SCORE` 阈值
- 作为 Phase 4「自动监控→自动回滚」的数据基础

### Layer 2: Skill Execution Benchmark（技能执行评估）

测试每个排障 skill 在给定场景下是否覆盖正确步骤、避开红线。

**用途**：
- Rollout 阶段：用 LLM 跑 skill → 产出步骤列表 → 对比 expected
- Reflect 阶段：没覆盖的 required_steps → 触发 skill 内容优化
- Gate-Lite：优化后重新跑，确保不倒退（score ≥ 上次）

## 与现有 benchmark.json 的关系

- `benchmark.json` → 保留，用于 **知识库条目** 的 Gate-Lite/Gate-Full 评分
- Skill Benchmark → 独立文件 `~/.hermes/knowledge/self-opt/skill_*.json`
- 两者互不替代，用途不同

## ✅ 已实现（2026-06-27）

**文件创建**：

```bash
~/.hermes/knowledge/self-opt/skill_router_benchmark.json      (10 skills, 49 queries)
~/.hermes/knowledge/self-opt/skill_execution_benchmark.json   (8 skills, 56 required_steps + 30 redlines)
```

**Gate-Lite 接入**：`gate_skill()` 新增 `skill_name` 参数，优先加载 `skill_execution_benchmark.json` 中匹配的条目，未匹配降级到知识库 benchmark。

安装时注意 skill 名对齐——Router 索引用 frontmatter `name:` 字段而非目录名，benchmark 条的 `skill` 字段必须匹配 frontmatter name。

| Skill | Directory | Frontmatter name |
|-------|-----------|-----------------|
| huawei-mac-auth-debug | `huawei-mac-auth-debug/` | `huawei-mac-auth-debug` |
| MAB Fallback | `mab-fallback-dot1x-diagnosis/` | `MAB Fallback 802.1X 故障诊断` |
| Detect Service | `detect-running-service-before-recommend/` | `Detect Running Service Before Recommend` |

Execution Skill Benchmark 的 `skill` 字段也已同步修正。

### 路由器实测结果

修 CJK 字符级匹配后，Router Benchmark：

```
top-1: 20/49 = 40.8%
top-3: 23/49 = 46.9%
NO_MATCH: 17, wrong skill: 12
```

从修之前的 1/49（2%）大幅提升，但仍有 **59% 失败**。主要根因：

1. **CJK 字符级匹配粒度太粗**：短查询（<10 字）字符少，重叠率低，分数爬不上 0.3。如「AP监控模式黄灯」6 字中只与 desc 重叠 2 个字，得分 0.167。
2. **纯英文 desc 对中文查询不友好**：`aruba-ap-troubleshooting`（纯英文 desc）匹配不了中文查询，`huawei-switch-auth-troubleshooting`（纯英文 desc）同理。
3. **skill 间描述语义重叠**：`huawei-mac-auth-debug` vs `MAB Fallback` 都含「交换机」「认证」「MAC」，CJK 字符级匹配无法区分。

**待做项**：降 `MIN_SCORE` / 加 jieba 分词 / 改写纯英文 skill description / 尝试其他分词策略。

## 下一步（待做）

1. 🔲 修复 Router 中文准确率 41% → target 80%+（jieba 分词 / 降阈值 / 改写英文 desc）
2. 🔲 Execution Benchmark 接入 SkillOpt Rollout → Reflect → Edit 循环
