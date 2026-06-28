---
name: feishu-profile-api-research
description: 查询飞书开放平台中个人资料（签名/状态）相关的API支持情况
steps:
  - 确认用户需要查询飞书个人签名(status/description)的API支持
  - 使用lark-cli或OpenAPI文档搜索profile更新接口（如PATCH /contact/v3/users/:user_id）
  - 区分读取接口和写入接口的支持情况
  - 告知用户最终结果，说明哪些操作支持/不支持
---
## Feishu Profile API Research

1. 确认用户所述功能：飞书个人签名(description)和个人状态(personal_status)
2. 搜索API文档：
   - 读取接口：lark-cli contact user_profiles batch_query (支持)
   - 写入接口：PATCH /open-apis/contact/v3/users/:user_id (不支持修改个人签名和状态)
3. 返回结论给用户