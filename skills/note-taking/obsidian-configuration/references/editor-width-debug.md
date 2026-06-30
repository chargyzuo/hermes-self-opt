# Editor Width: full debugging trace

## Problem

User wanted full-width editor in Obsidian. Tried Editor Width Slider plugin — slider moves but page width doesn't change.

## Debugging steps

### 1. Checked readableLineLength
Found `"readableLineLength": false` in `app.json`. Set to `true` — this is required for any plugin that manipulates `--file-line-width`.

### 2. Checked plugin data
`editor-width-slider/data.json` had `sliderPercentage: "20"`. Bumped to `"70"` for a wider default.

### 3. Restarted Obsidian — still no effect

### 4. Read the plugin source code (`main.js`)

Key finding — the plugin has a code bug:

```javascript
// onload() — line 87-95
async onload() {
    await this.loadSettings();
    this.addStyle();           // Creates empty <style> element
    this.app.workspace.on("file-open", () => {
      this.updateEditorStyleYAML();  // Only called on file-open
    });
    this.createSlider();       // Creates slider, but does NOT call updateEditorStyle()
    this.addSettingTab(...);
}
```

The `updateEditorStyle()` function (line 178-189) writes the CSS:
```javascript
styleElement.innerText = `
  body {
    --file-line-width: calc(700px + 10 * ${this.settings.sliderPercentage}px) !important;
  }
`;
```

But `updateEditorStyle()` is ONLY called from the slider's `input` event listener — never on initial load. The `file-open` handler calls `updateEditorStyleYAML()` which checks for YAML frontmatter `editor-width` field first, and only falls back to `updateEditorStyle()` if there's no frontmatter.

### 5. Checked Minimal theme CSS

The Minimal theme defines:
- `--line-width: 40rem` (its own variable, not Obsidian's `--file-line-width`)
- `--max-width: 88%`

It does NOT use `--file-line-width` on `.cm-sizer` directly. So even when the plugin's CSS fires, it sets the variable on `body` but Minimal doesn't read it for the editor container.

### 6. Root cause

Two compounding issues:
1. **Plugin bug**: CSS not applied on initial load, only on slider drag
2. **Theme incompatibility**: Minimal theme doesn't use `--file-line-width` on `.cm-sizer`, so the plugin's `body`-scoped variable declaration has no visual effect

## Solution

CSS snippet targeting the actual DOM elements, not CSS variables:

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

Enabled via `appearance.json` `enabledCssSnippets` array.

This works because:
- Targets `.cm-sizer` directly (the actual container Obsidian uses for line width)
- `!important` beats any theme CSS
- No dependency on `--file-line-width` or any other CSS variable
- Works in both live preview and reading view