---
name: start-hermes-desktop
description: 启动 Hermes 桌面端 GUI 应用（生产或开发模式）
triggers:
  - user: "hermes桌面端怎么打开"
  - user: "启动桌面端"
  - user: "desktop mode"
steps:
  - step: 确认模式
    check: user 是否想快速使用还是开发模式
    if_quick: 执行 `hermes desktop`，结束
    if_dev: 继续
  - step: 检查依赖
    command: "npm install" 在项目根目录
    expected: 无错误安装完成
    if_error: 提示检查 Node.js 和 npm 版本
  - step: 进入桌面端目录
    command: cd apps/desktop
  - step: 启动开发服务器
    command: npm run dev
    note: 会自动启动 Vite + Electron + Python backend
  - step: 环境变量调试
    variables: ["HERMES_DESKTOP_HERMES_ROOT", "HERMES_HOME"]
    if_error: 检查这些变量是否正确指向 hermes 源码和配置目录
---

# 启动 Hermes 桌面端

## 快速生产启动
```bash
hermes desktop
```

## 开发模式启动
```bash
npm install
cd apps/desktop
npm run dev
```

## 环境变量
- `HERMES_DESKTOP_HERMES_ROOT` - 指定 hermes 源码目录
- `HERMES_HOME` - 指定配置目录（默认 `~/.hermes`）

## 构建命令
- `npm run dist:mac` - 构建 DMG 安装包