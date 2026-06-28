---
name: aruba-ap-troubleshooting
description: "End-to-end Aruba wireless AP fault diagnosis: LED interpretation → WAC check → switch-side verification → Kibana log analysis. Covers AP-5xx/6xx models, internal ByteDance doc references, and proven troubleshooting workflows."
version: 1.0.0
author: Hermes Agent
platforms: [macos]
metadata:
  hermes:
    tags: [aruba, wireless, ap, led, troubleshooting, wac, kibana, networking]
---

# Aruba AP Troubleshooting

End-to-end Aruba wireless AP fault diagnosis: LED interpretation → WAC check →
switch-side verification → Kibana log analysis. Built from internal ByteDance
docs and real troubleshooting sessions.

## Triggers

- Aruba AP 故障 / LED 异常 / 掉线 / 离线
- AP 闪灯 (amber/green/red blinking)
- "AP down" / "AP not found on controller"
- WAC show ap database 显示 Down
- AP 无法注册 / 反复重启

## Step 1: LED 解读 — 判断故障方向

**先看 AP 机身上灯孔旁边的丝印标签**：
- **PWR** → System Status LED（系统状态灯）
- **WiFi** / 频段标签（5GHz, 2.4GHz, 6GHz）→ Radio Status LED（射频状态灯）

详细 LED 对照表：`skill_view(name="aruba-ap-troubleshooting", file_path="references/ap-led-reference.md")`

### System LED 速查

| 状态 | 根因 |
|------|------|
| 黄灯常亮 | PoE 供电不足（AP-555 需 802.3bt / 60W） |
| 黄灯闪烁 | PoE 不足 + 上行速率不达标 |
| 红灯 | 系统错误 / Crash / 硬件故障 |

### Radio LED 速查

| 状态 | 根因 |
|------|------|
| 黄灯常亮 | 双射频均在 Monitor Mode（AM 配置或 DFS 击中） |
| 黄灯闪烁 | 单射频 Monitor Mode + 另一个禁用 |

正常状态：**两颗灯都绿色常亮**。

## Step 2: WAC 侧确认

```bash
show ap database | include <AP名>
show ap database long | begin <AP名>
```

关键字段：`Status`（Down/Up）, `Flags`（S/T/p/r 等）, `Switch IP`

- Up → `show ap debug system-status ap-name <AP名>` 查详情
- Down → 进入 Step 3

## Step 3: Kibana 日志回溯

完整语法参考：`skill_view(name="aruba-ap-troubleshooting", file_path="references/kibana-filter-reference.md")`

```kibana
"<AP名>" AND ("down" OR "reboot" OR "heartbeat" OR "lost" OR "crash")
```

关键进程：`stm`（Station Management）, `sapd`（AP Daemon）。时间范围拉到掉线前后 1 小时。

## Step 4: 交换机侧确认

1. 从相邻 AP 的 `show ap lldp neighbors ap-name <AP名>` 确定交换机和端口规律
2. 按编号规律推断故障 AP 的交换机端口
3. 登录交换机检查：

```bash
# 华为交换机
display interface MultiGE0/0/<port>
display poe power interface MultiGE0/0/<port>
display mac-address <MAC格式: xxxx-xxxx-xxxx>
```

**`display poe power interface` 输出解读**：详见 `references/huawei-poe-interpretation.md`
— PD Class → 供电标准（Class 5 = 802.3bt 60W），功耗曲线可判断 AP 启动阶段 vs 异常状态。

4. 判断：

| 现象 | 根因 |
|------|------|
| Port DOWN + PoE 有供电 | **物理链路**：网线数据对断 / AP 以太网口故障 |
| Port DOWN + PoE 无供电 | 交换机 PoE 故障 / 供电耗尽 |
| Port UP + 无 MAC | VLAN 配置错误 / AP 获取不到 IP |

## Step 5: 物理层确认

- AP 端：重新插拔网线，换线测试
- 配线架端：检查跳线
- 测线仪验证全部 4 对线

## Step 6: Bug/RMA

- 收集：`show ap debug crash-info` + `show ap debug counters ap-name <AP名>`
- 查 `无线网络相关问题故障排查手册`（13 场景）中已知 Bug（如 8.10.0.7 AP 5xx ANI 禁用）

## 内部文档索引

| 文档 | Token | 用途 |
|------|-------|------|
| Aruba无线运维宝典 | `SGGhdTOeco3yBCxO2rDchU0jnkg` | 主入口，System/Radio Status LEDS |
| 无线AP指示灯状态含义 Wiki | `wikcnUBOTnI37M2VBcnqHqm1uh1` | 各型号 LED 布局实物照片 |
| 无线网络相关问题故障排查手册 | `PNGGdJ90hoAJ3YxcIEWchN5knpc` | 13 种标准故障场景 |
| OSC-Tier2-Tech-Aruba 常用命令 | `PLMpdxvvXoZHByxdPn6cOSycnKd` | 高频 TS 命令 |
| AP Going Down SOP | 运维宝典内链 | AP 下线排查 SOP |

搜索飞书新文档：
```bash
lark-cli docs +search --query "Aruba <关键词>" --page-size 10
```

## Pitfalls

- **NetBox "Planned" 状态不可信**：交换机可能已在线但 NetBox 未更新，以实际 SSH 可达为准
- **AP database 中 Port=N/A**：AP 未上线时 WAC 无法获取 LLDP，靠编号规律推断
- **PoE 有电 ≠ 链路 OK**：PoE 和 data link 独立协商，可能供电正常但端口 DOWN
- **MAC 格式差异**：WAC `xx:xx:xx:xx:xx:xx` → 华为 `xxxx-xxxx-xxxx`
- **默认只读**：所有操作默认只读（GET/查询/查看），禁止写入/修改/配置
