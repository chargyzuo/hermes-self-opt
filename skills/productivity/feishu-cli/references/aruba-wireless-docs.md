# Aruba Wireless Operations — Key Internal Documents

Discovered via Feishu doc search (2026-06-25). These are the authoritative
internal references for Aruba wireless troubleshooting at ByteDance.

## Core Documents

### 1. Aruba无线运维宝典 (Master Index)
- URL: https://bytedance.larkoffice.com/docx/SGGhdTOeco3yBCxO2rDchU0jnkg
- Owner: 沈岳 | Updated: 2026-02-13
- Token: SGGhdTOeco3yBCxO2rDchU0jnkg
- Content: Master index of ALL Aruba wireless ops knowledge. Links to sub-docs
  for hardware standards, best practices, RAC/RAP, wireless TS, RMA, captive
  portal, air groups, AP going down, packet capture, deauth reasons, etc.
- Key sub-documents linked from here:
  - Central AP下线 SOP (⚠️ permission-restricted)
  - AP Going Down Troubleshooting SOP
  - Aruba Captive Portal 工作机制及相关
  - 无线troubleshooting流程及分析
  - 空口抓包及控制器抓包
- High-frequency TS commands included inline (show ap association, show ap
  client trail-info, show ap debug radio-info, etc.)

### 2. 无线网络相关问题故障排查手册 (13 Scenarios)
- URL: https://bytedance.larkoffice.com/docx/PNGGdJ90hoAJ3YxcIEWchN5knpc
- Author: 李志康 | Reviewer: 刘粤华 | v1.0.0 (2026-05-29)
- Token: PNGGdJ90hoAJ3YxcIEWchN5knpc
- Content: 13 documented wireless fault scenarios with step-by-step resolution.
  Covers channel interference, high utilization, ClientMatch incompatibility,
  AWDL issues, AP bugs (ANI disabled on 8.10.0.7 + AP 5xx), AP555 dual-5G,
  AC bug batch reboot, warm reset RMA, etc.
- Key diagnostic commands for ANI bug detection:
  - `show ap debug radio-info ap-name xxxxx radio 0 | in ANI`
  - `show ap debug radio-info ap-name xxxxx radio 0 | in Int`
- Tools referenced: Netcare, Grafana, MM, OPS

### 3. IT Oncall诊断库使用SOP-无线网络 (Glata Copilot)
- URL: https://bytedance.larkoffice.com/docx/Omixd2Zafo9Sv4x1OLrcMdiQnrh
- Owner: 李喆 | v1.4 (2026-04-28)
- Token: Omixd2Zafo9Sv4x1OLrcMdiQnrh
- Content: Glata Copilot wireless diagnostic workflow. Diagnostic cards with
  auto-highlighted anomaly thresholds. SOP guided operations for T1/T2
  engineers. Covers: auto-repair AP, channel adjustment, network dial test,
  kick user reconnect, AWDL disable, AP/terminal panel (Grafana).
- Key anomaly thresholds:
  - Utilization ≥ 65%, Interference ≥ 15%, Noise Floor ≥ -85 dBm
  - Clients ≥ 40, Client Tx/Rx Rate ≤ 144 Mbps, SNR ≤ 25, Health < 40

### 4. Aruba Captive Portal 工作机制及相关
- URL: https://bytedance.larkoffice.com/docx/DUKvdpgbtoJfLfxiGhucYc6fnzc
- Owner: 孙纬南 | Updated: 2025-03-20
- Token: DUKvdpgbtoJfLfxiGhucYc6fnzc
- Content: Complete Captive Portal mechanism — call flow, portal modes
  (built-in vs external), redirect trigger process, http/https modes,
  HSTS implications, tri-session issues, DNS hijacking via
  captiveportal-login.wifi.bytedance.net. Portal redirect URL carries MAC
  as query parameter: `?cmd=login&mac=<mac>&ip=<ip>&essid=...`

### 5. Aruba captive-portal workflow in-depth analysis
- URL: https://bytedance.larkoffice.com/docx/NVVadFdygob8pqxwZWtcm6hfnLb
- Owner: 孙纬南 | Updated: 2024-10-10
- Token: NVVadFdygob8pqxwZWtcm6hfnLb
- Content: Deep-dive on the portal workflow before browser pop-up. Covers SYN
  interception, dst-nat to WAC:8080, SNAT reply forgery, SVI presence impact
  on portal delivery, firewall stateful filtering pitfalls.

## Supporting Documents

### 6. 无线AP指示灯状态含义 (Wiki)
- URL: https://bytedance.larkoffice.com/wiki/wikcnUBOTnI37M2VBcnqHqm1uh1
- Token: wikcnUBOTnI37M2VBcnqHqm1uh1
- Content: Per-model LED layout photos and status tables for AP-655, AP-635,
  AP-535, AP-325, and AP-225. Shows physical LED positions (PWR/WiFi labels
  on AP chassis) and full System/Radio Status LED meaning tables.
- Load `skill_view(name=\"aruba-ap-troubleshooting\", file_path=\"references/ap-led-reference.md\")`
  for the consolidated LED reference derived from this wiki + the main doc.

### OSC-Tier2-Tech-Aruba 常用命令
- URL: https://bytedance.larkoffice.com/docx/PLMpdxvvXoZHByxdPn6cOSycnKd
- Owner: 李志康 | Token: PLMpdxvvXoZHByxdPn6cOSycnKd

