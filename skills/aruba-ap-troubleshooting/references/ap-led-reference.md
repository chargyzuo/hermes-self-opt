# Aruba AP LED 指示灯完整对照表

整理自飞书 `Aruba无线运维宝典` 和 `无线AP指示灯状态含义` Wiki。

## LED 物理布局（看丝印标签）

### AP-555 / AP-535（5xx 系列）

```
┌─────────────────────────┐
│          Aruba           │
│                          │
│    ● PWR       ● WiFi    │
│     ↑            ↑       │
│  System LED   Radio LED  │
└─────────────────────────┘
```

正常状态：**两颗都绿色常亮**。LED 状态表覆盖 AP-555 + AP-535（同系列共用）。

### AP-655 / AP-635（6xx 系列）

```
   ●         ●         ●         ●         ●
  SYSTEM   5GHz     2.4GHz     5GHz      6GHz
    ↑        ↑         ↑         ↑         ↑
  系统灯   Radio0    Radio1    Radio2     6E
```

面板上印了频段标签，每频段一颗灯 + 独立 System Status LED。正常：System 绿灯 + 各频段绿灯。

### AP-325

两颗灯，正常两个都绿色常亮。

### AP-225（老型号）

五颗灯，从左到右：`PWR` `ENET0` `ENET1` `5GHz` `2.4GHz`，正常四颗绿灯常亮。

---

## System Status LED（系统状态灯，标签 PWR）

适用 AP-555 / AP-535（5xx 系），AP-655/635 类似。

| 状态 | 含义 | 严重程度 |
|------|------|:---:|
| 灭 (Off) | 设备关机 / 无供电 | ❌ |
| 绿灯闪烁 (blinking) | 设备启动中，未就绪 | ⏳ |
| 绿灯常亮 (solid) | ✅ 设备就绪，正常，无网络限制 | ✅ |
| 绿灯闪 pattern 1 | 就绪，但上行协商 < 1Gbps | ⚠️ |
| 绿灯闪 pattern 2 | 深睡眠模式 (Deep Sleep) | ⚠️ |
| 黄灯常亮 (amber solid) | 受限电源模式（PoE 不足 / IPM），无网络限制 | ⚠️ |
| 黄灯闪 pattern 1 | 受限电源 + 上行次优速率 | ❌ |
| 红灯 (red) | 系统错误，需立即关注 | ❌ |

---

## Radio Status LED（射频状态灯，标签 WiFi）

适用 AP-555 / AP-535，AP-655/635 每频段灯同理。

| 状态 | 含义 | 严重程度 |
|------|------|:---:|
| 灭 (Off) | AP 电源关闭或两射频均禁用 | ❌ |
| 绿灯常亮 (solid) | ✅ 两个射频均在接入模式 (Access) | ✅ |
| 绿灯闪烁 (blinking) | 一个接入模式，另一个禁用 | ⚠️ |
| 黄灯常亮 (amber solid) | 两个均在监控模式 (Monitor) | ⚠️ |
| 黄灯闪烁 (amber blinking) | 一个监控模式，另一个禁用 | ⚠️ |
| 绿黄交替 (alternating) | 一个接入 + 一个监控，各 1s，2s 周期 | ⚠️ |

---

## 常见故障场景速查

| 现象 | 最可能原因 | 排查命令 |
|------|-----------|---------|
| System 黄灯常亮 | PoE 供电不足 | `show ap debug power-info` |
| System 黄灯闪烁 | PoE 不足 + 上行 < 1Gbps | `show ap debug system-status \| in POE` |
| Radio 黄灯闪烁 | DFS 雷达击中 / AM 角色 | `show ap debug radio-info radio 0` |
| Radio 黄灯常亮 | 双射频均被配为 Monitor | `show ap arm state` |
| System 红灯 | 系统 Crash / 硬件故障 | `show ap debug crash-info` |

---

## HPE 官方 LED 手册

- AP-655: https://www.hpe.com/psnow/doc/a00119145chp.pdf
- AP-635: https://www.hpe.com/psnow/doc/a00114648enw
