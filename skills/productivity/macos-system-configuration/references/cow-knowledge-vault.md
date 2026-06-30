# Cow Knowledge Vault Overview

The user's Obsidian-style knowledge base lives at `/Users/bytedance/cow/knowledge/`. It contains structured troubleshooting docs, config templates, and case studies in Markdown.

## Structure

```
/Users/bytedance/cow/knowledge/
├── index.md                   # Root index (register)
├── log.md                     # Change log
├── config/                    # Config templates (per device/vendor)
├── Cases/                     # Specific troubleshooting cases
├── ...                        # Other categorized docs
```

## Content (Network-relevant)

| File | Topic |
|------|-------|
| `config/arista-dot1x-config.md` | Arista EOS dot1x global + port config, address locking setup |
| `Cases/arista-8021x-accounting-ip.md` | Arista 802.1X accounting missing client IP — root cause, fix (address locking) |
| `Cases/arista-address-locking.md` | Deep dive: Address Locking permit list, DHCP Leasequery mechanics, DORA death spiral |

## Usage

When asked about a specific vendor/feature that the user's skills don't cover, check `/Users/bytedance/cow/knowledge/` for relevant docs before reaching elsewhere. The vault is the user's curated, hand-maintained source of truth.
