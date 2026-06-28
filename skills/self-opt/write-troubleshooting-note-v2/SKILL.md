---
name: write-troubleshooting-note
description: 从飞书对话/合併转发中提取排障信息，撰写排障笔记并归档到 Obsidian
category: self-opt
triggers:
  - 用户要求写排障笔记 / 根据聊天记录写笔记 / 归档 Obsidian
steps:
  - title: 提取信息
    action: 从飞书合并转发/群聊中解析时间线、参与者、操作链、发现
  - title: 加载模板
    action: 自动加载 troubleshooting-doc skill 获取格式规范
  - title: 判断解决状态
    action: 若存在确认的根因和解决方案，使用“已解决”模板；否则使用“未解决”模板（含待尝试方案）
  - title: 撰写笔记
    content: |
      模板结构：
      - 背景
      - 问题现象
      - 环境信息（系统、Node版本、代理状态）
      - 排查过程（分阶段）
      - 根因分析（或暂未确定）
      - 解决方案 / 待尝试方案（优先级排序）
      - 验证命令
      - 相关文档/人员
  - title: 归档 Obsidian
    action: 将文件保存至 Obsidian Vault/Troubleshooting/<标题>.md
    external_commands:
      - echo '已写入'
requirements:
  - 正文中文，术语英文，命令输出不翻译
  - 自动加载 troubleshooting-doc 获取格式规范