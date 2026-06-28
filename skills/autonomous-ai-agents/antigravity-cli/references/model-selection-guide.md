# agy Model Selection Guide

## Quick Reference

| Need | Model | Command |
|---|---|---|
| Fast, reliable document gen | `Gemini 3.5 Flash (High)` | `--model "Gemini 3.5 Flash (High)"` |
| Default (user preference) | `Gemini 3.1 Pro (High)` | `--model "Gemini 3.1 Pro (High)"` or omit flag |
| Deep reasoning (short output) | `Claude Opus 4.6 (Thinking)` | `--model "Claude Opus 4.6 (Thinking)"`, keep prompt short |
| Cheapest | `Gemini 3.5 Flash (Low)` | `--model "Gemini 3.5 Flash (Low)"` |

## Claude Models in `--print` Mode: Known Limitation

Claude Opus and Sonnet 4.6 (Thinking) emit very long chains-of-thought before producing the final output. In `--print` mode, this causes regular timeouts:
- **Claude Opus**: Consistently times out at 300s for moderate-to-long document generation (e.g. 500+ line files)
- **Claude Sonnet**: Same issue, slightly less severe but still unreliable
- **Gemini Flash/Pro**: Complete similar tasks within 60-120s reliably

### Workaround: Emulate Claude quality on Gemini Flash

When the user wants "Claude Opus quality" for a long document:
1. Keep the prompt self-contained (no file reading — that adds 30-60s delay)
2. Add explicit style guidance: "write in the style of documents X — complete code examples, Mermaid diagrams, bash verification commands"
3. Use `Gemini 3.5 Flash (High)` or `Gemini 3.1 Pro (High)` with `--print-timeout 300s`
4. Result quality is comparable when the prompt contains enough format/structure examples

## OAuth Auth Flow

When agy shows the OAuth URL, the user can paste a code:
```bash
echo "4/0A...token..." | script -q /dev/null agy -p 'prompt' --print-timeout 60s
```
The `--auth-code-from-stdin` flag does NOT exist — agy reads auth from stdin during its interactive prompt.

## Chinese Path Workaround

agy cannot chdir into paths with Chinese characters in `workdir`. Use:
```bash
ln -sfn "/actual/中文/目录" /tmp/shortcut
```
Then `workdir=/tmp/shortcut`.
