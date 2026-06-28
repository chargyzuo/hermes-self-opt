---
name: antigravity-cli
description: "Operate the Antigravity CLI (agy): auth, plugins, sandbox."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Antigravity, CLI, Auth, Plugins, Sandbox]
    related_skills: [claude-code, codex, hermes-agent]
---

# Antigravity CLI (`agy`)

Operator guide for the Antigravity CLI, invoked as `agy`. Run all `agy`
commands through the Hermes `terminal` tool; inspect its config and logs with
`read_file`.

## When to Use

- Installing, updating, or smoke-testing the `agy` binary
- Driving non-interactive `agy --print` / `agy -p` one-shots
- Debugging Antigravity auth, sandbox, permissions, or plugin state
- Delegating tasks to agy (Gemini Pro backend)

## Prerequisites

- The `agy` binary on PATH: `/Users/bytedance/.local/bin/agy`
- VPN required in China (geo-restricted, cosmetic "ineligible" warning is harmless)
- Google account `chargyzuo@gmail.com` has Gemini Pro

## How to Run

Invoke every `agy` command through the `terminal` tool:

```
terminal(command="agy --version")
terminal(command="agy --print 'Summarize the repo in 3 bullets'", workdir="/path/to/project")
```

For non-interactive one-shot prompts, use `script -q /dev/null` wrapper
(bubbletea requires /dev/tty):

```
terminal(command="script -q /dev/null agy -p 'your prompt' --print-timeout 60s")
```

## Core paths

- Binary: `/Users/bytedance/.local/bin/agy`
- App data dir: `~/.gemini/antigravity-cli/`
- Settings file: `~/.gemini/antigravity-cli/settings.json`
- Keybindings file: `~/.gemini/antigravity-cli/keybindings.json`
- Logs: `~/.gemini/antigravity-cli/log/cli-*.log`
- Conversations: `~/.gemini/antigravity-cli/conversations/`

## Auth

If auth breaks, clear credentials and re-authenticate (must be on VPN):

```bash
security delete-generic-password -s "gemini" -a "antigravity"
rm -rf ~/.gemini/antigravity-cli/cache/*
```

Then run `agy` in a real terminal to complete browser OAuth, OR paste the
authorization code from the browser URL by piping it to stdin while agy is
waiting for the OAuth prompt:

```bash
echo "4/0AdVLPx..." | script -q /dev/null agy -p 'hello' --print-timeout 10s
# agy waits for auth, reads code from stdin, authenticates, then runs the command
```

Note: The `--auth-code-from-stdin` flag does NOT exist on the current agy
version. Instead, agy's interactive OAuth prompt reads from stdin — piping
the code while running a `-p` command works because agy first processes auth,
then runs the prompt.

### Quick auth check

Before launching a long agy command, verify auth is still valid:

```bash
script -q /dev/null agy -p 'Reply with just: OK' --print-timeout 10s
```

If this times out or shows the OAuth URL, re-auth is needed.

## MCP Integration

agy has its own MCP config at `~/.gemini/config/mcp_config.json`. Same format
as Hermes — share MCP servers by duplicating entries to both config files.

```bash
# Format for ~/.gemini/config/mcp_config.json
{
  "mcpServers": {
    "serverName": {
      "command": "python3",
      "args": ["/path/to/mcp_server.py"],
      "env": {}
    }
  }
}
```

Verify connected servers inside agy: `/mcp` slash command.

### Model Selection

Select models with `--model` flag on any `agy -p` command:

```bash
# List available models
agy models

# Use a specific model
script -q /dev/null agy -p 'PROMPT' --print-timeout 120s --model "Claude Sonnet 4.6 (Thinking)"
```

**Available models** (`agy models`):

| Model | When to Use |
|---|---|
| **Gemini 3.5 Flash (Medium)** | Default — fastest, most reliable for `--print` mode. Good enough for document generation. |
| **Gemini 3.5 Flash (High)** | Slightly better quality, still fast in `--print` mode. |
| **Gemini 3.5 Flash (Low)** | Cheapest, for trivial tasks. |
| **Gemini 3.1 Pro (Low/High)** | Older Pro model, stable but slower. |
| **Claude Sonnet 4.6 (Thinking)** | Deep reasoning. **Avoid in `--print` mode** — regularly times out at 300s. |
| **Claude Opus 4.6 (Thinking)** | Best for complex analysis. **Avoid in `--print` mode** — regularly times out. |
| **GPT-OSS 120B (Medium)** | Open-source fallback. |

**Real-world finding**: Gemini 3.5 Flash models are the only ones that reliably complete long document generation in `--print` mode within 300s timeouts. Claude models (Opus, Sonnet) time out regularly on multi-paragraph output — they emit long chains of thought that exceed the timeout before producing the final file.

**User default**: The user prefers agy to default to `Gemini 3.1 Pro (High)`.

**Tip**: If you need Claude-level quality for a long document but must use `--print` mode, prompt Gemini Flash with explicit instructions like "write in the style of the reference documents — complete code examples, Mermaid diagrams, and bash verification commands" to bridge the quality gap.

## Delegation from Hermes

Use `delegate_task` to offload tasks to agy (Gemini Pro backend):

```
delegate_task(
  goal="Use agy to ...",
  context="Run via: script -q /dev/null agy -p 'PROMPT' --print-timeout 120s",
  toolsets=["terminal", "file"]
)
```

The child agent runs `script -q /dev/null agy -p "..."` and captures output.
See [references/delegation-mcp-pattern.md](references/delegation-mcp-pattern.md)
for the full architecture, when-to-delegate decision guide, and dual-MCP-config
maintenance notes.

## Pitfalls

- `agy` without arguments requires a real TTY (bubbletea). Use `script -q /dev/null agy -p "..."` from Hermes.
- The "Account ineligible: not currently available in your location" warning is cosmetic — API still works.
- Must be on VPN for Google API access.
- For complex multi-step tasks, prefer `delegate_task` with the agy backend.
- MCP configs are NOT shared between Hermes and agy — must maintain both files.
- **Scratch dir default**: agy writes files to `~/.gemini/antigravity-cli/scratch/` when no workspace is set. After `agy -p` creates a file, the returned path points there — must copy to the actual target dir.
- **Chinese paths**: agy cannot chdir into paths with Chinese characters (the `workdir` param in terminal is rejected). Create a symlink to the target dir first: `ln -sfn "/actual/中文/目录" /tmp/shortcut`, then use `/tmp/shortcut` as workdir.
- **Return code always 0**: agy exits 0 even when auth fails (the OAuth URL is printed as the response). Always check output content, not just exit code.
- **Long prompt timeout**: For document generation, set `--print-timeout` generously (300s+). The 30s default will truncate multi-paragraph responses.
