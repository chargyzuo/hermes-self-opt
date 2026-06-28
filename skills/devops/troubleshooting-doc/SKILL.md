---
name: troubleshooting-doc
description: 创建网络与系统故障排查文档，结构化记录背景、拓扑、配置、排查过程、根因、解决方案
version: 1.0.0
author: Hermes Agent
platforms: [macos, linux]
metadata:
  hermes:
    tags: [troubleshooting, documentation, network, case-study]
---

# Troubleshooting 排查文档写作

创建标准化排查文档，格式兼容 Obsidian 笔记。适用于网络设备故障、系统配置异常、认证/审计日志问题等场景。

## 触发条件

- 用户完成一个完整的排查流程后要求"总结/写文档"
- 用户要求"生成排查文档/troubleshooting 文档"
- 调试过程涉及多个步骤（3+ 工具调用）且需要归档
- 用户报告 ping 目标为 198.18.0.x 或 DNS 服务器为 198.18.0.2 时，先参考 `references/mihomo-clash-fakeip-diagnostic.md`（Mihomo/Clash Meta Fake-IP 劫持快速诊断）

## 排查准备：先识别设备类型

**首次连接任何设备，第一条命令必须是识别厂商和型号** — 永远不要根据 IP、用户描述、或「上一次排查的也是华为」来假设设备类型。

- 华为：`dis version` → 主机名含 CE/NE/S 等
- Cisco：`show version` → 主机名含 C9200/C9300/WS/ISR 等
- Arista：`show version` → 主机名含 DCS 等

主机名本身就是厂商线索（如 `NOHRM01-...-C9200-...` = Cisco Catalyst 9200）。忽略主机名直接按华为语法发命令会导致所有诊断命令白跑一轮。

详细厂商命令对照：`skill_view(name="troubleshooting-doc", file_path="references/switch-diagnostic-commands.md")`

## 文档结构

### 标题格式

```
# 标题 - 问题简述
```

格式：`<设备/平台> <问题现象>`，如 `Arista 802.1X 认证后 Accounting 无 IP 排查`

### 段落结构

#### 1. 背景

描述问题现象、影响范围、用户/设备信息。简明扼要。

```
## 背景

用户 xxx (MAC/ID) 接入某设备，出现 xxx 问题。设备型号/版本 xxxx。
```

#### 2. 网络拓扑（网络类问题必填）

用文字拓扑图描述：

```
终端 (IP) → 接口 → 设备
                       → 上联 → 上游设备
                                → 服务器 (IP:PORT)
```

标注 VLAN、VRF、IP 网段等关键信息。

#### 3. 初始配置

收集相关配置并格式化展示。使用代码块 ` ``` ` 包裹。

```
### AAA
### dot1x
### 接口配置
### 全局配置
```

参考已有 Obsidian 笔记的 `[[Arista接入交换机dot1x配置]]` 等存档配置文档。

#### 4. 排查过程

按时间/逻辑顺序分段，每个阶段一个 h3 标题。

```
### 阶段一：xxx
### 阶段二：xxx
...
```

每个阶段包含：
- 执行了什么命令
- 关键输出摘录（只引用、不编造）
- 发现了什么（用 **发现** 高亮）

如果有对比（基线/正常设备 vs 故障设备），用表格：

```
| 项目 | 问题设备 | 基线设备 |
|------|---------|---------|
| xxx  | xxx     | xxx     |
```

#### 5. 根因

简洁明了，1-3 句话。用 **加粗** 突出根因。

```
## 根因

**xxx 配置缺失** 导致 xxx。
```

可附上简要的事件链/流程图。

#### 6. 解决方案

如果存在多个方案，用列表区分并注明推荐方案。

```
### 方案一：xxx（推荐）

配置步骤（用代码块）

### 方案二：xxx

...
```

包含注意/警告事项。

#### 7. 验证命令

列出排查和验证用的关键命令，分类整理。

```
## 验证命令
### 基础诊断
### 配置检查
### 日志
```

#### 8. 相关文档

列出引用过的飞书文档、Obsidian 笔记链接。

## 相关文档

- [文档标题](飞书URL)
- [[关联笔记名称]]

## 进阶：YAML 知识蒸馏管线

当 troubleshooting 文档积累到一定规模后，可进一步蒸馏为结构化 YAML 知识库
供 agent 排障时直接引用。详见 `references/yaml-knowledge-distillation.md`。

#### 9. 诊断命令

列出排查和验证用的关键命令，分类整理。常用厂商命令速查见 `references/switch-diagnostic-commands.md`。

```
## 验证命令
### 基础诊断
### 配置检查
### 日志
```

## 写作规则

### 禁止
- 编造命令输出或数据 — 所有输出必须来自实际工具执行
- 使用模糊表述如"可能"、"大概" — 结论必须明确
- 在文档中插入角色扮演或元指令

### 必须
- 每一条发现对应一条工具执行结果
- 对比基线时有表格
- 引用内部文档时标注来源
- 文档写入 Obsidian Vault/Troubleshooting/

### 格式规范
- 代码块用 ` ``` ` 包裹，标注语言（`bash`/`text`/`config`）
- 关键发现用 **加粗**
- 命令和配置参数用 `行内代码`
- 使用 `|` 表格对齐对比项
- 日期格式统一为 `YYYY-MM-DD`
