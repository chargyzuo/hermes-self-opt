---
name: huawei-mab-pre-auth-troubleshoot
description: 排查华为交换机上MAC认证旁路卡在Pre-authen状态的流程，重点关注IP冲突和RADIUS交互。
version: 1.0.0
---

# 华为设备MAB Pre-auth 故障排查

## 1. 收集基础信息
- `display dot1x` / `display mac-authen` → 确认全局配置
- `display radius-server configuration` → RADIUS服务器组和密钥
- `display domain name <domain>` → 认证方案和计费方案
- `display access-user mac-address <mac>` → 用户状态、认证类型、domain

## 2. 验证RADIUS可达性
- `ping -s 1472 -f <radius-ip>` → 测试path MTU，标准1500排除分片
- `test-aaa user <username> password <pwd> authentication-scheme <...>` → 但注意MAB使用Call-Check，非PAP，此测试可能不准

## 3. 检查端口稳定性
- `display interface <iface>` → 查看`Last physical up/down`，若间隔极短则存在link flap

## 4. 查看认证失败记录
- `display aaa online-fail-record mac-address <mac>` → 失败原因，尤其是`IP address conflict`
- 若有IP冲突，检查同VLAN下其他在线的`access-user`的IP地址

## 5. 定位IP冲突源
- `display dhcp snooping bind` → DHCP绑定表
- `display arp` → ARP表
- 终端侧确认Docker网桥IP等

## 6. 解决与恢复
- 修改冲突IP（如修改Docker bip）或隔离VLAN
- `reset access-user mac-address <mac>` 触发重认证
- 验证成功状态