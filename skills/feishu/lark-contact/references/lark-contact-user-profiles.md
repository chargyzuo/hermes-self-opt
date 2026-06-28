# user_profiles batch_query — 个人状态 & 个性签名

## 概述

飞书的「个性签名」(description) 和「个人状态」(personal_status) 属于 **profile-v2** 项目，**不在 contact-v3 的 `PATCH /open-apis/contact/v3/users/:user_id` 接口范围内**。lark-cli 将其映射为 `contact user_profiles batch_query`。

## 查询（只读）

```bash
lark-cli contact user_profiles batch_query \
  --params '{"user_id_type":"open_id"}' \
  --data '{"user_ids":["ou_xxx"],"query_option":{"include_description":true,"include_personal_status":true}}' \
  --as user
```

### 身份与权限

| 项目 | 值 |
|------|-----|
| 身份 | **仅 user**（`--as user`），bot 不支持 |
| scope | `profile:user_profile:read` |
| 频率限制 | 100 次/分钟 |

### 返回字段

**description（个性签名）**：
- `default_locale` — 默认语种（如 `zh_cn`）
- `default_value` — 签名文本；空字符串表示真实为空
- `i18n_value` — 国际化签名

**personal_status（个人状态）**：
- `personal_status_id` — 状态 ID
- `title` — 状态名称（如「会议中」）
- `i18n_title` — 国际化名称
- `icon_key` — 状态图标标识（如 `GeneralInMeetingBusy`）
- `effective_interval` — 生效区间（命中表示状态生效中）
- `is_not_disturb_mode` — 是否联动勿扰模式

## 更新（写）

**目前飞书 OpenAPI 未提供公开的更新接口**用于修改 description 或 personal_status。`PATCH /open-apis/contact/v3/users/:user_id` 的请求体中不包含这两个字段——它们属于 profile 项目，不属于 contact 项目。

如需程序化修改个人签名/状态，目前只能通过飞书客户端手动操作。如后续飞书开放了 profile-v2 的写接口，可通过 `lark-cli api` 裸调。

## 注意事项

- **不要混淆**：`contact-v3 PATCH user` 可改姓名/邮箱/手机/部门等，但**不能**改签名和状态
- 如遇 41050 权限错误，检查是否已开通 `profile:user_profile:read` scope
- 跨租户用户的这些字段可能为空
