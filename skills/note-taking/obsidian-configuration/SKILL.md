---
name: obsidian-configuration
description: Configure Obsidian appearance, editor, plugins, and CSS snippets via config files. Use when the user asks to adjust editor width, line length, theme settings, enable/disable plugins, or troubleshoot plugin conflicts.
platforms: [macos]
---

# Obsidian Configuration

Use this skill when the user wants to adjust Obsidian settings programmatically via config files — editor width, readable line length, CSS snippets, plugin management, and troubleshooting plugin/theme conflicts.

## Vault path

This user's vault is at:
```
/Users/bytedance/Library/Mobile Documents/com~apple~CloudDocs/笔记/Obsidian Vault
```

Config files live under `.obsidian/` inside the vault directory.

## Key config files

| File | Purpose |
|------|---------|
| `.obsidian/app.json` | `readableLineLength`, editor settings |
| `.obsidian/appearance.json` | theme, accent color, `enabledCssSnippets` |
| `.obsidian/community-plugins.json` | JSON array of enabled plugin IDs |
| `.obsidian/plugins/<id>/data.json` | Per-plugin settings |
| `.obsidian/snippets/*.css` | CSS snippets |

## Controlling editor width

### Recommended: CSS snippet

The most reliable approach — works across all themes and doesn't depend on buggy plugins.

1. Create `.obsidian/snippets/wide-editor.css`:
```css
.markdown-source-view.mod-cm6.is-readable-line-width .cm-sizer,
.markdown-source-view.mod-cm6 .cm-sizer {
  max-width: none !important;
  margin-inline: auto;
}
.markdown-reading-view .markdown-preview-view {
  max-width: none !important;
  margin-inline: auto;
}
```

2. Enable it in `appearance.json`:
```json
{ "enabledCssSnippets": ["wide-editor"] }
```

Replace `none` with a specific value (e.g. `1200px`) if the user wants a custom width rather than full-width.

### Alternative: Toggle readableLineLength

In `app.json`, set `"readableLineLength": false` to disable line-width entirely. This is simpler but breaks plugins that rely on `--file-line-width` CSS variable.

### Pitfall: Editor Width Slider plugin

The `editor-width-slider` plugin has a code bug — `onload()` creates an empty `<style>` element but doesn't populate it until the slider is first dragged. It also only touches `--file-line-width` on `body`, which Minimal theme ignores in favor of its own `--line-width` variable. **Avoid this plugin** — use the CSS snippet approach instead.

## Plugin management

### Enable/disable a plugin

Edit `.obsidian/community-plugins.json` — it's a JSON array of plugin IDs. Add or remove IDs to enable/disable.

### Check plugin data

Read `.obsidian/plugins/<plugin-id>/data.json` for per-plugin settings.

## Minimal theme conflicts

The Minimal theme defines its own `--line-width: 40rem` and `--max-width: 88%` variables. Plugins that only modify Obsidian's core `--file-line-width` won't reliably override Minimal's editor width. Always use CSS snippets that target the actual DOM elements (`.cm-sizer`, `.markdown-preview-view`) with `!important` when working with Minimal.

## Restart required

Changes to config files require an Obsidian restart to take effect. Inform the user after making changes.