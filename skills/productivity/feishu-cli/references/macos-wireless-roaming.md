# macOS Wireless Client Excessive Roaming — Troubleshooting

When a macOS wireless client shows SNR ≤ 25, RSSI ≤ -70 dBm, and 50+
roams in a few hours, follow this pipeline. The most common root cause on
macOS is AWDL (Apple Wireless Direct Link) interference.

## Internal Document References

- 在 macOS 上永久关闭 AWDL（戴勉）: https://bytedance.larkoffice.com/docx/F3gpd0P0Bo9DdjxEl7acYan1nrh
- Mac WiFi 间歇性断流断网问题解决-最佳实践（孙纬南）: https://bytedance.larkoffice.com/docx/doxcnaPLlPeTvCpAIXL4Hewc1be
- 无线网络相关问题故障排查手册（李志康）: https://bytedance.larkoffice.com/docx/PNGGdJ90hoAJ3YxcIEWchN5knpc
- IT Oncall诊断库使用SOP-无线网络（李喆）: https://bytedance.larkoffice.com/docx/Omixd2Zafo9Sv4x1OLrcMdiQnrh

## Glata Copilot Anomaly Thresholds (from 诊断库SOP)

| Metric | Abnormal Condition |
|--------|-------------------|
| Client SNR | ≤ 25 |
| Noise Floor | ≥ -85 dBm |
| Client Tx/Rx Rate | ≤ 144 Mbps |
| Utilization | ≥ 65% |
| Interference | ≥ 15% |
| Client_health | < 40 |

## Phase 1: Gather Evidence (on WAC)

```bash
# Pull roaming history — focus on Deauth Reason column
show ap client trail-info <MAC>
```

### Deauth Reason Decoder

| Deauth Reason | Meaning | Action |
|--------------|---------|--------|
| `Dormant STA Del` | Client left on its own, AP cleaning up stale entry | **Client-side problem** — proceed to Phase 2 |
| `Client Match` | Infrastructure forced roam (802.11v/k) | ClientMatch incompatibility scenario |
| `wlan driver wireless client out of range` | macOS dropped off AP's radio | AWDL or macOS version bug |
| `STA has left and is disassociated` | Normal client-initiated disassociation | Edge-case ping-pong if frequent |

macOS ClientMatch is globally disabled per 运维宝典 (沈岳, 2026-02-13):
> "目前已经通过 api 全局禁用了 MACOS 的 client-match"

If still seeing ClientMatch deauths in your region, manually add:
```bash
add ap arm client-match unsupported <MAC>
```

## Phase 2: Identify Root Cause

### Pattern A: Only `Dormant STA Del`, frequent roaming across floors

**Symptom**: All deauth reasons are `Dormant STA Del`, client jumps across
multiple APs on different floors in minutes.

**Root cause**: Client-side roaming decision — not infrastructure.
On macOS, this is almost always AWDL.

**Verify**: On user's Mac, check:
```bash
ifconfig awdl0
# If interface exists and shows UP/active → AWDL is the cause
```

Or use Glata Copilot diagnostic card — it detects AWDL status automatically.

### Pattern B: `Client Match` in deauth reasons

Follow 故障排查手册 场景三: add MAC to ClientMatch unsupported list
permanently.

### Pattern C: `wlan driver wireless client out of range`

Follow 故障排查手册 场景七: disable AWDL, or upgrade macOS version if old.

## Phase 3: Fix — Disable AWDL

### Internal recommended method (one command, permanent)

ByteDance internal optimized script (戴勉, hosted on mdmlab — no VPN needed):

```bash
# Disable AWDL permanently (survives reboot/wake)
sudo curl -sL https://mdmlab.bytedance.com/awdl-daemon.sh | bash
```

What it does:
1. `ifconfig awdl0 down` — immediate disable
2. Installs LaunchDaemon that polls every 1s, downs awdl0 if system re-enables it
3. Auto-runs on boot, wake, and network changes

Verify:
```bash
ifconfig awdl0 | grep status
# Expected: status: inactive
```

### Restore AWDL (if needed)

```bash
sudo curl -sL https://mdmlab.bytedance.com/cleanup-and-reenable-awdl.sh | bash
```

### Temporary test (verify AWDL is the cause before permanent disable)

```bash
sudo ifconfig awdl0 down
# Test for 30 min, then:
sudo ifconfig awdl0 up   # restore
```

## Phase 4: Companion Settings (from 最佳实践 doc)

| Setting | Path | Reason |
|---------|------|--------|
| AirPlay Receiver OFF | System Settings → Sharing → uncheck AirPlay Receiver | Primary AWDL trigger |
| Wi-Fi Location OFF | Privacy → Location Services → System Services → uncheck "Networking & Wireless" | Prevents Wi-Fi scanning interference |
| Low Power Mode OFF | Battery → disable Low Power Mode | Prevents aggressive power-saving that drops Wi-Fi |
| Prevent sleep on AC | Adapter → check "Prevent automatic sleeping" | Stability during long sessions |

### M-chip Mac specific

Apple has acknowledged M1/M2 Macs have Wi-Fi disconnection issues with
Aruba APs. Internal best practice:
- Upgrade to latest macOS
- **Still disable AWDL** even on latest macOS

## Impact of Disabling AWDL

These Apple ecosystem features will stop working:
- AirDrop
- AirPlay / screen mirroring
- Sidecar (iPad as second display)
- Apple Watch auto-unlock
- Shared Wi-Fi password

## Verification After Fix

1. Wait 30 minutes
2. Re-run `show ap client trail-info <MAC>` — roaming frequency should drop
   dramatically
3. Check Glata Copilot / Grafana SNR/RSSI trend — should stabilize

## Standard Customer-Facing Script (from 诊断库 SOP)

> 同学，你好，我们检测到你设备的 AWDL 功能处于开启状态，该功能可能会对
> Wi-Fi 网络造成干扰，导致 WIFI 断流卡顿，影响你的网络使用体验。
>
> 请执行以下命令关闭 AWDL：
> `sudo curl -sL https://mdmlab.bytedance.com/awdl-daemon.sh | bash`
>
> 关闭后 AirDrop 等功能会暂时不可用，如需恢复可随时联系。
