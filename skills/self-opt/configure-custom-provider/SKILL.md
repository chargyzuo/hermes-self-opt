---
name: configure-custom-provider
description: 在Hermes中配置或更新自定义推理provider，处理环境变量隔离并提供备选方案
---

# 配置自定义 provider

## 步骤
1. 检查 `custom_providers` 是否已包含目标 provider（按 name 或 base_url 匹配）
2. 让用户选择 API key 的提供方式：
   - 读取环境变量（需 warn 终端隔离）
   - 直接输入 key
   - 写入 .env 文件并引用
3. 若选择环境变量但读取失败，提醒用户 export 仅作用于当前 shell，提供替代的 inline python 命令或建议直接输入 key
4. 更新或追加 provider 条目：设置 name, base_url, api_key, default_model（若缺失）
5. 建议用户执行 `hermes config validate` 或进行一次简单推理测试