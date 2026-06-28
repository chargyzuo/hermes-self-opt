# Feishu 排障文档 → 知识库 Markdown 蒸馏

从飞书排障文档目录批量读取子文档，去重后蒸馏为结构化 Markdown，存入 `~/.hermes/knowledge/normal/<厂商>/<id>.md`。

## 触发场景

- 用户给出一个飞书文档 URL，该文档是一个分层目录（含多个 `<cite file-type="docx">` 子文档链接）
- 用户要求"萃取/蒸馏/整理"飞书排障文档
- 用户要求"将飞书案例转成排障笔记"

## 前置条件

1. lark-cli 已通过用户身份认证（`--as user`），有目标文档的读权限
2. 目标目录已创建：`mkdir -p ~/.hermes/knowledge/normal/{huawei,arista,network,misc}`
3. Python 环境可用（需 `html` 标准库做 `html.unescape()`）

## 步骤

### 1. 读取主目录文档，提取子文档列表

```bash
lark-cli docs +fetch --api-version v2 --doc "<doc_url_or_token>" --format pretty
```

注意：`--scope` 有效值为 `full`、`outline`、`range`、`keyword`、`section`，**不是** `all`。省略 `--scope` 即读整篇。

从返回的 XML 中提取所有 `<cite doc-id="..." file-type="docx" title="...">` 标签，获得子文档的 token 和标题。

**推荐用 Python 正则提取并去重：**
```python
import re
pattern = r'doc-id="([A-Za-z0-9]+)"\s+file-type="docx"\s+title="([^"]*)"'
matches = re.findall(pattern, xml_content)
# 按 doc-id 去重
seen = set()
docs = [(did, title) for did, title in matches if not (did in seen or seen.add(did))]
```

### 2. 去重

同一个 `doc-id` 可能在主文档中出现多次（行和备注列各一次）。用 token 去重，每个文档只处理一次。

### 3. 读取每个子文档

```bash
lark-cli docs +fetch --api-version v2 --doc "<doc_token>" --format pretty
```

**重要：使用 `--format pretty`（纯 XML 文本输出），而非 `--format json`。**
`--format pretty` 直接返回可读的 XML 内容，无需解析 JSON 提取 `data.document.content`。

通过 Python 的 `html.unescape()` 处理转义后的 XML 内容：
```python
import html
content = html.unescape(raw_xml)
```

### 4. 蒸馏为结构化 Markdown

**判断文档类型，选择对应模板：**

#### 模板 A：故障排查类（标题含【解决】/【未解决】/IT-单号等）

```markdown
---
title: <从原标题提取，去噪>
id: <英文小写连字符，从标题提炼>
date: YYYY-MM-DD
tags: [协议, 设备, 故障类型]  # 3-6个
source_doc: <飞书文档token>
---

## 现象
<2-5句，含受影响范围、症状、频率>

## 排查路径
<只保留走向根因的关键路径，3-6步。跳过用户确认、截图沟通、失败猜测、重复验证。格式：操作 → 结果>

## 根因
<因果链，1-2句>

## 方案
<1句>

## 操作
<编号列表，可执行级别，标明设备>

## 备注
<版本、注意事项、无效尝试汇总>
```

#### 模板 B：SOP/指南/手册类（无特定故障描述）

```markdown
---
title: <文档标题>
id: <英文小写连字符>
date: YYYY-MM-DD  # 无则留空
tags: [协议, 设备, 类型]
source_doc: <飞书token>
---

## 概述
<文档目的和适用范围，2-3句>

## 流程
<编号步骤，可执行级别，标明设备>

## 命令参考
<具体命令，注明设备型号>

## 注意事项
<关键提醒、安全约束>

## 备注
<版本信息、关联文档>
```

### 5. 蒸馏要点

