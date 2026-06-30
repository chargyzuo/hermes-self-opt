---
name: feilian-vpn-data-plane-troubleshoot
description: 排查飞连VPN隧道数据面不通的标准化流程，适用于Full Tunnel或Split Tunnel模式下内网域名解析失败或路由异常。
triggers:
  - 请求包含“飞连VPN”、“DNS解析”、“路由不通”、“隧道数据面”等关键词
  - 用户描述nslookup内网域名超时，ping内网IP失败
---

# 飞连VPN数据面问题排障流程

## 1. 快速确认网络可达性
- 让用户测试外网连通性（如ping 8.8.8.8）以排除基础网络故障。

## 2. 检查系统DNS配置
```cmd
ipconfig /all | findstr /i "dns"
netsh interface ipv4 show dnsservers
```
期望：飞连虚拟网卡DNS为127.0.0.1，且无其他网卡配置不同DNS。

## 3. 检查DNS代理监听状态
```cmd
netstat -ano | findstr :53
```
确保仅飞连进程监听127.0.0.1:53，无其他代理冲突。

## 4. 检查路由表
```cmd
route print
```
- Full Tunnel模式：应有0.0.0.0/1和128.0.0.0/1指向飞连网关。
- Split Tunnel模式：应包含内网网段路由（如10.0.0.0/8）。

## 5. 验证实际出口
```powershell
Find-NetRoute -RemoteIPAddress <内网IP>
```
确认下一跳为飞连网关，接口为飞连虚拟网卡。

## 6. 测试隧道连通性
```powershell
ping <飞连虚拟网卡IP> -n 2
ping <飞连网关IP> -n 2
```
如果ping不通，说明隧道数据面已断。

## 7. 检查虚拟适配器残留
```cmd
ipconfig /all
```
查看是否存在多个Wintun/TAP实例，特别是标有#1、#2的残留，表明切换Server Node时未清理干净。

## 8. 决策与修复
- **数据面通但DNS解析失败**：检查飞连split DNS配置或手动添加hosts。
- **路由正确但数据面不通**：重启飞连客户端或操作系统，如仍无效则卸载并重装虚拟网卡驱动。
- **路由丢失或指向错误接口**：手动清理残留虚拟适配器，重新连接飞连。
- **间歇性故障**：用户频繁切换Server Node导致竞态，建议避免切换，或每次切换后执行一次完整重连。