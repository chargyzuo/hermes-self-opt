# Arista EOS — dot1x Host-Mode 详解

四种模式，由 `dot1x host-mode` 设定：

```
dot1x host-mode [single-host | multi-host | multi-host authenticated | multi-domain]
```

## 1. single-host（默认）

端口只允许**一个 MAC**。第一个设备认证后，其他 MAC 的 EAPOL 和数据流量均被丢弃。

```
+--------+         +----------+
| PC-1   |---------|  Switch  |  ← 仅一个 MAC
+--------+    Et1  +----------+
```

- 认证后第二个设备接入 → 流量被丢弃
- 适用：1 port = 1 device

## 2. multi-host

**认证一个，全员放行。** 第一个设备认证成功后，端口对所有后续 MAC 开放，无需再认证。

```
+--------+         +----------+
| PC-1   |----+----|  Switch  |  PC-1 认证 ✓ → 全员放行
+--------+    |    +----------+
+--------+    |
| PC-2   |----+    PC-2 无需认证
+--------+
```

- 安全上最宽松
- 已认证用户下线 → 端口重新锁定 → **所有人断开**
- 适用：会议室/共享区（不推荐生产环境）

## 3. multi-host authenticated（最安全的 multi-host）

**每个 MAC 独立认证。** 端口允许多个设备，但每个设备的 MAC 都要完成一次完整的 dot1x/MAB 认证。

```
+--------+         +----------+
| PC-1   |----+----|  Switch  |  PC-1 认证 ✓
+--------+    |    +----------+  PC-2 认证 ✓  ← 各自独立
+--------+    |
| PC-2   |----+
+--------+
```

- 认证互不影响 — A 掉线不影响 B
- 典型场景：多人共享端口、IP Phone + PC 菊花链
- 常配合 `dot1x mac based authentication` 使用：支持 802.1X 的设备走 EAPOL，不支持的发 MAB

## 4. multi-domain

端口分**两个域**——数据域和语音域。每域一个设备，各自独立 VLAN。

```
                   +----------+
IP Phone ----------|  Switch  |  语音域 → VLAN 100 (voice)
   |               +----------+  数据域 → VLAN 200 (data)
   |
PC -+
```

- 语音域通常走 MAB，数据域通常走 802.1X
- 域间隔离，互不影响
- 适用：经典 IP Phone + PC 菊花链

## 与 `dot1x mac based authentication` 的关系

`dot1x mac based authentication` 不是 host-mode，而是 MAB 开关：

- 设备不发 EAPOL → 交换机用 MAC 地址做 RADIUS 认证（MAB）
- 设备发 EAPOL → 正常 802.1X

**时序问题**：交换机发 EAPOL 后如果立即切 MAB，慢启动的 supplicant 会被跳过。
用 `dot1x mac based authentication delay <seconds>`（全局命令）给 supplicant 缓冲时间。

## 与 `dot1x timeout quiet-period` 的关系

`quiet-period` 控制认证失败后端口静默时间。静默期内交换机不发 EAPOL Request。
值越小，失败后重试越快。值 30（SGSIN07 当前）意味着失败后 30 秒重新尝试。

对比基线 CNDAT02 用 `quiet-period 65535`（约 18 小时）—— 失败后几乎不再重试。

## 典型配置对照

| 配置 | SGSIN07 (Et5/Et6) | 说明 |
|------|-------------------|------|
| `dot1x host-mode multi-host authenticated` | ✓ | 每 MAC 独立认证 |
| `dot1x mac based authentication` | ✓ | 支持 MAB 回退 |
| `dot1x timeout quiet-period 30` | ✓ | 失败后 30s 重试 |
| `dot1x authentication failure action traffic allow vlan 300` | ✓ | 失败 → VLAN 300 |
| `dot1x reauthentication` | ✓ | 每小时重认证 |
