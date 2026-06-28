# Stage 1 Batch Execution: Real Session Reference

This document captures a real 31-doc batch distillation session, including
commands, pitfalls encountered, and final output structure.

## Source

Feishu doc: `JvYadjdWmovfUJxdJ5BcpAG9nBb` — "Tier2 Network 特殊案例"
→ 32 sub-docs listed in a `<table>` via `<cite>` tags, with doc-id, title, author, notes.

## Session Flow

```
1. Verify auth: lark-cli auth status
   → Bot identity only → missing user token
2. Auth login: lark-cli auth login --domain docs --no-wait --json
   → Generate QR code → User scans → lark-cli auth login --device-code <code>
3. Fetch index: lark-cli docs +fetch --doc "<index_token>" --scope full
   → Parse XML for <cite doc-id="..." title="..."> tags
4. Batch dispatch: 4 delegate_task calls × 8 docs each
   → 3 concurrent max → dispatch 3, then 1 after any finish
5. Each subagent reads docs and writes to ~/.hermes/knowledge/normal/<vendor>/<id>.md
6. Verify: find + wc -l + grep frontmatter
```

## Distillation Prompt (used verbatim in each subagent context)

See `normal-distillation-prompt.md`. The prompt was embedded directly in each
subagent's `context` parameter.

## ID Translation Examples

| Raw title | Generated id |
|---|---|
| 【解决】20231214-IT-8403549-PDI角色用户有线无法认证 | pdi-youxian-wufa-renzheng |
| 【解决】20240110-IT-8698267-话机能接通但无法听不到声音 | huaji-wufa-tingdao-shengyin |
| [解决] IT-9572524 PS Remote Play无法连接到远端PS5 | ps-remote-play-nat |
| 【解决】20231226-IT-8525520-无法访问boe环境下的ipv6地址（OSPFv3 MTU） | 20231226-it-8525520-ospfv3-mtu |

## Vendor Assignment

| doc title | Vendor dir |
|---|---|
| PDI角色用户有线无法认证 (华为720XP) | huawei/ |
| PDI角色终端认证失败 (Arista) | arista/ |
| 中坤DATA实验室设备无法访问外网 | network/ |
| CNPEK19手机测试设备无法获取访客地址 | network/ |
| 用户打开MAC地图显示国际版 | misc/ |
| 邮件中的链接无法正常打开 (非网络问题) | misc/ |
| OSPFv3 MTU / SD-WAN / DNS / 路由 | normal/ (root) |

## Error Handling

### Permission Denied (code 3380004)
- **Cause**: The doc is in another user's private space
- **Action**: Skip silently. Record as "no permission" in summary.
- **Note**: This is NOT a transient error — `--retry` won't help

### Bot vs User Identity
```json
{"identity": "bot", "error": {"code": 3380004}}
```
→ Fix: `lark-cli auth login --domain docs`

## Final Output (31 normal docs)

```bash
find ~/.hermes/knowledge/normal/ -name "*.md" | wc -l
# → 31

# Per-directory breakdown:
# arista/  : 1
# huawei/  : 2
# network/ : 4
# misc/    : 1
# root     : 23
```

## Key Lessons

1. **Delegate_task context must be self-contained**: Include the full distillation prompt + each doc's token + title. Subagents have no access to parent conversation or memory.
2. **Verify counts**: After all batches, check file count matches expected. A subagent may "complete" successfully but have actually skipped docs silently.
3. **lint output files**: Spot-check 2-3 files per batch for frontmatter correctness and section structure. Check that `<img>` alt-text noise was stripped.
4. **Vendor directory**: Add new vendor dirs as needed. Docs that span vendors (e.g. SD-WAN involving multiple vendor devices) go in root `normal/`.
