# Arista / Corporate Network DHCP DORA 抓包实录

## 环境

- macOS (en7), DHCP 上网
- DHCP 服务器: 10.91.0.39
- DHCP Relay/网关: 100.80.160.1
- VRRP MAC (网关): 00:00:5e:00:01:0c
- Client MAC: 10:98:19:57:34:fb

## 抓包命令

```bash
tcpdump -i en7 -n -e -v port 67 or port 68 -c 4
```

## 完整 DORA

### ① Discover（Client → Broadcast）

```
23:58:03.876148 10:98:19:57:34:fb > ff:ff:ff:ff:ff:ff
    0.0.0.0.68 > 255.255.255.255.67: BOOTP/DHCP, Request
    Client-Ethernet-Address 10:98:19:57:34:fb
    DHCP-Message: Discover
    Flags [none]            ← 广播位=0，允许服务器单播回复
    Hostname: "M7TJMC2RK0"
```

| 字段 | 值 |
|------|-----|
| SRC MAC | 10:98:19:57:34:fb |
| DST MAC | ff:ff:ff:ff:ff:ff |
| SRC IP | 0.0.0.0 |
| DST IP | 255.255.255.255 |
| UDP | 68 → 67 |

### ② Offer（Server → Client）★ 单播

```
23:58:03.938807 00:00:5e:00:01:0c > 10:98:19:57:34:fb
    10.91.0.39.67 > 100.80.171.148.68: BOOTP/DHCP, Reply
    Your-IP 100.80.171.148
    Gateway-IP 100.80.160.1
    Client-Ethernet-Address 10:98:19:57:34:fb
    DHCP-Message: Offer
    Server-ID: 10.91.0.39
    Lease-Time: 86378
    Subnet-Mask: 255.255.240.0
    Default-Gateway: 100.80.160.1
    Domain-Name-Server: 100.80.128.1
    Domain-Name: "bytedance.net"
```

| 字段 | 值 |
|------|-----|
| SRC MAC | 00:00:5e:00:01:0c (VRRP) |
| DST MAC | 10:98:19:57:34:fb ← **单播** |
| SRC IP | 10.91.0.39 (DHCP Server) |
| DST IP | 100.80.171.148 ← **单播** |
| UDP | 67 → 68 |

### ③ Request（Client → Broadcast）

```
23:58:04.943014 10:98:19:57:34:fb > ff:ff:ff:ff:ff:ff
    0.0.0.0.68 > 255.255.255.255.67: BOOTP/DHCP, Request
    Client-Ethernet-Address 10:98:19:57:34:fb
    DHCP-Message: Request
    Requested-IP: 100.80.171.148
    Server-ID: 10.91.0.39
```

| 字段 | 值 |
|------|-----|
| SRC MAC | 10:98:19:57:34:fb |
| DST MAC | ff:ff:ff:ff:ff:ff |
| SRC IP | 0.0.0.0 |
| DST IP | 255.255.255.255 |
| UDP | 68 → 67 |

### ④ ACK（Server → Client）★ 单播

```
23:58:05.009459 00:00:5e:00:01:0c > 10:98:19:57:34:fb
    10.91.0.39.67 > 100.80.171.148.68: BOOTP/DHCP, Reply
    Your-IP 100.80.171.148
    Gateway-IP 100.80.160.1
    Client-Ethernet-Address 10:98:19:57:34:fb
    DHCP-Message: ACK
    Server-ID: 10.91.0.39
    Lease-Time: 86377
```

| 字段 | 值 |
|------|-----|
| SRC MAC | 00:00:5e:00:01:0c (VRRP) |
| DST MAC | 10:98:19:57:34:fb ← **单播** |
| SRC IP | 10.91.0.39 |
| DST IP | 100.80.171.148 ← **单播** |
| UDP | 67 → 68 |

## 对 Address Locking 故障排查的意义

Offer 和 ACK 都是单播发送（DST MAC = 客户端 MAC）。如果 Address Locking 的 permit 表没有客户端的 IP 条目：

```
客户端的 ARP 请求  → 交换机丢弃
DHCP Offer(单播)   → 交换机丢弃   ← 客户端永远收不到
客户端 → xid 永远不匹配 → DHCP 超时 → 无 IP
```

这就是为什么认证成功但客户端没有 IP：**不是交换机 L2 不转发，是 Address Locking 的 L3 IP 过滤丢弃了回程单播包。**

## 参考

- Arista Address Locking 概念: `arista-dot1x-accounting.md` → "Address Locking 不是 STP — IP 白名单过滤"
- 抓包方法: `arista-debug-and-capture.md`
