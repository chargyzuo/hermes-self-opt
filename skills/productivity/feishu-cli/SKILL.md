---
name: feishu-cli
description: Install, configure, authenticate, and use lark-cli (Feishu CLI) — covers setup, auth, spreadsheet reading, multi-sheet navigation, targeted queries, and cron integration patterns.
tags: [feishu, lark, cli, install, auth, config, sheets, spreadsheet, schedule, automation]
---

# Feishu CLI (lark-cli)

Install and configure `lark-cli` — the Feishu/Lark CLI for AI agents. Covers the full setup flow: npm install, skill installation, app credential configuration, and auth login.

## When to use

- User asks to install feishu-cli / lark-cli
- User wants to configure Feishu app credentials for CLI use
- User needs to authenticate lark-cli
- Errors from `lark-cli` about config, binding, or auth
- **Reading shift schedules, calendars, or monthly grid data from Feishu sheets** — see `references/reading-schedules.md` for the date-mapping verification pattern and common pitfalls
- User shares a Feishu/Lark spreadsheet URL and needs data extracted
- Reading schedule/roster sheets for personal automation (cron jobs, reminders)
- Finding metadata or lookup tables within large multi-sheet workbooks

## Installation

```shell
# 1. Install CLI globally
npm install -g @larksuite/cli

# 2. Install CLI skills (27 skills covering docs, sheets, calendar, mail, etc.)
npx -y skills add https://open.feishu.cn --skill -y
```

## Configuration (Hermes context)

### Pitfall: `config init --new` is refused in Hermes

Inside a Hermes session, `lark-cli config init --new` will fail with:

```
config init is refused inside hermes context (would create a parallel app and shadow the existing hermes binding)
```

**Fix:** Add `--force-init` flag:

```shell
lark-cli config init --new --force-init
```

### Alternative: `config bind --source hermes`

If Hermes already has Feishu credentials configured (FEISHU_APP_ID in `~/.hermes/.env`), you can bind instead:

```shell
lark-cli config bind --source hermes --identity user-default
```

**Pitfall:** This requires `FEISHU_APP_ID` to be set in `~/.hermes/.env`. If it's not there, you'll get:

```
FEISHU_APP_ID not found in /Users/.../.hermes/.env
```

In that case, fall back to `config init --new --force-init`.

### Identity presets

When configuring, choose an identity preset:

| Preset | Description | When to use |
|--------|-------------|-------------|
| `bot-only` | Bot identity only, no impersonation | Safer default; public resources only (group chats, shared docs) |
| `user-default` | User identity allowed, can impersonate user | When user needs access to personal resources (calendar, mail, drive) |

**Ask the user** which they want. Default to `bot-only` if unsure.

### The browser config flow

There are TWO different browser flows depending on which config path you took:

#### Flow A: `config init --new` (new app registration)

Interactive — prints a QR code and a URL like:

```
https://open.feishu.cn/page/cli?user_code=XXXX-XXXX&lpv=1.0.56&ocv=1.0.56&from=cli
```

The user opens this URL in a browser to **create** the Feishu app and configure credentials. The CLI waits for confirmation.

**Run in background with PTY** since it blocks on browser completion:

```shell
# background=true, pty=true, notify_on_complete=true
lark-cli config init --new --force-init
```

#### Flow B: `config bind --source hermes` (bind to existing Hermes app)

This is the **more common path in Hermes**. The bind step itself does NOT open a browser — it uses Hermes' existing Feishu app credentials. Browser interaction happens in the separate **auth login** step below.

```shell
# Bind to Hermes' Feishu app (no browser needed for this step)
lark-cli config bind --source hermes --identity user-default
```

## Authentication

After config is set up (either flow), the user must authorize lark-cli to act on their behalf:

```shell
lark-cli auth login --recommend
```

This prints a **device verification URL** to the terminal (NOT a QR code):

```
https://accounts.feishu.cn/oauth/v1/device/verify?
  flow_id=Od6IJ0PrH0dK...&user_code=SZLA-QKHY
```

The user opens this URL in their browser, sees a Feishu OAuth consent page showing their avatar and the list of requested permissions (129 scopes for `user-default`), and clicks "授权" (Authorize). The CLI auto-completes once authorization is granted.

**Pitfall — users often forget they did this:** This is a quick URL copy-paste flow (not a QR scan), takes ~30 seconds, and only happens once. Users commonly don't remember authorizing lark-cli because it feels like any other webpage. If a user questions "how did you get my Feishu access?", this is the answer — they opened that URL and clicked one button, likely weeks ago.

Verify with:

```shell
lark-cli auth status
```

