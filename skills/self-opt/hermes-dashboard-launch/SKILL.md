---
name: hermes-dashboard-launch
description: 诊断并恢复 Hermes Agent 网页版 Dashboard 无法启动的问题
steps:
  1. 检查 'hermes dashboard' 进程是否运行 (ps aux | grep hermes)
  2. 如果进程存在但端口 9119 未绑定，杀死进程 (kill <PID>)
  3. 重新启动: hermes dashboard
  4. 若首次启动 (dist 不存在)，等待 npm build 完成
  5. 验证端口 9119 是否监听 (ss -tlnp | grep 9119)
  6. 验证 HTTP 200 响应: curl -o /dev/null -s -w "%{http_code}" http://localhost:9119
  7. 通知用户访问 http://localhost:9119