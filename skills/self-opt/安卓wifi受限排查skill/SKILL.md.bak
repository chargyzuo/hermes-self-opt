---
name: 安卓wifi受限排查skill
description: 系统化排查安卓设备WIFI连接后显示“网络连接受限”的问题
version: 1.0.0
trigger: 用户反馈安卓设备连接WIFI后提示“网络连接受限”
---

## 步骤

### 步骤1：确认是否仅系统误报
- 操作：让用户打开浏览器访问 `baidu.com`
- 结果：若能正常打开，则问题为Captive Portal检测被墙

### 步骤2：修改Captive Portal检测服务器（当步骤1成功）
- 方案A（已root）：修改为国内服务器，例如 `connect.rom.miui.com/generate_204`
- 方案B（未root）：通过ADB执行 `adb shell settings put global captive_portal_http_url http://connect.rom.miui.com/generate_204`

### 步骤3：排查真实网络问题（当步骤1失败）
- 检查L3层：用 `ping 223.5.5.5` 测试路由可达性
- 检查L4层：用 `telnet` 或 `nc` 测试TCP 80/443端口
- 检查路由器：重启、检查DHCP、检查MAC过滤
- 检查ISP：联系网络运营商

### 步骤4：验证修复
- 关闭WIFI重新连接
- 确认左上角图标变为正常WIFI符号
- 再次访问baidu.com确认连通