---
name: network-connectivity-issue-triage
description: 系统化排查VPC/容器网络连通性问题的通用工作流
triggers:
  - "用户报告间歇性断网、服务不可达、DNS解析失败"
  - "系统时间错误导致证书验证失败"
steps:
  - name: "收集基础诊断信息"
    actions:
      - "执行 nslookup <目标域名> 检查DNS解析"
      - "执行 ping <目标IP> 检查基础连通性"
      - "执行 traceroute 检查路由路径"
  - name: "检查网络代理/VPN组件"
    actions:
      - "确认当前VPN/代理状态，临时断开后观察是否恢复"
      - "查看SWG/Zscaler等代理日志"
      - "对比迁移前后的网络行为差异"
  - name: "检查系统时间与NTP"
    actions:
      - "执行 date 确认系统时间"
      - "执行 timedatectl status 检查NTP服务"
      - "验证NTP端口（123/UDP）是否被防火墙拦截"
  - name: "分析临时修复方案"
    actions:
      - "尝试重置DNS缓存、重启网络服务、硬重启设备"
      - "验证临时修复后是否恢复正常"
  - name: "升级或回退组件"
    actions:
      - "将VPN代理升级到最新版本"
      - "回退到之前稳定版本的代理"
      - "重启容器/服务以恢复NTP同步"
  - name: "总结与记录"
    actions:
      - "记录根本原因和解决状态"
      - "更新知识库供后续参考"
