# Arista Address Locking + DHCP Option 82 Leasequery 不匹配

## 问题场景

客户端 dot1x 认证成功、DORA 完整走通、MAC 表显示 VLAN 200 STATIC、STP forwarding，但**网关 SVI 学不到 ARP，用户无法通信**。

```
认证 SUCCESS → DORA 完成 → Address Locking Leasequery → DHCP服务器返回 UNKNOWN
                                                             ↓
                                                        permit表无条目
                                                             ↓
                                                        客户端ARP被丢弃
                                                             ↓
                                                        网关学不到ARP
```

## 关键证据

### Address Locking 计数器

```
show address locking counters

                  Lease Active  Lease Unknown
DHCP Server Query  Rcvd  Drop   Rcvd   Drop
10.72.207.8   693    31     0    659      3
10.64.109.8   693    31     0    662      0

 Interface    Query  Lease Active  Lease Unknown
----------   -----  ------------  -------------
 Ethernet5     792             0            791
 Ethernet6       6             6              0
```

Et5: 792 次查询，0 次 Active，791 次 Unknown。Et6: 6 次查询，全都 Active（有静态绑定）。

### DHCP 服务器日志

```
DHCPLEASEQUERY from 10.64.17.15 for e0:4e:7a:cf:29:18
DHCPLEASEUNKNOWN to 10.64.17.15 for e0:4e:7a:cf:29:18 (0 associated IPs)
```

即使 `DHCPLEASEACTIVE` 也带着 `(0 associated IPs)` — 服务器知道这个 MAC 但没有 IP 返回。

## 根因分析

### 拓扑

```
[Client] -- Et5 -- [ASW 10.64.17.15] -- Po1 -- [CSW 10.64.17.2] -- DHCP Server 10.64.109.8
```

### DHCP Relay（CSW）配置

```
interface Vlan200
   ip helper-address 10.64.109.8 vrf default source-interface Vlan30
   ip helper-address 10.72.207.8 vrf default source-interface Vlan30
   ip dhcp relay information option                  ← 关键行
```

`ip dhcp relay information option` 使 CSW 在转发 DHCP 时插入 **Option 82（Relay Agent Information）**。

### Address Locking（ASW）配置

```
address locking
   local-interface Vlan30
   dhcp server ipv4 10.64.109.8
   dhcp server ipv4 10.72.207.8
```

**与 DHCP relay 指向同一个服务器。** 但 ASW 发 Leasequery（RFC 4388）时只带 MAC 地址(chaddr)，不带 Option 82。

### 不匹配的路径

```
DORA路径（CSW转发）：
  Discover → CSW 添加 giaddr + Option 82 → DHCP Server
  → 服务器记录 lease: key = MAC + Option 82

Leasequery路径（ASW发送）：
  Leasequery → 只带 MAC (chaddr) → DHCP Server
  → 服务器查 lease: key = MAC 但不匹配 Option 82 部分
  → DHCPLEASEUNKNOWN
```

**根因：DHCP 服务器将 lease 存储在 MAC + relay 信息的组合 key 下。Leasequery 只带 MAC，匹配失败。**

### 为什么 Et6 正常？

Et6 的 Address Locking 配置了静态绑定，绕过 Leasequery：

```
lease 10.64.18.49 mac 00:e0:4c:77:da:9e
```

静态绑定直接装入硬件 permit 表，不依赖 Leasequery 结果。

## 解决方案

### 短期：ASW 静态绑定

```bash
configure
address locking
   lease <IP> mac <MAC>
```

添加后立即生效，不需要重启 DHCP 或重认证。

### 长期：DHCP 服务器侧排查

1. 确认 lease 记录是否包含 `option agent.circuit-id` / `option agent.remote-id`
2. 修改 DHCP 服务器配置，允许 Leasequery 仅通过 chaddr 匹配（忽略 Option 82 scope）

## Address Locking 行为速查

### 什么触发 Leasequery（Ariasta 文档）

1. 学到新 MAC → 立即发一批（1次 + 6次指数重试，最长80秒）
2. **未授权源 IP 的包到达时** → 触发新一轮（形成死循环）
3. 已授权流量每 50s 一次保活查询

**死循环原因：** 无 permit 条目 → 客户端 ARP 被丢弃 → 客户端再发 ARP → 触发新一轮 Leasequery → 还是 UNKNOWN → 无限循环。计数器上的 792 次就是这样产生的。

### Address Locking 不是 STP 阻塞

```
STP blocking:            L2，整个端口不转发
Address Locking deny:    L3，permit 表以外的源 IP 被丢弃
```

端口 authorized、STP forwarding、MAC 在 VLAN 200（STATIC）、认证 SUCCESS，但客户端仍然无法通信 — **这是最迷惑人的点。**
