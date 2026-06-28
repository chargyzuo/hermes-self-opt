# English Learning Workflow (Obsidian + Eudic + TTS)

The user has an English learning pipeline in their Obsidian vault.
Vault path: `/Users/bytedance/Library/Mobile Documents/com~apple~CloudDocs/笔记/Obsidian Vault/`

## Vault Structure

```
English_learning/
  Study_Plan.md              # Overall plan, IELTS schedule, transition timeline
  Vocabulary.md              # Word bank (### word format, with Meaning/Example/Added)
  Monthly_Log_Template.md    # Copy per month for tracking
  Eudic_Export_Guide.md      # How to export from 欧陆词典
```

## Vocabulary Format

Each word in Vocabulary.md:
```
### word
- **Meaning**: English definition | 中文释义
- **Example**: sentence
- **Added**: YYYY-MM-DD
```

## Script Toolchain

All scripts in `~/script/`:

| Script | Purpose |
|--------|---------|
| `gen_vocab_audio.py` | Parse Vocabulary.md → generate MP3 via macOS `say` + ffmpeg → `~/Desktop/Vocab_Audio/` |
| `eudic_to_vocab.py` | Parse Eudic CSV export → append to Vocabulary.md (skip duplicates) |
| `addword.py` | Quick-add single/batch words to Vocabulary.md |

### Usage

```bash
# Generate audio from Vocabulary.md
python3 ~/script/gen_vocab_audio.py
# Output: ~/Desktop/Vocab_Audio/ → AirDrop to iPhone

# Import from Eudic CSV
python3 ~/script/eudic_to_vocab.py ~/Desktop/eudic_export.csv --dry-run  # preview
python3 ~/script/eudic_to_vocab.py ~/Desktop/eudic_export.csv             # import

# Quick-add words
python3 ~/script/addword.py ubiquitous "无处不在的"
echo "word | meaning" | python3 ~/script/addword.py --stdin  # batch
```

## Eudic Data

- Installed at `/Applications/Eudic.app`
- Account: 779260457@qq.com (user ID 12877bf3-...)
- Local word book data is encrypted (dailyWords.db in Group Containers — not readable)
- Export method: Eudic → 生词本 → File → Export → CSV (UTF-8)

## Audio Pipeline Details

- Uses macOS built-in `say` command (no API key needed)
- Default voice: Samantha (US English)
- UK English: Daniel / AU English: Karen
- ffmpeg handles concatenation and silence gaps
- Config vars in script: VOICE, RATE (wpm), PAUSE_BETWEEN, FINAL_GAP

## Notes

- The Vocabulary.md parser skips entries without an "Added" field (template placeholders)
- Section headings in Vocabulary.md should use `##` or `####`, NOT `###` (reserved for word entries)
- Run `gen_vocab_audio.py` after any vocabulary changes to refresh audio