A healthy output shows `"status": "ready"` for the user identity, with `userName` matching the Feishu display name. Token auto-refreshes on expiry — no re-auth needed unless the refresh token expires (typically 7 days of inactivity).

## Installed skills

The `npx skills add` step installs 27 skills covering:
- lark-approval, lark-apps, lark-attendance
- lark-base, lark-calendar, lark-contact
- lark-doc, lark-drive, lark-event
- lark-im, lark-mail, lark-markdown
- lark-minutes, lark-note, lark-okr
- lark-openapi-explorer, lark-shared
- lark-sheets, lark-skill-maker, lark-slides
- lark-task, lark-vc, lark-vc-agent
- lark-whiteboard, lark-wiki
- lark-workflow-meeting-summary, lark-workflow-standup-report

Install location: `~/.hermes/skills/feishu/lark-*/`. After `npx skills add` installs them to `.agents/skills/`, copy them to the unified Hermes skills directory and delete the project-level `.agents/` directory to avoid split-brain.

## Searching All Documents

lark-cli can search across **all** Feishu documents the user has access to — not just one at a time. For full command reference and pitfall details, see `skill_view(name="feishu-cli", file_path="references/searching-documents.md")`.

Two search commands:

### Content search (`docs +search`)

```shell
lark-cli docs +search --query "关键词" --page-size 10
```

Searches docx, wiki, sheets, and other document types by keyword. Returns document titles, tokens, and snippets.

### Filtered search (`drive +search`)

```shell
lark-cli drive +search --query "..." --doc-types docx,doc,sheet,wiki \\
  --created-since 30d --page-size 15
```

Supports filters: `--doc-types`, `--created-since`/`--created-until`, `--edited-since`, `--mine`, `--creator-ids`, `--folder-tokens`, `--space-ids`.

### Pitfall: `search:docs:read` scope

Search requires the `search:docs:read` scope, which is **not** included in the default `auth login --recommend` flow. If search fails with:

```
missing required scope(s): search:docs:read
```

Add the scope:

```shell
lark-cli auth login --scope "search:docs:read"
```

This prints a device verification URL — the user opens it in their browser, sees a minimal consent page for the single new scope, and clicks authorize. The existing scopes are preserved. This is a one-time add-on; the new scope persists with token refresh.

Run in background with PTY (it blocks waiting for browser completion):

```shell
# background=true, pty=true
lark-cli auth login --scope "search:docs:read"
```

After auth completes, verify with `lark-cli auth status` — scope list should now include `search:docs:read`.

### User trigger-phrase convention

This user uses specific Chinese phrases to signal "search Feishu docs first":

| Phrase | Meaning |
|--------|---------|
| 内部文档 | Internal docs — search Feishu before answering |
| 飞书文档 | Feishu docs — search Feishu first |
| 公司文档 | Company docs — search Feishu first |

When any of these appear in a question, do `lark-cli docs +search --query "..."` BEFORE answering — the user expects Feishu-sourced answers, not general knowledge. The scope includes docx, doc, sheet, slides, and wiki.

### Network operations domain docs

For Aruba wireless / Central / Portal / AP troubleshooting, a curated index of
key internal documents (owners, tokens, contents) is maintained at
`skill_view(name="feishu-cli", file_path="references/aruba-wireless-docs.md")`.
Load it when the user asks about Aruba topics — it saves the search step and
points directly to the authoritative docs (运维宝典, 故障排查手册, 诊断库SOP,
Captive Portal deep-dives, etc.).

The same reference file also includes an **AP LED Status Reference** section
(System/Radio LED tables extracted from 运维宝典 → 无线TS). Consult it for
quick decoding of AP535/AP555 LED blink patterns without re-reading doc images.

For **macOS wireless client issues** (excessive roaming, SNR/RSSI drops,
AWDL interference), load `skill_view(name="feishu-cli",
file_path="references/macos-wireless-roaming.md")` — it contains the full
investigation pipeline: `show ap client trail-info` deauth decoding, AWDL
detection/disable commands, and internal script URLs.

## Reading shift schedules

For extracting work shift schedules from Feishu spreadsheets (date
mapping, anchor verification, local JSON caching for cron), see
`references/shift-schedule-pattern.md`. Key pitfalls: month labels are
misleading, always cross-check date mapping with weekday labels and a
user-confirmed reference cell.

## Reading Spreadsheets

For programmatic spreadsheet data extraction and the annotated-CSV parsing
pattern, see `skill_view(name="feishu-cli", file_path="references/reading-sheets.md")`.
Covers: flag conventions, URL-to-token extraction, row finding, multi-sheet
month workbooks, date header parsing, truncation handling, targeted range
queries, finding metadata and lookup tables within sheets, and cron integration.
