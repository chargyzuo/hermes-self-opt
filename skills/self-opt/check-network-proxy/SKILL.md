---
name: check-network-proxy
description: 通过两端抓包对比确认client与server之间是否存在代理（负载均衡/TLS代理）
triggers:
  - 需要验证网络中间是否有代理设备
---
## 步骤
1. 在client端执行tcpdump捕获发往server的包，记录源IP、目的IP、MAC地址。
2. 在server端执行tcpdump捕获来自client的包，记录源IP、目的IP。
3. 比较server端看到的src IP是否等于client的真实出口IP，以及client端看到的dest IP是否等于server的真实IP。
4. 若不相等，则存在代理；若相等，则可能直连。