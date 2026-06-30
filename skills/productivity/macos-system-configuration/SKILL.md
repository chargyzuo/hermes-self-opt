---
name: macos-system-configuration
description: "Programmatic macOS system configuration: Night Shift control, terminal input troubleshooting, and SSH keep-alive setup."
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [macos, night-shift, corebrightness, iterm2, ssh, troubleshooting]
---

# macOS System Configuration

Programmatic control of macOS system settings that matter for Hermes and terminal workflows. Covers Night Shift (CoreBrightness private framework), iTerm2 input conflicts with prompt_toolkit, and SSH keep-alive configuration.

## When to Load

- User asks to enable/configure Night Shift programmatically
- Hermes CLI input becomes unresponsive (can't type or delete)
- User mentions iTerm2 and character injection (anti-idle, "When idle send ASCII code")
- SSH keep-alive configuration on macOS

## Night Shift Control

### Background

On modern macOS (Sequoia 15+ / macOS 26+), the traditional approaches for Night Shift control do NOT work:

- **No `com.apple.CoreBrightness` plist exists** — `defaults read com.apple.CoreBrightness` fails with "domain does not exist"
- **`defaults write` fails** — cannot write to non-existent domain
- **PyPI `nightlight` package is unrelated** — it's a config reader, not a Night Shift controller
- **`corebrightnessdiag` is read-only** — diagnostic tool only
- **AppleScript/System Events** — requires accessibility permissions, often denied

### Approach: CoreBrightness Private Framework via Swift

The only working programmatic approach found is using the CoreBrightness private framework through dynamically-loaded Swift:

```swift
import Foundation

guard let bundle = Bundle(path: "/System/Library/PrivateFrameworks/CoreBrightness.framework") else { exit(1) }
bundle.load()

guard let CBClient = NSClassFromString("CBClient") as? NSObject.Type else { exit(1) }
let client = CBClient.init()
let bl = client.perform(NSSelectorFromString("blueLightClient"))!.takeUnretainedValue()

// Force enable Night Shift at max strength
bl.perform(NSSelectorFromString("setEnabled:"), with: true as NSNumber)
bl.perform(NSSelectorFromString("setStrength:commit:"), with: 1.0 as NSNumber, with: true as NSNumber)
```

Key methods discovered on `CBBlueLightClient`:
- `setEnabled:` / `setEnabled:withOption:` — toggle Night Shift
- `setStrength:commit:` — set warmth (0.0–1.0)
- `setMode:` — 0 = manual
- `setSchedule:` — set on/off schedule
- `getBlueLightStatus:` — read current state
- `getStrength:` / `getCCT:` — read current values

### Pitfall: `setSchedule:` Parameter Format

**DO NOT pass NSDictionary to `setSchedule:`.** The method expects a specific C struct, and passing an NSDictionary corrupts the schedule data (garbage values like `NightStartHour = "-157511256"` appear in `corebrightnessdiag` output).

If the schedule gets corrupted, the user must manually fix it in **System Settings → Displays → Night Shift**. There is no known programmatic fix without knowing the exact struct layout.

The `setEnabled:` + `setStrength:commit:` approach is safe and does not corrupt any persistent state.

### Script

The Swift script is available at `scripts/nightshift-enable.swift`. Compile and run:

```bash
swiftc -o /tmp/nightshift-enable scripts/nightshift-enable.swift && /tmp/nightshift-enable
```

### Verification

```bash
/usr/libexec/corebrightnessdiag nightshift-internal
```

Look for `BlueReductionEnabled = 1` — that means Night Shift is on.

## iTerm2 Input Freezing with Hermes

### Symptom

After starting Hermes, typing text, leaving the terminal idle, then returning — input becomes unresponsive. Cannot delete or edit, can only press Enter to send the corrupted text to Hermes.

### Root Cause

iTerm2 has a feature: **Preferences → Profiles → Session → "When idle, send ASCII code"** (or "Anti-idle"). This periodically injects characters (commonly `@`, ASCII 64) into the terminal's stdin to prevent SSH remote disconnection.

Hermes CLI uses **prompt_toolkit**, which reads raw terminal input. Injected characters corrupt prompt_toolkit's internal buffer, causing the input widget to freeze.

This can also be set per-session via **Session → Edit Session** in the iTerm2 menu bar.

### Fix

1. **Disable the iTerm2 feature** — uncheck "When idle, send ASCII code" in Preferences
2. **Use SSH-level keep-alive instead** — add to `~/.ssh/config`:

```
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 5
```

SSH protocol-level keep-alive sends encrypted packets at the transport layer — nothing reaches the terminal, prompt_toolkit is unaffected.

### Additional Defense: tmux

If running Hermes over SSH, wrap it in tmux:

```bash
ssh server
tmux new -s hermes
hermes
```

If SSH drops, reconnect with `tmux attach -t hermes`. No character injection needed.

### Quick Recovery If Already Frozen

- `/redraw` + Enter — forces prompt_toolkit UI repaint
- `Ctrl+L` — terminal-level clear/redraw
- `Ctrl+C` — exit and restart Hermes

## macOS DHCP / APIPA Diagnosis

### Symptom: Physical Link Up But IP = 169.254.x.x

When `ifconfig enX` shows `status: active` and `media: autoselect (1000baseT <full-duplex,...>)` but the `inet` address is `169.254.x.x`:

```
inet 169.254.85.235 netmask 0xffff0000 broadcast 169.254.255.255
```

This is an APIPA (Automatic Private IP Addressing) address. The physical layer is healthy — cable, switch port, speed/duplex negotiation all passed. The problem is DHCP failure.

### Diagnostic Flow

```bash
# Verify physical status
ifconfig en0
# Look for: status: active, 1000baseT, full-duplex, flags include RUNNING

# Check current IP
ipconfig getifaddr en0

# Try manual DHCP renew
sudo ipconfig set en0 DHCP

# Or full reset
sudo ifconfig en0 down
sudo route flush
sleep 2
sudo ifconfig en0 up

# Check DHCP server
ipconfig getoption en0 server_identifier

# Capture DHCP traffic
sudo tcpdump -i en0 -c 10 port 67 or port 68 -n
```

### Common Causes

| Cause | Check |
|-------|-------|
| Switch port disabled / VLAN mismatch | `show interfaces status`, `show vlan` on switch |
| DHCP relay broken | Relay IP reachable? Relay configured on correct SVI? |
| DHCP scope exhausted | Check DHCP server pool utilization |
| Client supplicant not triggering DHCP | After dot1x auth, client needs to renew DHCP |
| Cable / port flapping | `ifconfig en0` media status should be stable `active` |

### 169.254.x.x Does NOT Mean Hardware Fault

Many users panic when they see `169.254.x.x` — it's macOS's normal behavior when DHCP fails. The interface gets this link-local address automatically so basic local-link communication (ARP, mDNS) still works. The fix is always DHCP-side, not hardware-side.

## Hermes CLI Session Context Optimization

When Hermes CLI session consumes too many tokens on startup (20K+ tokens before any user input), see `references/hermes-session-context-optimization.md` for a complete diagnostic-optimization workflow covering `platform_disabled`, MCP server toggling, guidance trimming, and persona pruning.

Quick check:
```bash
hermes prompt-size          # show system prompt + tool schemas breakdown
hermes config edit           # edit config → skills.platform_disabled.cli
hermes config set mcp_servers.wechat.enabled false  # disable unneeded MCP
```

Changes take effect after `/reset`.

## Cow Knowledge Vault (User Knowledge Base)

The user maintains an Obsidian knowledge vault at `~/cow/knowledge/` containing structured network troubleshooting docs, vendor configs, and case studies. See `references/cow-knowledge-vault.md` for a document index.

When asked about Arista, Huawei, or other network topics not covered by installed skills, check this vault first — it is the user's curated source of truth.

## CLI Input Troubleshooting — Extended Diagnostics

### Quick Symptoms Checklist

- You can type, but some keys don't work (Backspace, arrows)
- Input field becomes completely unresponsive — only Enter sends
- Characters randomly appear in the input buffer you didn't type
- Problem worsens after leaving the terminal idle for a while

### iTerm2 Triggers

Check: **iTerm2 → Settings → Profiles → [your profile] → Advanced → Triggers**

Triggers can send text on certain patterns or idle conditions. Look for any trigger that sends keystrokes.

### Background Keep-Alive Scripts

Check the running process tree for scripts that echo/printf to the terminal:
```bash
ps aux | grep -iE 'sleep|while' | grep -v grep
```
Look for patterns like `while true; do printf '@'; sleep 60; done`.

Also check: tmux config (`~/.tmux.conf`), screen config (`~/.screenrc`), launch agents (`~/Library/LaunchAgents/`), Keyboard Maestro, BetterTouchTool, Hammerspoon.

### CLI Fails to Start — "could not open TTY" (Go bubbletea TUIs)

Go-based TUI tools using the **bubbletea** framework (e.g. `agy` / Antigravity CLI) require a real controlling terminal. When run through Hermes' `terminal` tool or any non-TTY context, they fail with:

```
bubbletea: could not open TTY: open /dev/tty: device not configured
```

**Workaround for non-interactive use**: Wrap with `script` to allocate a PTY:
```bash
script -q /dev/null agy --print "your prompt here"
```

**For interactive sessions**: Use the Hermes `terminal` tool with `pty=true`, or run the CLI directly in a real terminal emulator.

Common bubbletea-based CLIs affected: `agy` (Antigravity), `gh-dash`, `lazygit`, `lazydocker`, `gum`-based tools.

### Prevention

- Never use character-injection for SSH keep-alive with prompt_toolkit tools
- Use SSH `ServerAliveInterval` or `tmux`/`screen` for session persistence
- If using tmux: run Hermes inside tmux on the remote host, not directly over SSH
- For bubbletea TUIs driven through Hermes: use `pty=true` or the `script -q /dev/null` wrapper
