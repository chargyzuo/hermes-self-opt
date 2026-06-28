---
schema: 1.0
name: hermes-cron-persistence-setup
inputs:
  - hermes_cli_running: yes/no (是否当前CLI窗口运行)
  - hermes_deployment: pip/brew/other
steps:
  - name: check_deployment
    command: |
      which hermes
      hermes --version
      ps aux | grep hermes | grep -v grep
      brew list --cask 2>/dev/null | grep hermes || true
      ls ~/.hermes/gateway.plist 2>/dev/null || true
    description: 检查hermes安装方式（pip/brew）及是否已有gateway服务
  - name: install_gateway
    condition: deployment == "pip" && no_gateway_service
    command: |
      hermes gateway install
      hermes gateway start
    description: 安装launchd后台服务，使cron持久运行并开机自启
  - name: verify
    condition: true
    command: |
      hermes gateway status
      hermes cron list
      tail -5 ~/.hermes/logs/gateway.log
    description: 验证gateway运行、cron任务存在、无错误
  - name: explain_provided
    command: |
      echo "✅ Gateway已安装并运行，CLI关闭后cron继续触发"
      echo "重启Mac后自动启动，进程崩溃由launchd自动重启"
    description: 告知用户当前状态和验证方式
```