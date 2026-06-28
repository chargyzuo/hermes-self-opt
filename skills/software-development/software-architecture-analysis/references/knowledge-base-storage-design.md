# 核心知识库存储设计

> 核心知识库是以 LLM 和机器可读为首要目标的设计，人类一般不会直接查阅。因此使用纯 YAML + JSON Schema 校验。

## 设计原则

1. **机器优先** — 格式要易于 LLM 生成和解析，字段固定，嵌套浅
2. **Schema 约束** — 每次写入前用 JSON Schema 校验，不符合就自动修复或拒绝
3. **无冗余字段** — 不存背景、描述、上下文，只存触发条件 + 判断逻辑 + 结论
4. **Git 友好** — 每一条一个 `.yaml` 文件，自然支持行级 diff

## 存储格式

### 单条知识

```yaml
# poe-power.yaml
id: poe-power
type: symptom-to-decision
tags: [AP, PoE, power]

triggers:
  - AP LED orange
  - AP cannot power up
  - AP randomly reboots

checks:
  - port power budget
  - cable continuity
  - PSE output

decisions:
  - condition: port power < AP min
    action: replace port or use injector
    confidence: high
  - condition: cable test fail
    action: replace cable
    confidence: high
  - condition: port power OK & cable OK & AP still off
    action: replace AP
    confidence: medium
```

### Schema 定义

```yaml
# _schema.yaml
type: object
required: [id, type, tags, triggers, decisions]
properties:
  id:
    type: string
    pattern: "^[a-z0-9-]+$"
  type:
    enum: [symptom-to-decision, symptom-tree, root-cause-map]
  tags:
    type: array
    items: { type: string }
    minItems: 1
  triggers:
    type: array
    items: { type: string }
    minItems: 1
  decisions:
    type: array
    items:
      type: object
      required: [condition, action, confidence]
      properties:
        condition: { type: string }
        action: { type: string }
        confidence: { enum: [high, medium, low] }
```

## 目录结构

```
~/.hermes/knowledge/core/
├── _schema.yaml         # JSON Schema
├── _index.yaml          # 索引
├── poe-power.yaml
├── dhcp-failure.yaml
├── vlan-mismatch.yaml
└── ...
```

### 索引文件

```yaml
# _index.yaml
entries:
  - id: poe-power
    triggers: [AP LED orange, AP no power, AP reboot]
    tags: [AP, PoE, power]
    priority: high
  - id: dhcp-failure
    triggers: ["cannot get IP", "DHCP timeout", "AP stuck at 0.0.0.0"]
    tags: [DHCP, VLAN, IP]
    priority: high
```

## LLM 使用方式

### 查询

```text
symptom: AP LED orange，PoE端口显示errdisable
core_knowledge: <读取 ~/.hermes/knowledge/core/_index.yaml 匹配到的条目>
LLM 根据知识库给出排障建议
```

### 写入

```text
请将以下排障经验格式化为 YAML，字段需严格遵循 schema。
不符合 schema 的内容将被拒绝。

schema: <_schema.yaml 内容>
raw session: <session 文本>
```

## 后续方向

| 方向 | 说明 | Priority |
|------|------|----------|
| Schema 校验自动化 | 写入前自动跑 YAML 校验，不通过就提示 LLM 重试 | P1 |
| 条件索引 | 不只是 tag 匹配，还能根据 triggers 做语义匹配 | P2 |
| 置信度衰减 | 长期未验证的知识自动降低 confidence | P3 |
| 多源合并 | 多条知识描述同一故障时自动合并 | P3 |