### Online Service Center-Tier2 网络文档目录 (Wiki)
- URL: https://bytedance.larkoffice.com/wiki/VIONwrQeBiRz9okjJPfcVkCdnje
- Token: VIONwrQeBiRz9okjJPfcVkCdnje
- Structure: 日常运维SOP → 问题/故障排查类 → 基础类 → Aruba Central-SBO

### 网络工单学习 (左佳杰)
- URL: https://bytedance.larkoffice.com/docx/SQ26dSHKJonmP9xRCqrcjVgVnCg
- Token: SQ26dSHKJonmP9xRCqrcjVgVnCg
- Contains: aruba portal 认证排错流程图

## macOS-Specific Troubleshooting

- See [`references/macos-wireless-roaming.md`](macos-wireless-roaming.md) for
  the full macOS wireless client excessive roaming / AWDL investigation
  pipeline. Covers: SNR/RSSI thresholds, `show ap client trail-info` deauth
  reason decoding, AWDL detection, internal one-command AWDL disable script
  (`mdmlab.bytedance.com`), and companion macOS settings.

## AP LED Status Reference

Extracted from 运维宝典 → 无线TS → System/Radio Status LEDS (2026-06-26).

### System Status LED (AP535)

| LED State | Meaning |
|-----------|---------|
| Off | Device powered off |
| Green - blinking | Booting, not ready |
| Green - solid | ✅ Ready, functional, no network restrictions |
| Green - flash pattern 1 | Ready, but uplink <1Gbps (suboptimal) |
| Green - flash pattern 2 | Deep sleep mode |
| Amber - solid | ⚠️ Limited power (PoE/IPM restriction), network OK |
| Red | ❌ System error — immediate attention needed |

### Radio Status LED (all models)

| LED State | Meaning |
|-----------|---------|
| Off | AP power off or both radios disabled |
| Green - solid | ✅ Both radios in Access Mode |
| Green - blinking | One radio Access Mode, other disabled |
| Amber - solid | ⚠️ Both radios in Monitor Mode |
| Amber - blinking | One radio Monitor Mode, other disabled |
| Green/Amber alternating | Alternating 1s each, 2s cycle |

### Quick Triage by LED

- **Red system LED** → `show ap debug system-status ap-name <name>`
- **Amber system LED solid** → PoE insufficient (AP in IPM), check PSE budget/cable/LLDP
- **Amber system LED flashing** → Most likely physical cable fault: PoE OK but no Ethernet link.
  Do NOT assume PoE failure — check `display poe power` on the switch port first.
  If PD power > 0W but port is DOWN → data pairs broken, replace cable.
- **Green blinking system LED (persistent)** → AP can't register to controller
- **Radio LED unexpected** → `show ap debug radio-status ap-name <name>`

📝 Full AP LED troubleshooting guide saved to Obsidian:
  `Obsidian Vault/Aruba AP 指示灯状态与故障排查.md`

### 6. 无线AP指示灯状态含义 Wiki
- URL: https://bytedance.larkoffice.com/wiki/wikcnUBOTnI37M2VBcnqHqm1uh1
- Token: wikcnUBOTnI37M2VBcnqHqm1uh1
- Content: Per-model LED layout photos + system/radio status tables for
  AP-655, AP-635, AP-535, AP-325, AP-225. Includes HPE official PDF links.
  Physical LED labels: **PWR** = System Status LED, **WiFi** = Radio Status LED.
- For AP-555/535: 2 LEDs, silk-screened PWR (system) + WiFi (radio). Both green = normal.
- For AP-655/635: 5 LEDs, silk-screened SYSTEM + 5GHz + 2.4GHz + 5GHz + 6GHz.

## End-to-End AP-Down Troubleshooting Workflow

When an AP shows amber/flashing LED or is Down on WAC, follow this chain:

### Phase 1: WAC Triage

```
show ap database long | include <ap-name>     # Status, uptime, flags, standby
show ap lldp neighbors ap-name <ap-name>      # Which switch + port?
```

Key flags to watch: T=ThermalShutdown, r=PowerRestricted, p=DeepSleep, S=Standby

### Phase 2: Trace to Switch Port

Use LLDP neighbors from WAC, or if AP is down, check adjacent APs' LLDP
to infer the switch, then search by MAC on candidate switches.

```
display mac-address <mac-huawei-format>        # Huawei: HHHH-HHHH-HHHH
```

### Phase 3: Port + PoE Diagnosis

```
display interface <port>                        # UP/DOWN? Speed? Last up/down time?
display poe power interface <port>              # PD power (mW), class, reference
```

**Critical diagnostic**: Port DOWN but PoE delivering power → physical cable fault (data pairs broken while power pairs intact). This causes AP amber flashing LED: AP boots on PoE but can't establish Ethernet link to controller.

### Phase 4: Physical

- Re-seat cable at AP and patch panel
- Replace patch cable if port still DOWN
- If PoE gone too → switch port/PSE issue
- If PoE present, link still DOWN → AP Ethernet port hardware fault → RMA

## Search Strategy

When asked about Aruba wireless/Central/Portal topics, search Feishu with:
- `lark-cli docs +search --query "Aruba <topic>" --page-size 10`
- Key owners to watch: 孙纬南 (portal/RAP), 李志康 (troubleshooting manuals),
  沈岳 (运维宝典), 李喆 (diagnostic SOP)
- The wiki directory (VIONwrQeBiRz9okjJPfcVkCdnje) is the master index of all
  Tier2 network docs — start there for broad navigation.
