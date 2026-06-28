# Arista EOS dot1x Accounting & IP Locking

## 概述

Arista 交换机的 dot1x accounting 行为与华为/思科有本质差异。本文档基于 SGSIN07 (10.64.17.15) 和 CNDAT02 (100.92.98.52) 两台 Arista CCS-720XP-48Y6-F (EOS 4.31.1F) 的对比排查。

## Arista dot1x 认证流程（两步式）

内部文档 "有线 dot1x 认证流程详解" 明确记录：

- **Step 1-4**: 标准 EAPOL → ISE → FreeRadius 认证
- **Step 5 (Arista only)**: ASW 携带 Filter-Id 再次发起 Radius-Request 请求授权
- **Step 6 (Arista only)**: ISE 根据 Filter-Id 下发 dVLAN/dACL

> "第5、6步为可选步骤，目前仅在 arista 交换机场景下会触发这两步"

## Accounting 触发条件

内部文档 "有线 dot1x 认证流程详解 - 补充四：审计流程"：

> "在 FreeRadius 完成认证且经由 ISE 授权之后，如果 ASW 配置了 accounting，则 ASW 会发起 Accounting-request"
> "第一个 Accounting-request 报文中不会携带客户端的 IP 地址"
> "在后续的 interim-update accounting-request 中会携带客户端 IP 地址"

关键：认证 AND 授权两步都完成，accounting 才触发。

## Accounting 命令

```
aaa accounting dot1x default start-stop group <group>
```

`start-stop` 在 Arista EOS 上只发 Acct-Start（会话建立）和 Acct-Stop（会话结束），**不发周期性 Interim-Update**。

要发周期 Interim-Update，需额外配置：
```
aaa accounting update periodic 3    # 每3分钟
```

或者 FreeRadius 在 Access-Accept 中返回 `Acct-Interim-Interval`。

## IP Locking（Address Locking）

### 问题

内部文档 "Arista交换机配置说明-用户终端802.1x认证字段"：

> "由于交换机实现不同，Arista交换机无法直接获取到用户的IP地址信息。在802.1x认证及后续AAA交互过程中，也无法向radius服务器提供这些信息（Framed-IP-Address, Service-Type）。"

### 机制

Arista 通过 IP Locking 向 DHCP 服务器发 Leasequery（RFC 4388）获取客户端 IP。是安全功能，但被用来填补 accounting 的 IP 缺口。

### Address Locking 不是 STP — IP 白名单过滤

**Address Locking 不是像 STP 一样 block 端口。** 两者本质完全不同：

```
STP blocking:           L2 层面，整个端口不转发任何流量
Address Locking deny:   L3 层面，只放行有 IP 条目的流量，其他 IP 被丢弃
```

Address Locking 维护一个 **IP 白名单 (permit list)**：

```
   IP Address      Action
------------------ ------
   10.64.18.49     permit     ← 有 DHCP lease/静态绑定的 IP
```

- 有条目 → 该 IP 的流量 `permit`，正常转发到网关 SVI
- 无条目 → **不是阻止端口（端口 authorized、STP forwarding、MAC 在 VLAN 正常）**，而是**阻止没有 IP 的流量到达网关 SVI (L3 过滤)**

**实践影响：** 客户端认证成功后，即使端口 authorized、MAC 表显示 `VLAN 200 STATIC`、STP forwarding，如果 Address Locking 没有该客户端的 IP 条目，交换机会丢弃客户端的 ARP 请求/响应，网关 SVI 学不到 ARP，用户永远无法通信。

**验证方法：**

```bash
# Address Locking 无条目 → 流量被挡
show address locking table ipv4 | include <mac>  # 无结果
show ip arp mac-address <mac>                    # 无结果

# L2 层面一切正常（误导性强）
show mac address-table address <mac>             # VLAN 200, STATIC
show spanning-tree vlan 200                      # forwarding
show dot1x hosts mac <mac> detail                # SUCCESS
```

### 常见问题场景：认证成功但无网络 / 无 accounting

```
认证成功 (SUCCESS)
  → MAC 在 VLAN 200 (STATIC)
  → 但客户端没有 DHCP (不自动续约/supplicant 不触发)
  → Address Locking Leasequery 空返回
  → permit 表无条目
  → 客户端的免费 ARP 被丢弃
  → 网关 SVI 学不到 ARP
  → 用户出不了门 && 没有 accounting
```

**解决方案：**

**短期（静态绑定）：** 在 ASW 上手动添加一条 `lease`，绕过 DHCP 依赖：

