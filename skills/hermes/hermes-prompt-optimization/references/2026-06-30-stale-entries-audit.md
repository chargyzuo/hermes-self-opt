# Stale Disabled Entries Audit — 2026-06-30

## Session: Prompt bloat analysis

User asked "为何这次session开始用的token如此之多" (why is this session's token count so high).

## Current State

| Metric | Value |
|--------|-------|
| Total prompt | 9,097 chars (~2,274 tokens) |
| Skills section | 5,243 chars (58.2%) |
| Agent identity | 3,077 chars (34.2%) |
| Mid-turn steering | 679 chars (7.5%) |
| Total installed skills | 169 |
| Disabled on CLI (config) | 145 |
| Actually matched & disabled | 138 |
| **Stale entries** | **7** |
| **Active skills (not disabled)** | **31** |

## Optimization Already Applied

- `tool_use_enforcement`: false
- `task_completion_guidance`: false
- `parallel_tool_call_guidance`: false
- `environment_probe`: false
- `memory.memory_char_limit`: 500

## Stale Disabled Entries

These names are in the `platform_disabled.cli` list but no matching skill dir exists:

| Stale name | Likely renamed to |
|---|---|
| `Detect Running Service Before Recommend` | `detect-running-service-before-recommend` |
| `MAB Fallback 802.1X 故障诊断` | `mab-fallback-dot1x-diagnosis` |
| `audiocraft-audio-generation` | `audiocraft` |
| `evaluating-llms-harness` | `lm-evaluation-harness` |
| `segment-anything-model` | `segment-anything` |
| `serving-llms-vllm` | `vllm` |
| `飞书文档批量蒸馏` | `feishu-doc-batch-distill` |

## Active Skills (31 total)

Categories that contribute most to the 5,243-char skills section:

- **Networking/troubleshooting** (core): aruba-ap-troubleshooting, tcp-connectivity-troubleshooting, huawei-switch-auth-troubleshooting, huawei-mac-auth-debug, pcap-analysis, netbox-device-query, etc.
- **Self-opt/meta**: hermes-agent, hermes-prompt-optimization, context-bloat-optimizer, systematic-debugging, create-agent-prompt-inspection-script, etc.
- **Docs/notes**: research-notes, obsidian, troubleshooting-doc, write-troubleshooting-note-v2
- **Audio/creative** (rarely used): audiocraft
- **Dev tools** (rarely used): github, vllm, lm-evaluation-harness, segment-anything
- **Feishu/China**: feishu-doc-batch-distill, macos-system-configuration

## Estimated Savings If Further Optimized

Disabling the ~15 least-used active skills would save ~300-400 chars (~75-100 tokens).

## Technical Note

`~/.hermes/skills` is a symlink to `~/script/hermes-self-opt/skills/`. All
`find` commands must use `-L` to traverse into the real directory tree.
