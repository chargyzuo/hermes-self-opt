# Arista EOS — SUPPLICANT-TIMEOUT 诊断

## 症状

`show dot1x hosts mac <mac> detail` 显示：

```
Supplicant state: SUPPLICANT-TIMEOUT
Authentication method: EAPOL
AAA Server Returned:           ← 全部为空 / 0xFFFFFFFF
  Filter-Id: (空)
  Framed-IP-Address: 0.0.0.0
  Service-Type: Unknown (4294967295)
  Tunnel-Private-GroupId: (空)
  VLAN ID: (空)
```

## 根因

**客户端不响应 EAPOL Identity Request**。交换机发出 EAPOL 请求后未收到客户端响应，
EAPOL 握手在客户端侧中断，**RADIUS 从未被访问过**。

这不是 RADIUS 问题 — AAA Server Returned 全部为空是因为认证从未到达 RADIUS 阶段。

## 确认方法

### 1. 检查 MAC 所在 VLAN

```bash
show mac address-table address <xx:xx:xx:xx:xx:xx>
```

如果 MAC 在 **auth-failure VLAN**（以 `STATIC` 类型）：

```
Vlan 300    6c6e.0743.2f8c    STATIC      Et5
```

这是因为 `dot1x authentication failure action traffic allow vlan 300` 将认证失败用户放入失败 VLAN。
STATIC 类型表示该 MAC 是通过认证流程绑定的（而非动态学习）。

### 2. 对比正常 VLAN

```bash
show running-config interface ethernet <n> | include switchport|vlan|failure
```

正常 VLAN（`switchport access vlan 200`）vs 失败 VLAN（`dot1x authentication failure action traffic allow vlan 300`）。

### 3. 检查 EAPOL 计数器（可选）

```bash
show dot1x interface ethernet <n> detail
```

看 `EapolFramesTx`（发出）vs `EapolFramesRx`（收到）。Tx >> Rx 确认客户端不回包。

### 4. 确认 reauthentication 时间

```
Reauthentication interval: 3600 seconds
```

如果之前认证成功过、MAC 表有 STATIC 条目，但当前重认证超时，说明 supplicant 在重认证窗口未响应。

## 原因列表

| 原因 | 可能性 | 证据 |
|------|--------|------|
| 客户端无 802.1X supplicant | 高 | macOS 未配置 / Windows Wired AutoConfig 未启动 |
| Supplicant 配置错误 | 中 | EAP 方法、证书、凭据不匹配 |
| 客户端休眠/重启后 supplicant 未恢复 | 中 | 之前认证成功过（MAC 有 STATIC 条目），重认证失败 |
| 网卡驱动不处理 EAPOL | 低 | 特定网卡/驱动问题 |

## 排查建议

1. 客户端侧检查 802.1X 配置（macOS: 网络 → 以太网 → 802.1X；Windows: services.msc → Wired AutoConfig）
2. 客户端抓包：`tcpdump -i en0 ether proto 0x888e` — 看是否有 EAPOL Response
3. 如果同端口其他 MAC 认证正常（`multi-host authenticated` 模式下），问题 100% 在客户端
4. 如急需通网：临时关闭该端口的 dot1x 或配置 MAB 白名单
