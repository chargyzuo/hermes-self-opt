---
id: mab-fallback-dot1x-diagnosis
name: MAB Fallback 802.1X 故障诊断
version: 1.0
description: 诊断Huawei交换机上MAB回退认证（dot1x超时→MAC认证成功但客户端不通）的问题。
author: AI Agent
status: draft
---

# MAB Fallback 802.1X 故障诊断

## 1. 收集基础信息
```bash
# 检查目标MAC当前在线状态
dis access-user | include <MAC>
# 检查历史失败记录
dis access-user online-fail-record | include <MAC>
# 检查ARP
dis arp | include <MAC>
# 检查DHCP Snooping
dis dhcp snooping binding | include <MAC>
# 检查端口配置
dis current-configuration interface GigabitEthernet <端口号>
```

## 2. 分析时序
- 对比online-fail-record中802.1x失败时间与当前成功时间：如果只差1-2秒，说明是正常的MAB fallback流程。
- 比较access-user中的IP和DHCP snooping中的IP：如果不一致，说明客户端没有使用分配的IP。

## 3. 定位根因
- **情景A**: access-user显示成功，ARP表无条目 → 客户端未实际使用IP通信（配了静态错误的IP/网卡未配置）。
- **情景B**: dot1x失败时间与MAB成功时间基本同时 → 正常fallback，非故障。
- **情景C**: 端口配置缺少认证模式 → 确认`dot1x enable`和`mac-authen`配置。

## 4. 结论
- 认证成功不等于客户端通信正常。最终要检查ARP。
- 如果access-user里的IP是“脏数据”（如旧会话IP），而DHCP分配了另一个IP，说明客户端用了不同的IP地址。
- 建议客户端检查网卡配置，确保使用DHCP分配的IP，并尝试ping网关验证连通性。