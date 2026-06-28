---
name: android-wifi-limited-connectivity-troubleshooting
description: 系统化排查安卓设备WIFI连接后显示网络连接受限的问题（英文工作流）
inputs:
  - symptom: "安卓连接WiFi后显示网络连接受限"
steps:
  - step: 1
    action: 验证互联网连通性
    details: 连上WiFi后打开浏览器访问 baidu.com
    decision: 如果能打开baidu.com，说明是因Captive Portal检测被墙导致的伪问题
  - step: 2
    action: 修改Captive Portal服务器
    details: |
      方法A (已root): 修改captive portal服务器为国内地址 (如 connect.rom.miui.com/generate_204)
      方法B (未root): 通过ADB执行命令
      adb shell settings put global captive_portal_http_url http://connect.rom.miui.com/generate_204
  - step: 3
    action: 定位网络层问题
    details: ping 223.5.5.5 验证路由是否可达
  - step: 4
    action: 定位传输层问题
    details: 使用telnet或nc测试TCP/UDP端口连通性
  - step: 5
    action: 定位应用层问题
    details: 检查代理、VPN或防火墙设置
