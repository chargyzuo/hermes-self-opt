# Phase 2 端到端测试工作流

测试 Phase 2 管线（飞书文档 → normal/ → knowledge-build）的完整步骤。

## 工作流

### 1. 获取飞书排障文档

```bash
lark-cli docs +fetch --api-version v2 --doc "<URL或token>" --doc-format markdown
```

### 2. 蒸馏为 normal/ Markdown

**关键原则：只保留走向根因的关键路径，3-6步。跳过用户确认、截图沟通、失败猜测、重复验证。**

使用模板 A（故障排查类），输出到 `~/.hermes/knowledge/normal/<id>.md`：

```markdown
---
title: <原标题>
id: <英文kebab-case>
date: YYYY-MM-DD
tags: [协议, 设备, 故障类型]
source_doc: <token>
---

## 现象
<2-3句>

## 排查路径
<3-6步，只保留关键路径。跳过用户确认/截图/失败猜测/重复验证>

## 根因
<1-2句因果链>

## 方案
<具体可执行方案>

## 备注
<无效尝试、版本注意事项>
```

### 3. 验证 extract 解析

```bash
hermes self-opt extract --file ~/.hermes/knowledge/normal/<id>.md --json
```

检查 sections 是否包含 expected keys（symptoms, troubleshooting, root_cause, solution）。

### 4. 运行 Phase 2 管线

```bash
hermes self-opt knowledge-build -y --skip-gate
```

### 5. 验证产出

```bash
hermes self-opt knowledge                    # 统计: core total +N
hermes self-opt eventlog --type knowledge    # 查看 commit 日志
cat ~/.hermes/knowledge/core/full-<id>.yaml  # 检查 flow 链
```

## 常见陷阱

### 标题格式不匹配

Extractor 用 `startswith(alias)` 匹配标题。编号标题（`## 1. 问题描述`）strip 后变成 `1. 问题描述`，不以 `问题描述` 开头，会被静默跳过。

**修复**: 使用纯标题 `## 问题描述`、`## 排查过程`、`## 原因分析`、`## 解决方案`。

### check_source 爆炸

如果 normal/ Markdown 的排查路径包含 13 步（含用户沟通、截图确认、失败猜测），Phase 2 会生成 13 个 check_source，全部以描述代命令。

**修复**: 蒸馏阶段就只保留 3-6 个关键步骤。

### 回滚注意

`rollback_last_commit()` 会回滚 ALL committed entries，不只最后一轮。不要在生产环境使用 — 非常危险。

### gate-full tags 限制

原 schema 要求 `tags.minItems: 1`，但 distill 不生成标签。已修（移除 minItems），如后续增加 tag 生成可恢复限制。

### command 字段修复（→ 分隔符）

distill_knowledge.py 的 `_generate_check_source()` 原逻辑只有反引号匹配和全文截断，遇到"操作 → 结果"格式时 command 退化为全文。修复（commit `5e01e8a`）：优先级改为 反引号 > `→` 左侧 > `：` 右侧 > 全文截断。修复后 `ping nas.bytedance.net → 返回 IPv6` 的 command 变为 `ping nas.bytedance.net`。

## 真实测试案例

### 2026-06-28: NAS IPv6 SLAAC 间歇不通

- 源文档: `KgwSdek9eoJnEkxgtDJc3jzHnSd`
- 改前: 12 check_sources (13步排查流水账) → 改后: 5 check_sources (5步关键路径)
- tags: 空 → `[IPv6, SLAAC, 802.1X, VLAN, NAS, 华为]`
- core total: 401 (+14) → 回滚 → 恢复387 → 重做 → 394 (+7)
