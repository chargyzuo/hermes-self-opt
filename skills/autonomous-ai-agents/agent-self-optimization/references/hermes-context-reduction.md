# Hermes Session Context Bloat — Diagnose & Fix

Session startup eating 20K+ tokens before the first user message? Root cause is almost always
**too many enabled skills + toolsets + MCP schemas** injected into the system prompt.

## Quick Diagnosis

```bash
# Count enabled skills
hermes skills list 2>&1 | grep -c 'enabled$'   # >30 is concerning, >100 is critical

# See enabled toolsets + MCP tools
hermes tools list --platform cli

# These two numbers are your context budget hogs.
```

## Skill Pruning

### Interactive (recommended for first pass)
```bash
hermes skills config    # TUI — requires real terminal, not pipeable
```

### Non-interactive / batch
Edit `~/.hermes/config.yaml` directly:

```yaml
skills:
  platform_disabled:
    cli:
      - apple-notes
      - ascii-art
      - lark-approval
      # ... 138 skills disabled, 23 kept
```

The config path is `skills.platform_disabled.<platform>`, NOT `skills.disabled` (that's global).
`hermes skills list --enabled-only` does NOT reflect `platform_disabled` (it doesn't read `HERMES_PLATFORM`
env), but the actual system prompt generator DOES respect it at session startup.

### Target
- Default CLI: 15–30 enabled skills
- Disable entire categories you don't use daily: feishu, creative, media, social-media, smart-home,
  apple, email, mlops, data-science, most self-opt

## Toolset Pruning

Non-interactive, per-platform:
```bash
hermes tools disable --platform cli computer_use image_gen tts vision delegation cronjob code_execution
```

MCP tools (long schemas — disable unless actively using):
```bash
hermes tools disable --platform cli wechat:get_messages wechat:send_text_message ...
hermes tools disable --platform cli switch:switch_execute switch:switch_get_prompt ...
```

Verify:
```bash
hermes tools list --platform cli
```

## Compression (supplementary, not primary)

Compression compresses conversation HISTORY, not the initial system prompt.
It helps long sessions but won't fix session-start bloat.

```bash
hermes config set compression.enabled true
hermes config set compression.threshold 0.6    # trigger at 60% context
```

## Expected Results

| Component | Before | After |
|-----------|--------|-------|
| skills in prompt | 161 (all) | 15–30 |
| toolsets | ~15 enabled + 2 MCP servers | 9 core + 0 MCP |
| Appx. session-start tokens | 20K–30K | 8K–12K |

## Pitfalls

- **`hermes skills config` is TUI-only** — can't pipe, can't automate. Use config.yaml edit for batch.
- **`--enabled-only` flag lies** about platform_disabled — trust the next session, not the listing.
- **All changes require `/reset` or new session** to take effect. Tools/skills are snapshotted at startup.
- **Don't disable `skills` toolset itself** — you need it to re-enable things.
- **Keep `hermes-agent` skill enabled** — it has the CLI reference and setup commands.
