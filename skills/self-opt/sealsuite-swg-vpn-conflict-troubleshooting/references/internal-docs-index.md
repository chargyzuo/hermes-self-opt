# SealSuite SWG + VPN 内部文档索引

## 核心文档

| 文档 | Token | 说明 |
|------|-------|------|
| IT-Oncall SealSuite SWG 运维FAQ | `YH83dU8ego9029xQ3jMcTWBmnEd` | 中文运维 FAQ，含「SWG已连接但VPN无法使用」 |
| SealSuite SWG O&M FAQ (EN) | `SVdcwVHTBi5cLmkQxadc461InIe` | 英文版运维 FAQ，含 VPN vs SWG 对比表 |
| SealSuite SWG 常见问题与解答 | `UjvpwAizoiG02NkyX0UcuL81nPd` | 面向用户的 FAQ，含证书、公共 Wi-Fi 等问题 |
| SealSuite SWG User FAQs (EN) | `C960dz3wro8egixCYl1c3q5ZnNf` | 英文用户 FAQ |
| IT-Oncall SWG 常见问题与解答 | `NEDBdokXModiMDxDRHscycGJn4g` | IT Oncall 版本 FAQ |
| Zscaler to SWG Replacement SOP | `HrM3dC6mAonSMExL2j3c8H9znhe` | 迁移 SOP，含「VPN 优先级高于 SWG」关键引述 |
| Zscaler to SWG Migration Troubleshooting | `YltmwFBpli30KGk2yBScB2jan9d` | 迁移排障指南 |
| Zscaler to SWG Project Overview | `JSEkdf2NgoNujqx2A5gcJuMvnDh` | 项目概览 |
| SWG Rollout Full Data | `Saeesp2YuhOqJXtflMhcVGFHnlg` | 部署数据（Sheet） |

## 搜索技巧

在 Lark 中搜索 SWG 相关文档：

```bash
# 全局搜索
lark-cli drive +search --query "SealSuite SWG" --format json --as user

# Wiki 空间搜索（IT 空间: 7063044846051491842, 基础设施: 7068272999580827649）
lark-cli wiki nodes list --space-id <space_id> --format json --as user

# 读取具体文档
lark-cli docs +fetch --api-version v2 --doc <token> --scope keyword --keyword "<关键词>" --doc-format markdown --as user
```

## 关键架构引述

**来自 SOP 文档 (HrM3dC6mAonSMExL2j3c8H9znhe)**：
> 飞连SWG也是隧道模式，与VPN隧道解耦。VPN隧道优先级高于SWG隧道，即可以通过开启飞连VPN FULL MODE，绕过飞连SWG隧道。

**来自 SWG O&M FAQ (SVdcwVHTBi5cLmkQxadc461InIe)**：
> SWG uses MITM proxy for 80/443 HTTP/HTTPS traffic; VPN provides encrypted tunnel for corporate network access. Both are independent modules.

**来自 常见问题与解答 (UjvpwAizoiG02NkyX0UcuL81nPd)**：
> SealSuite SWG 与 SealSuite VPN 为独立的模块，互不影响。

**来自 运维FAQ (YH83dU8ego9029xQ3jMcTWBmnEd) — 已知问题**：
> 问：客户端显示SWG已连接，但是VPN连接后却无法使用
> 答：请优先协助用户检查以下内容：飞连客户端已升级至3.2.16及以上版本；请检查当前设备Zscaler客户端是否已卸载，或关闭所有策略。

## 已知相关故障群

飞书群 `oc_16edff151f69f4f86c614dc4e42432e8`（SealSuite SWG 故障排查群）：
- 约 6/17~6/30，多位 Seattle 用户报告 SWG + VPN 随机断网
- 状态：未解决，仍在排查
- 线索：禁用 Chrome QUIC 协议待验证
