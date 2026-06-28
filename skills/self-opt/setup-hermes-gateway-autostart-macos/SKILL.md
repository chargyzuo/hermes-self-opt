---
name: setup-hermes-gateway-autostart-macos
description: 在macOS上为CLI模式下通过pip安装的Hermes设置Gateway后台服务，实现开机自启和cron持久运行
triggers:
  - 用户需要hermes cron在关闭终端后继续运行
  - 用户需要重启Mac后hermes自动启动
steps:
  - 检查hermes版本和安装方式：`hermes --version`和`which hermes`
  - 检查是否已有gateway服务：`hermes gateway status`
  - 若未安装，执行`hermes gateway install`创建launchd plist（~/Library/LaunchAgents/ai.hermes.gateway.plist）
  - 启动gateway：`hermes gateway start`
  - 验证服务状态：`hermes gateway status`和`ps aux | grep hermes`
  - 验证cron是否生效：`hermes cron list`
  - 可选：查看日志 `tail -f ~/.hermes/logs/gateway.log`
