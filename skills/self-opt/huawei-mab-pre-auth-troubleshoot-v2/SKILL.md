---
name: huawei-mab-pre-auth-troubleshoot
trigger: 华为交换机 Dot1x MAB 认证卡在 pre-auth
steps:
  1. 检查交换机上 radius 服务器配置和 shared key
  2. 检查认证服务器（ACS/ISE）可达性及策略
  3. 在交换机上执行 `display dot1x all` 确认客户端状态
  4. 检查 MAC 地址是否被 authorized 或 denied
  5. 排查 IP 冲突：对比终端 IP 与 Docker 网段
  6. 若发现 Docker 容器 IP 冲突，调整 docker network 或使用 --ip 参数分配独立 IP
tags: [huawei, dot1x, mab, authentication, docker]
---
# 华为交换机 Dot1x MAB 认证卡在 pre-auth 排障

## 场景复现
用户 Dot1x MAC 认证（MAB）卡在 pre-authentication 阶段，Radius Access-Request 无响应。

## 排查步骤
1. 确认交换机 radius 配置正确。
2. 测试认证服务器连通性。
3. 查看 dot1x session 状态。
4. 检查 MAC 地址是否被动态授权。
5. 检查网络内 IP 冲突（常见于 Docker 容器）。
6. 调整网络规划后重试。

## 根因
Docker 容器分配了与终端相同的 IP 段，导致 ARP 冲突，交换机无法完成 MAC 认证。