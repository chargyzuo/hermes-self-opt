---
name: hermes-dashboard-startup-troubleshoot
description: 诊断和修复 hermes dashboard 无法启动的问题（进程存在但端口未绑定）
trigger: 用户运行 hermes dashboard 后提示 "服务还未开启"
---

1. 检查 hermes 进程是否在运行:
   - 命令: `pgrep -f "hermes dashboard"` 或 `ps aux | grep hermes`
   - 如果无进程: 直接运行 `hermes dashboard`
   - 如果有进程: 进入下一步

2. 检查端口 9119 是否被监听:
   - 命令: `lsof -i :9119` 或 `ss -tlnp | grep 9119`
   - 如果端口已监听: 告知用户访问 `http://localhost:9119`
   - 如果端口未监听: 进程异常，执行下一步

3. 终止异常进程并重启:
   - kill 进程 (例如 `kill -9 <PID>`)
   - 重新运行 `hermes dashboard`

4. 如果重新运行后仍无端口监听:
   - 捕获启动输出，检查是否需要编译前端:
     - 检查 `~/.hermes/dashboard/dist/` 目录是否存在
     - 如果不存在: 执行 `cd ~/.hermes/dashboard && npm build`
     - 如果存在但启动仍失败: 删除 dist 并重新编译

5. 验证服务:
   - 确认端口监听 (`lsof -i :9119`)
   - 运行 `curl -o /dev/null -s -w "%{http_code}" http://localhost:9119` 确认返回 200
   - 告知用户浏览器访问 `http://localhost:9119` 即可使用 Dashboard