| 要素 | 做法 |
|------|------|
| **去噪** | 丢弃聊天寒暄、\\<img\\> 截图描述文字、重复讨论、与排障无关的段落 |
| **保留** | 具体命令、错误信息、数值、设备名、接口名、IP/MAC/IT 工单号 |
| **排查路径** | **只保留走向根因的关键路径**。跳过：（1）用户确认/复述/截图沟通环节（2）与根因无关的岔路排查和失败猜测（3）重复验证步骤。格式：操作 → 结果，3-6步即可 |
| **操作可执行** | 用具体操作描述，如「VCO 修改 Overlay MTU」而非「改 MTU」 |
| **id 生成** | 从标题中文提炼核心关键词，拼音直译。如「PDI角色用户有线无法认证」→ `pdi-youxian-wufa-renzheng`；如有标题含 IT-单号可加入如 `pdi-youxian-wufa-renzheng-it8403549` |
| **tags** | 从内容提取协议（802.1X/RADIUS/DHCP/OSPFv3）、设备品牌（华为/Arista/Aruba/白盒交换机）、故障类型（认证/DNS/路由/MTU/BUG） |
| **厂商目录** | 见下方"厂商目录判定"表 |
| **date** | 从标题中的日期格式提取，如 `20231214`；出现在标题不同位置（开头/中间），用正则 `\d{8}` 或 `\d{6}` 提取 |

**厂商目录判定：**

| 标题/内容关键词 | 目录 |
|----------------|------|
| 华为交换机、华为SDN、OSPFv3 MTU (华为设备) | `huawei/` |
| Arista 交换机、Arista SDN、Arista 接入交换机、PDI (Arista) | `arista/` |
| Aruba、AP (无线)、AirGroup、Guest、AC BUG、无线网络 | `arista/` |
| Velo/SDWAN/VeloCloud/VCO | `network/` |
| 专线链路、网络告警、停电恢复、DNS、Bluecat/DHCP | `network/` |
| NAS/445端口、IPv6、防火墙、SDN 环境TS | `network/` |
| 终端接入、非办公终端、TCS、GP安全、RDS、Windows、HR、Y项目 | `misc/` |
| 仓库、跨境电商 | `network/` |

### 6. 批处理并行策略

当子文档数量较多（>6），使用 `delegate_task` 并行处理：
- 每批建议 9-12 个文档（受 `delegation.max_concurrent_children` 限制，当前为 3）
- 分批建议：排障案例（【解决】类）优先处理，SOP/指南类后续
- 每个子代理独立读取和蒸馏
- 主代理等所有子代理完成后统一验证
- 权限不足的文档（code 3380004）直接跳过并记录，不影响批次整体进度

### 7. 验证

蒸馏完成后用 `read_file` 抽查几个文件，确保：
- YAML frontmatter 解析正确
- 各节标题格式正确
- 无残留的截图描述、XML 标签

## 常见陷阱

- **`--scope all` 不合法**：飞书 API 不识别 `all`，用 `full` 替代
- **图片/附件无法读取**：`docs +fetch` 只返回文本内容，图片作为 `<img>` 标签出现但 src 不可直接使用。不要尝试获取图片。
- **XML 中的转义** `&amp;`、`&lt;`、`&gt;` 等需要 Python `html.unescape()` 处理
- **用户身份缺失**：Bot 身份默认无文档读权限。需先用 `lark-cli auth login --domain docs` 获得用户授权
- **Auth QR 码只能在当前工作目录生成**：`lark-cli auth qrcode` 的 `--output` 必须是相对路径
- **文档权限失败**：如果遇到 code 3380004（No permission），说明当前身份无访问权限。**跳过该文档继续处理其余文档**，无需中断整个批次
- **`--format pretty` 优于 `--format json`**：直接返回文本 XML，无需解析 JSON 结构
- **非 `<cite>` 链接无法自动捕获**：主文档中纯 `<a>` 链接引用的子文档（如内嵌 URL）不会被 `<cite>` 正则捕获，需手动补充提取