```bash
configure
address locking
   lease 10.64.19.X mac e0:4e:7a:cf:29:18
```

一旦添加，permit 表立即生效 → 客户端 ARP 通过 → 网关学到 ARP → accounting Interim-Update 携带 IP。

**长期（客户端侧）：** 修复 dot1x 认证后 DHCP 不自动重试的问题（操作系统/supplicant 配置）。

### 配置（DHCP Leasequery 模式）

```
address locking
   local-interface Vlan30              # 管理接口
   dhcp server ipv4 <bluecat-ip>       # DHCP 服务器地址

vlan 200
   address locking
      address-family ipv4

interface Ethernet53                   # 上联口关闭
   address locking
      address-family ipv4 disabled
      address-family ipv6 disabled
```

需要 Bluecat DHCP 服务器开启 leasequery 功能。

### 配置（静态绑定模式）

```
address locking
   local-interface Vlan30
   dhcp server ipv4 <dummy-ip>         # 即使静态也要有一个
   lease 10.64.18.49 mac 00:e0:4c:77:da:9e

vlan 200
   address locking
      address-family ipv4
```

静态 lease 不需要 DHCP 服务器查询，但 VLAN 激活仍需至少一个 `dhcp server` 声明。

### 验证

```
show address locking                  # VLAN 状态应为 yes
show address locking table ipv4       # lease 应为 installed
show dot1x hosts mac <mac> detail     # Framed-IP-Address 应有 sourceIpLocking
```

## AAA Server Returned 属性诊断

`show dot1x hosts mac <mac> detail` 显示 FreeRadius/ISE 返回的属性：

| 属性 | 正常值 | 异常值 |
|------|--------|--------|
| Service-Type | Framed-User (2) | Unknown (0xFFFFFFFF) — FreeRadius 未设置或 ISE 损坏 |
| Tunnel-Private-GroupId | 1010 | (空) — 未下发动态 VLAN |
| Filter-Id | dev/PDI | (空) |
| Framed-IP-Address | 0.0.0.0 (初始) → IP (IP Locking 后) | — |
| VLAN ID | 1010 | (空) — 回退到端口 access VLAN |

## 分页问题

Arista EOS 使用 `terminal length 0` 禁用分页（**不是** 华为的 `screen-length 0 temporary`，也不是 Cisco 的 `terminal length 0`）。不设置会导致输出被 `--More--` 截断。

```
terminal length 0
```

**建议在所有诊断命令前先执行此命令。**

## 交换机命令参考

```
terminal length 0                     # 必须先禁用分页
show dot1x hosts                       # 所有认证终端
show dot1x hosts mac <mac> detail      # AAA返回属性+会话详情
show dot1x interface ethernet <n> detail
show dot1x all
show dot1x hosts blocked               # 被拉黑的终端
show radius                            # RADIUS统计 (Start/Interim/Stop计数器)
show address locking
show address locking table ipv4
show mac address-table address <mac>   # MAC所属VLAN
show ip arp mac-address <mac>          # ARP表
show running-config interface ethernet <n>
show running-config | include aaa      # AAA配置
show ip access-list                    # 本地ACL (需与Filter-Id匹配)
clear dot1x host mac <mac>             # 踢用户下线
```

## Address Locking 排查 — Leasequery 回复分析

当用户认证成功、DORA 完成、MAC 在 VLAN 正常、STP forwarding，但网关 SVI 学不到 ARP 时，Address Locking 丢弃了客户端的 ARP。**核心排查工具是 `show address locking counters`。**

### 诊断流程

#### 1. 检查泄漏查询成功率

```bash
show address locking counters
```

看 **DHCP Server** 部分的统计：

```
DHCP Server Query  Rcvd   Drop   Rcvd   Drop    Rcvd     Drop Unknown
10.72.207.8   696    34      0    659      3       0        0       0
10.64.109.8   696    34      0    662      0       0        0       0
```

- **LeaseActive Rcvd**: DHCP 服务器回复了带 IP 的激活响应 — 这才是成功
- **LeaseUnknown Rcvd**: 服务器不认识这个 MAC（或认出但没带 IP）

看 **Interface** 部分的统计：

```
 Interface Query Lease Active Lease Unknown Lease Unassigned
Ethernet5   792            0           791                0
Ethernet6     6            6             0                0
```

- **Query**: 该接口发出的总查询次数
- **Lease Active**: 成功的次数（带 IP）
- **Lease Unknown**: 失败的次数（无 IP）

#### 2. 对比基线交换机

正常工作的交换机 Lease Active 命中率应在 **50% 以上**：

