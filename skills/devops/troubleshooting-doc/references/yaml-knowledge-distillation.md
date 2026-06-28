# YAML 知识蒸馏管线 — v4 三类型原子化架构

> 将结构化 troubleshooting 文档（normal/）蒸馏为 agent 可直接引用的
> 结构化 YAML 知识库（core/）。设计文档见 Obsidian:
> `Agent学习/Agent self-optimization Frame/核心知识库存储设计.md`

## 三层知识库结构

```
~/.hermes/knowledge/
├── core/                    # YAML 核心知识（agent 排障时直接引用）
│   ├── _schema.yaml         # JSON Schema（三种类型各自校验）
│   ├── _index.yaml          # tags + triggers 倒排索引
│   ├── check-source/        # 检查原子
│   ├── decision-source/     # 结论原子
│   └── <id>.yaml            # full 类型（路由图）
├── normal/                  # Markdown 排障笔记（人+LLM 读）
└── self-opt/                # 优化管道工作区
    ├── benchmark.json
    ├── staging/             # 待审核
    └── committed/           # 已提交历史
```

## 三种 YAML 数据类型

### check_source — 检查原子

纯检查步骤，不含分支逻辑。可被多个 full 文档复用。

```yaml
id: check-velo-tunnel-mtu          # 命名规范: check-<动作>-<对象>
type: check_source
description: "检查 Velo 隧道 MTU 是否小于 ISE EAP challenge 报文"
command: "velo edge: debug.py --path 查隧道 MTU"
device_type: velo                   # 去重关键字段
tags: [velo, mtu, tunnel, ise, eap]
source: normal/huawei/mtu-8021x-failure.md
added: 2026-06-28
revised: []
```

### decision_source — 结论原子

排障推演的终点，包含根因和操作步骤。

```yaml
id: decision-increase-velo-overlay-mtu
type: decision_source
description: "Velo 隧道 MTU 不足导致 EAP 报文被丢弃"
action: |
  1. velo edge: debug.py --path 确认当前 MTU
  2. VCO 修改 Overlay MTU（需确认 Path MTU Discovery 状态）
  3. 隧道重建后验证 EAP 认证正常
tags: [velo, mtu, overlay, eap]
confidence: high                    # high / medium / low
source: normal/huawei/mtu-8021x-failure.md
```

### full — 路由图

声明式路由图，连接 check_source 节点。每步后根据 True/False 分支跳转。

```yaml
id: mtu-8021x-auth-failure
type: full
tags: [802.1X, MTU, MAC, Velo, RADIUS]
confidence: high
triggers:
  - "MAC 有线 802.1X 认证先弹出失败，过30-60s又自动成功"
  - "display aaa online-fail-record 显示 'Radius authentication reject'"
flow:
  - step: 1
    check: check-aaa-online-fail-record
    on_true:
      next_check: check-velo-tunnel-mtu
    on_false:
      redirect: 8021x-basic-config-check
  - step: 2
    check: check-velo-tunnel-mtu
    on_true:
      decision: decision-increase-velo-overlay-mtu
    on_false:
      next_check: check-radius-packet-capture
```

## 分支语义（三选一）

| 分支字段 | 值类型 | 含义 |
|----------|-------|------|
| `next_check` | check_source id | 继续排查，跳到下一个检查 |
| `redirect` | full id | 不匹配此故障，跳转到另一个 full 文档 |
| `decision` | decision_source id | 找到根因，执行方案，排障结束 |

**关键规则**：
- 每个 step 的 on_true 和 on_false 都必须有值（分支完整性）
- check 字段只能指向 check_source（不直接指向 decision 或另一个 full）
- redirect 产生跨文档引用，需要循环引用检测（DFS 三色标记法）

## 蒸馏流程

```
normal/<vendor>/<id>.md
  → 解析 YAML frontmatter + Markdown 正文
  → 去重（精确匹配 id → command+device_type → 语义相似度 > 0.92）
  → 生成 check_source（每个排查步骤）
  → 生成 decision_source（根因/方案）
  → 组装 full（链接 check_source/decision_source 的 id）
  → staging/（待人工审核）
  → Gate-Full（Schema + 引用完整 + 分支完整 + 循环引用）
  → Commit → core/
```

## 去重策略

**check_source**：
1. 精确匹配 id → 跳过
2. 精确匹配 command + device_type → 跳过
3. 语义相似度 > 0.92 且 tags 交集 ≥ 2 → 标记 candidate_duplicate

**decision_source**：同上，command 替换为 action。

## Gate-Full 校验项

1. **JSON Schema**：三种类型各自校验（必要字段 + 数据类型）
2. **引用完整性**：full 中 check/redirect/decision 指向的节点必须存在
3. **分支完整性**：flow 中每个 step 必须同时有 on_true 和 on_false
4. **循环引用**：DFS 遍历 redirect 链，只检查 full→full 跨文档引用

## 实施注意

- SOP 类文档（无排障闭环）无法生成 full — 只产生 check_source
- 先走通 1 篇文档的完整管线，再批量处理
- 推荐先手写静态提取脚本验证管道，再接入 LLM 批量蒸馏
