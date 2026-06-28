---
description: 华为交换机MAC认证失败排查标准流程
os: VRP
version: "5.170"
category: troubleshooting
---

# 华为交换机MAC认证排障流程

## 阶段1：收集基础信息

```
<<< 查看MAC地址当前的认证状态 >>>
dis access-user mac-address <MAC>

<<< 查看该MAC的历史认证失败记录 >>>
dis access-user online-fail-record mac-address <MAC>

<<< 查看MAC表位置 >>>
dis mac-address <MAC>
```

## 阶段2：检查IP通信层

```
<<< 确认ARP表中是否有该客户端 >>>
dis arp | include <MAC>

<<< 查看DHCP snooping确认DHCP分配状态 >>>
dis dhcp snooping user-binding mac <MAC>
```

## 阶段3：检查端口配置

```
<<< 查看端口认证模式 >>>
dis dot1x interface <interface>
dis mac-authen interface <interface>

<<< 查看端口配置（确认VLAN、MAB参数） >>>
dis this interface <interface>
```

## 决策逻辑

1. 若 `dis access-user` 显示 success → 认证通过
2. 若 `online-fail-record` 只有EAPOL timeout → 正常MAB fallback
3. 若认证会话IP ≠ DHCP snooping分配IP → 以DHCP snooping为准
4. 若认证成功 + DHCP完成但ARP无条目 → 客户端未使用分配IP