```
基线 (正常):   Query=63526, LeaseActive=34907   ← 55% 命中
问题交换机:    Query=696,   LeaseActive=31      ← 4.5% 命中 → 几乎都失败
```

**对比方法：** 找同一区域、同一 DHCP 服务器、拓扑相似的另一台 Arista ASW，比对 `show address locking counters` 的占比。

#### 3. 判断标准

| LeaseActive 占比 | 结论 |
|---|---|
| > 50% | DHCP 服务器正常返回 IP |
| 10-50% | 部分失败，需排查特定接口/用户 |
| < 10% | DHCP 服务器 Leasequery 回复异常 — 大概率 **回复不带 IP** |

低命中率时，结合 DHCP 服务器日志确认：

```
DHCPLEASEACTIVE to 10.XX.XX.XX for MAC address XX:XX:XX (0 associated IPs)
                       ^ 回复是 Active         ^ 但不带 IP
```

**这就是问题——服务器确认了 MAC 但没告诉交换机这个 MAC 的 IP。** Address Locking 需要 IP 才能安装 permit 条目。

#### 4. 为什么会进入重查循环

Address Locking 在 permit 表无条目时对入站流量做检查：

| 流量 | 行为 |
|---|---|
| DHCP Discover/Request (0.0.0.0 → 255.255.255.255) | **放行** — 文档明确 |
| ARP with SPA=0.0.0.0 (DAD 探测) | **放行** — 文档明确 |
| 客户端 ARP 携带真实源 IP | **丢弃** — 源 IP 不在 permit 表 |
| 客户端 IP 数据包 (TCP/UDP/ICMP) | **丢弃** — 源 IP 不在 permit 表 |
| L2 控制面协议 (LLDP, STP, CDP) | **放行** — 不检查 |
| DHCP Offer/Ack 入方向 | **丢弃** — 文档明确 |

客户端完成 DORA 后流程：

```
① Discover (0.0.0.0 → 255.255.255.255)  ✓ 放行
② Offer/ACK（双向正常）
③ Request (0.0.0.0 → 255.255.255.255)  ✓ 放行
④ 客户端拿到 IP, 发送免费 ARP (SPA=IP)  ✗ 丢弃！
   → 触发 Leasequery → UNKNOWN/Active(0 IPs) → permit 没装上
   → 客户端再发 ARP → 再丢 → 每 50 秒重查一次 (Arista 内建机制)
   → 死循环，累计 792 次查询
```

#### 5. 解决方案

**短期 — 静态绑定（立即生效）：**

```bash
configure
address locking
   lease 10.64.19.51 mac e0:4e:7a:cf:29:18
```

一旦写入，permit 条目立即安装到硬件，从此不再受 Leasequery 影响。检查：

```bash
show address locking table ipv4
# 应看到 installed
```

**长期 — 排查 DHCP 服务器：**

1. 确认 DHCP 服务器支持并正确实现 RFC 4388 Leasequery
2. 确认 DORA 经过的 relay 和 Leasequery 到达的是同一个 DHCP 后台
3. 排查 Option 82 (Relay Agent Information) 是否导致 lease 存储 key 不匹配：
   - relay 在 DORA 中插入 Option 82 (`ip dhcp relay information option`)
   - 服务器存储 lease 时可能 key = MAC + Option 82
   - 交换机 Leasequery 只带 MAC (RF 4388 标准)，不带 Option 82
   - 服务器匹配不到 → LeaseUnknown 或 LeaseActive(0 IPs)
4. 检查 DHCP pool / scope 配置，确保 lease 数据库正确记录了客户端的绑定

## Pre-Auth VLAN 行为

Arista 与华为的本质差异：**Arista dot1x 认证前没有 pre-auth VLAN**。

```
show dot1x interface ethernet <n> detail:
   Unauthorized access VLAN egress: No     ← 未认证不允许任何VLAN出口
   Unauthorized native VLAN egress: No     ← 未认证不允许native VLAN
```

认证前端口完全隔离，客户端无任何网络访问。认证成功后进入 `switchport access vlan <X>`；认证失败进入 `dot1x authentication failure action traffic allow vlan <Y>`。

这意味着：**客户端必须先完成 dot1x 认证，再发 DHCP 拿 IP。** 与华为不同，华为的 pre-authen VLAN 允许 DHCP 先跑。

## DHCP DORA 在公司网络的行为（真实抓包验证）

在字节网络环境中，通过 macOS 实际抓包验证了 DHCP Offer/ACK 是 **单播（Unicast）**：

