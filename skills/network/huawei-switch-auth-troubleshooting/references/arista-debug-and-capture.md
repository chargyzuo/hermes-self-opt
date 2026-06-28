# Arista EOS Debug & Packet Capture

## 方法总览

| 方法 | 权限要求 | 用途 |
|------|---------|------|
| `monitor session` | config | SPAN 端口镜像，接 PC/Wireshark |
| `bash tcpdump` | admin/bash | 交换机本地抓包 |
| 接口计数器对比 | readonly | 判断客户端是否在发包 |
| `trace dot1x` | config | dot1x 实时调试日志 |
| `show monitor session` | readonly | 查看已有 SPAN session |

## 方法 1：monitor session（SPAN 镜像）

把目标端口的流量镜像到空闲端口，接 PC 抓包：

```
configure
monitor session dhcp_cap source ethernet 5
monitor session dhcp_cap destination ethernet <空闲端口>
```

查看和删除：
```
show monitor session              # 查看
no monitor session dhcp_cap       # 删除
```

## 方法 2：bash tcpdump（本地抓包）

EOS 基于 Linux，内置 tcpdump。注意：**readonly 账号 `bash` 会被拒绝**（`% Authorization denied`），需要 admin 权限。

```
bash tcpdump -i et5 -n -e                          # 实时抓包
bash tcpdump -i et5 -n port 67 or port 68           # 只看 DHCP
bash tcpdump -i et5 -n -c 100 -w /mnt/flash/et5.pcap  # 写 PCAP 文件
```

导出 PCAP：`bash tftp`、`copy` 或 SCP。

## 方法 3：接口计数器对比（readonly 可用）

不抓包也能判断客户端是否在发包。核心思路：看 `show interface` 的 `packets input` 是否增长。

```
show interface ethernet <n> | include "packets input|broadcasts"
```

隔 30 秒再跑一次，对比数值。如果 `packets input` 不变 → 客户端没发包。同时看 5 分钟速率：

```
5 minutes input rate 230 bps, 0 packets/sec     ← 0 pps = 没发包
```

这是 L2 层面最直接的证据，比抓包更快，且 readonly 可用。

## 方法 4：dot1x trace debug

```
configure
trace dot1x level debug
```

查看日志：
```
show trace dot1x
show log last 100 | include DOT1X
```

注意：`trace` 可能输出密码明文。调试完记得关闭 `no trace dot1x`。

## 针对 DHCP 问题的诊断流程

当怀疑客户端没发 DHCP 时，按顺序：

```
# 1. 接口级：5分钟入向速率
show interface ethernet <n> | include "minutes input rate"

# 2. 计数级：隔30秒对比
show interface ethernet <n> | include "packets input"

# 3. 广播计数：累计收到的广播
show interface ethernet <n> | include "broadcasts"

# 4. 确认 VLAN 成员和 STP 状态
show vlan <vlan-id>
show spanning-tree vlan <vlan-id>
```

如果入向 0 pps 且广播计数不增长 → 客户端根本没发包，问题不在交换机 L2 转发层面。

## Readonly 账号限制

以下是 readonly 账号无法执行的命令，需要 config 或 admin：

```
bash tcpdump ...          → % Authorization denied
bash ...                  → % Authorization denied
configure                 → 需要 config 权限
monitor session ...       → 需要 config 权限
trace dot1x ...           → 需要 config 权限
```

Readonly 可以执行所有 `show` 命令、`terminal length 0`。

## WebSSH 代理注意事项

某些 `show` 命令可能超时（返回空结果），如 `show dot1x all`、`show running-config | begin ...`（大输出）。遇到空结果时：
- 使用更精确的 `| include` 替代 `| begin`
- 拆分成多个小查询
- 如持续失败，减短命令或增加 `max_wait_time`
