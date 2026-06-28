---
name: trusted-project-support
description: 可信项目（办公安全设备认证）T2 支持：PC 端飞书设备认证、移动端 BYOD/Omnissa 注册与合规问题排查。Load this skill when the user asks about 可信项目, 办公安全设备认证, BYOD enrollment, OMISSSA/Omnissa UEM, passcode compliance, device certificate issues, or 飞书设备认证.
---

# 可信项目（办公安全设备认证）T2 支持

## 项目背景

办公安全设备认证是面向**全体员工**的统一安全方案，基于 X.509 证书构建设备认证和校验能力。

地区差异：
- **CN / APAC**：使用飞连 / SealSuite 注册
- **AMS / EMEA**：使用 Workspace ONE (Omnissa) 注册（即原 BYOD Program）

OMISSSA = Omnissa = Workspace ONE UEM (WS1)，三个名字指向同一个平台。

## 核心内部文档

以下文档是排查问题的权威来源，按优先级排列：

| # | 文档 | Token | Owner | 用途 |
|---|------|-------|-------|------|
| 1 | IT-OSC-T2 办公设备安全认证 SOP | `XBNKdMSKgopZJnxKGmjcog80nYf` | 孙成辉/李春雨 | PC 端主要 SOP |
| 2 | IT-OSC-Trusted Device Mobile device (EMEA+AMS) SOP | `CV1udnZ0coWsSQxHPGSc9mJGnAi` | 王欣茗 | 移动端 BYOD 主 SOP |
| 3 | 办公安全设备认证计划 FAQ（IT内部） | `Ka2ZdBkiRoDhPGx2cPzcsDN7nUf` | 孙成辉 | 项目 FAQ、技术原理 |
| 4 | 可信项目工单培训+wave1支持启动会 智能纪要 | `RtFLdr1UzowGUax3JFvcbTUlnXg` | 李春雨 | 培训背景、流程 |

## 排查通用流程

收到用户报障时，第一步永远是**搜索内部文档**：

```bash
# 搜索飞书文档
lark-cli docs +search --query "<关键词>" --page-size 10

# 拉取文档内容（keyword 模式）
lark-cli docs +fetch --api-version v2 --doc "<token>" --scope keyword \
  --keyword "<关键词>" --context-before 3 --context-after 6
```

文档搜索可能 0 结果，原因：
1. 关键词不匹配 → 换不同角度重试（中文/英文/缩写）
2. 平台名称拼写变体 → OMISSSA 试 Omnissa, WS1, Workspace ONE
3. 结果在下一页 → 注意 `has_more: true`，用 offset 翻页

## PC 端：飞书设备认证

飞书版本必须 ≥ v7.65 才能读到可信证书。排查优先级：

1. **飞书版本** → 升级到最新版
2. **Puppet 活跃时间** → 终端执行 `sudo puppet agent -t -v`
3. **版本达标仍未认证** → 可能是飞书 bug，找洪洋/庆峰重推证书
4. **已认证但仍弹窗** → 清理浏览器 feishu.cn / larkoffice.com / bytedance.net 缓存
5. **以上无效** → 升级 IT-OSC-项目支持经办组
6. **紧急加白** → 1 天无需审批，7 天需 +1/+2 审批

关单技术目录：信息安全 → 零信任与终端准入 → PC端安全证书

## 移动端：BYOD (AMS/EMEA)

### 注册要求

- Android ≥ 15，iOS 不落后最新版超过 2 个主版本（iOS 18 或 26）
- 最多同时注册 2 台设备
- 注册后必须安装 3 个 app：Hub、Lark、MTD (Mobile Threat Defense)

### Passcode 合规（高频问题）

**关键陷阱**：SOP 注册指引说 "passcode should be 4 digits"，但 Omnissa UEM 实际策略要求 **PIN at least 8 characters**（或使用生物识别）。用户设 4 位密码会被判 "Passcode is not compliant"。

排查步骤：
1. 确认用户有锁屏密码
2. 要求设为 ≥ 8 位或使用指纹/Face ID
3. 打开 Intelligent Hub → 手动 Sync
4. 等 5-10 分钟让 UEM 重新评估
5. 仍不合规 → Unenroll 后重新 Enroll
6. 升级 IT-OSC-Non Network 检查 WS1 Smart Group/Profile

### 其他常见移动端问题

| 问题 | 关键动作 |
|------|---------|
| 飞书登录拦截 | 检查证书 (SCEP)、飞书版本 ≥ 7.55、curl 验证 |
| Enroll 后只有 MTD+Privacy | 升级 IT-OSC-Non Network 检查 WS1 组 |
| Profile Installation Failed | 检查 WS1 Smart Group → Unenroll → Re-enroll |
| Enroll failed / 超过 2 台 | Unenroll 旧设备 |
| 飞书自动消失 | MTD 不合规 → 7 天自动卸载；或 Root/越狱 |
| Android unenroll 后重新 enroll 失败 | 升级 IT-OSC-Non Network，检查 WS1 状态 |

关单技术目录：信息安全 → 零信任与终端准入 → BYOD，备注 "BYOD Related"

### Omnissa WS1 关键 URL

- 管理后台：https://connect.omnissa.com/csp/gateway/portal/#/home/overview
- 设备日志收集：https://docs.omnissa.com/zh-CN/bundle/TroubleshootingandLoggingGuideV2306/page/WorkspaceONEUEMDevice-SideLogging.html
- 用户注册指引 ITKB：https://it.bytedance.com/portal/articles/247914954824876951?lang=1
- Unenroll 指引：https://bytedance.sg.larkoffice.com/docx/Yy1idXtaLo4Sxtx6QSEllll7gb7

## 升级路径

| 场景 | 升级目标 |
|------|---------|
| PC 证书问题无法解决 | IT-OSC-项目支持经办组 |
| 移动端 WS1 组/Profile 问题 | IT-OSC-Non Network |
| WS1 组正确但仍异常 → | Infra |
| 证书已安装但飞书拦截 | IAM Oncall（飞书安全与合规） |
| BYOD 策略咨询 | IT Security |
| 设备不支持/无法注册 | IT-OSC-Non Network |
| 非 Corporate Phone 地区需要加白 | IT-OSC-Non Network |

## 给用户的反馈格式

所有面向用户的回复遵循：
- 简洁步骤（不超过 3-4 步）
- 每个步骤一句话说明原因
- 避免内部术语（不说 WS1/Omnissa，说 "设备管理平台"）
- 提供自助链接

内部排查信息（WS1 后台截图、Smart Group、Old/New Tenant）**禁止截图分享给用户**。