```
② Offer (DHCP Server → Client)
   SRC MAC: VRRP/Gateway MAC → DST MAC: 客户端MAC    ← 二层单播
   SRC  IP: DHCP Server IP   → DST  IP: 客户端IP      ← 三层单播

④ ACK (DHCP Server → Client)
   SRC MAC: VRRP/Gateway MAC → DST MAC: 客户端MAC    ← 二层单播
   SRC  IP: DHCP Server IP   → DST  IP: 客户端IP      ← 三层单播
```

**原因：** 客户端 Discover 报文的广播标志位（Flags）= none（0），指示服务器可以直接单播回复。DHCP Relay 通过 Discover 内层的 Client-Ethernet-Address 知道客户端的 MAC，直接单播发送 Offer/ACK。

**对故障排查的意义：** Offer 单播回的 DST MAC 是客户端的真实 MAC。如果 Address Locking 没有 permit 条目 → 交换机丢弃这个单播 Offer → 客户端永远收不到 Offer → DHCP 超时 → 用户无 IP。

完整 DORA 抓包示例（从现场实际 macOS 捕获）参见 `references/arista-dhcp-dora-capture.md`。

## "无 accounting" 诊断流程

当用户认证成功但没有 accounting 时，按以下顺序排查：

### 1. 查 AAA 返回属性

```
show dot1x hosts mac <mac> detail
```

关键字段：
- **VLAN ID**: 为空 → 授权步骤可能失败
- **Tunnel-Private-GroupId**: 为空 → ISE 未下发动态 VLAN
- **Service-Type**: 0xFFFFFFFF → FreeRadius 未设置，ISE 透传空值
- **Framed-IP-Address**: 0.0.0.0 vs `X.X.X.X sourceIpLocking`

### 2. 查 IP Locking 是否学到 IP

```
show address locking table ipv4 | include <mac>
show ip arp mac-address <mac>
```

无条目 = 客户端没发 DHCP。**Address Locking 依赖 DHCP Leasequery → Bluecat，客户端不 DHCP 就没有 IP → accounting Interim-Update 无法携带 Framed-IP-Address。**

### 3. 对比正常/异常用户

当同交换机上有正常用户时，用以下命令逐项对比：
`show dot1x hosts mac <mac> detail`（异常 vs 正常）
`show mac address-table address <mac>`（确认同一 VLAN）
`show running-config interface ethernet <n>`（接口配置一致性）

### 4. 常见结果

| 症状 | 根因位置 | 排查方向 |
|------|---------|---------|
| 无 IP (0.0.0.0) | 客户端 | 客户端未 DHCP；DHCP relay 不可达 |
| 有 IP 但无 accounting | ISE/FreeRadius | 授权步骤失败；Service-Type 异常 |
| VLAN ID 空 | ISE | 未下发 Tunnel-Private-GroupId |
| Address Locking 无条目 | DHCP/Bluecat | Leasequery 未返回；客户端没 lease |

## Filter-Id / ACL 映射验证

Arista 将 AAA 返回的 `Filter-Id`（如 `dev`）映射到本地 ACL。验证方法：

```
show ip access-list | begin <filter-id大写>
```

例如 `Filter-Id: dev` → ACL `DEV`。正常应为 `permit ip any any`。如果 ACL 有 deny 规则（如 `NACROLE`），会阻断特定流量。

## 更多抓包和调试方法

参见 `references/arista-debug-and-capture.md`：monitor session、bash tcpdump、接口计数器对比、dot1x trace、readonly 限制。

## 基线配置对照

SGSIN07 (问题) vs CNDAT02 (基线) 关键差异：

| 配置 | SGSIN07 | CNDAT02 |
|------|---------|---------|
| auth dot1x | group bd_radius | group feilian |
| acct dot1x | group bd_radius (同auth) | group dynamic-author (分离) |
| address locking | 已配置 (VLAN 200, DHCP 10.64.109.8 / 10.72.207.8) | 已配置 |
| accounting update periodic | 无 | 无 (由FreeRadius Acct-Interim-Interval驱动) |
| quiet-period | 30 | 65535 |
| host-mode | multi-host authenticated | (default) |

## 内部文档索引

- 有线接入认证流程故障排查手册: `AIccdbvLGo6P4ox4x6IcVafenCK`
- 有线 dot1x 认证流程详解: `FynMdfaLmo3giRxIeyMcjO8tnab`
- Arista交换机配置说明-用户终端802.1x认证字段: `QUftdvAJBod5XexCk4zc9iQknDf`
