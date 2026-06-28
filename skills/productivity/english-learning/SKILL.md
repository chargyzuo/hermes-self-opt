---
name: english-learning
description: English/IELTS vocabulary learning pipeline — Eudic import, Obsidian word bank, batched 5-min TTS audio for iPhone commute listening, quick-add CLI.
platforms: [macos]
---

# English Learning & IELTS Preparation

Use when the user asks about English study planning, IELTS prep, vocabulary management, Eudic export, or TTS audio generation. Covers the Obsidian vault structure, vocabulary format, import scripts, and the macOS `say` + ffmpeg audio pipeline with ~5-minute batched output.

## Triggers

- User mentions English study, IELTS, TOEFL, vocabulary, word lists, or language learning
- User wants to import from 欧路词典 (Eudic), add words, generate audio, or update study plans
- User asks about TTS voice/accent selection for listening practice

## Architecture

```
欧陆词典 CSV export ──→ eudic_to_vocab.py ──┐
                                              ├──→ Vocabulary.md (Obsidian) ──→ gen_vocab_audio.py ──→ Vocab_Part_XX.mp3 ──→ iPhone
手写/手动输入 ────────→ addword.py ──────────┘

538 考点词表 ─────────→ 538keyword.md (Obsidian) ──→ gen_538_audio.py ──→ 538_Part_XX.mp3 ──→ iPhone
```

## Key Paths

| Resource | Path |
|----------|------|
| Obsidian vault | `~/Library/Mobile Documents/com~apple~CloudDocs/笔记/Obsidian Vault/` |
| Word bank (Eudic + manual) | `English_learning/Vocabulary.md` |
| 538 IELTS keywords | `English_learning/538keyword.md` |
| Study plan | `English_learning/Study_Plan.md` |
| Eudic export guide | `English_learning/Eudic_Export_Guide.md` |
| Import script | `~/script/eudic_to_vocab.py` |
| Quick add script | `~/script/addword.py` |
| Audio generator (Vocab) | `~/script/gen_vocab_audio.py` |
| Audio generator (538) | `~/script/gen_538_audio.py` |
| Audio output | `~/Desktop/Vocab_Audio/` |
| 538 audio output | `~/Desktop/Vocab_Audio/538/` |

## Workflow 1: Import from Eudic (欧陆词典)

1. Open Eudic → 生词本 → 全选 → File → Export → CSV (UTF-8)
2. Save as `~/Desktop/eudic_export.csv`
3. Dry-run first:
   ```bash
   python3 ~/script/eudic_to_vocab.py ~/Desktop/eudic_export.csv --dry-run
   ```
4. Import (auto-skips duplicates, adds dates):
   ```bash
   python3 ~/script/eudic_to_vocab.py ~/Desktop/eudic_export.csv
   ```

Eudic CSV format: `﻿#,单词,音标,解释,笔记` — has BOM prefix (`\ufeff#`), 5 columns. Script auto-detects column indices.

## Workflow 2: Add Words Manually

```bash
# Single word
python3 ~/script/addword.py ubiquitous "无处不在的"

# Batch via stdin (word | meaning per line)
python3 ~/script/addword.py --stdin
```

## Workflow 3: Generate Audio (Vocab)

```bash
# ALWAYS test with --limit first
python3 ~/script/gen_vocab_audio.py --limit=30

# Full generation (~5 min batches)
python3 ~/script/gen_vocab_audio.py
```

Output: `Vocab_Part_01.mp3`, `Vocab_Part_02.mp3`, etc. in `~/Desktop/Vocab_Audio/`. Script auto-cleans the output directory before each run.

Transfer to iPhone: AirDrop the folder → Files app → play in order.

## Workflow 4: Generate 538 Keywords Audio

The 538 keyword list (`English_learning/538keyword.md`) is a separate table-format file. Use dedicated script:

```bash
# Test first
python3 ~/script/gen_538_audio.py --limit=10

# Full generation (50 words per file by default)
python3 ~/script/gen_538_audio.py
```

Output: `538_Part_01.mp3`, etc. in `~/Desktop/Vocab_Audio/538/`. Each file = exactly `WORDS_PER_BATCH` words (default 50).

538 audio format per word: **word. chinese_meaning. synonyms.** — single multilingual voice reads everything naturally. The `538keyword.md` table columns: `# | Word | POS | Chinese | Synonyms`.

### Parsing messy 538 raw text

The original 538 keyword file from the web is a three-section messy markdown with broken table rows, grammar notes mixed in, and inconsistent formatting. To clean it:
1. Strip `|` delimiters, skip header rows (`排名`, `---`, `考点词`)
2. Skip rows starting with `*` (grammar footnotes, not words)
3. Filter to 4+ pipe-delimited fields
4. Output as clean Obsidian table: `| # | **word** | POS | Chinese | Synonyms |`
5. Expected ~376 real keywords (538 includes grammar notes)

## Audio Engine

**edge-tts (Microsoft Neural TTS) is the standard engine.** Free, requires internet during generation only. Output MP3s work offline. Install: `pip3 install edge-tts`

macOS `say` is a **fallback only** — lower quality, sounds robotic. Do not use unless edge-tts is unavailable.

### Default Voice

`en-US-AvaMultilingualNeural` — handles both English and Chinese naturally in a single TTS pass. This is critical: the user's definitions are **Chinese-only** (not English). A multilingual voice avoids the need for separate EN/CN voice calls.

Never use separate EN + CN voices per word (3 TTS calls/word). It's ~30x slower and offers no real quality benefit over a single multilingual voice. The multilingual voice switches language naturally based on content.

### Voice Options

| Voice | Languages | Best For |
|-------|-----------|----------|
| `en-US-AvaMultilingualNeural` ⭐ | EN + CN (and others) | **Default** — expressive female, reads EN + CN naturally |
| `en-US-AvaNeural` | EN only | English-only content (Chinese sounds garbled) |
| `en-GB-RyanNeural` | EN only | IELTS listening (British accent) |
| `zh-CN-XiaoxiaoNeural` | CN | Chinese-only speech (warm, news-style female) |

### gen_vocab_audio.py Config

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `VOICE` | `en-US-AvaMultilingualNeural` | edge-tts voice name |
| `RATE` | `-5%` | Speed (`+0%`=default, `-10%`=slower) |
| `TARGET_MINUTES` | `5` | ~minutes per output batch (approximate) |
| `FINAL_GAP` | `3` | Silence between words (seconds) |

### gen_538_audio.py Config

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `EN_VOICE` | `en-US-AvaMultilingualNeural` | Reads word + synonyms + CN meaning |
| `RATE` | `-5%` | Speed |
| `WORDS_PER_BATCH` | `50` | Exact word count per file (0 = time-based) |
| `FINAL_GAP` | `3` | Silence between words |

### Chinese-Only Definitions

The user wants **Chinese definitions only** in audio. `gen_vocab_audio.py` uses `extract_chinese_meaning()` which splits on ` | ` and takes the last part:
- `"present, everywhere \| 无处不在的"` → `"无处不在的"`
- `"n. 代表团"` → `"n. 代表团"` (already Chinese)

### edge-tts CLI Pitfalls

- `--rate` must use `=` syntax: `--rate=-5%` NOT `--rate -5%` (the `-` gets parsed as a separate flag)
- Voice names case-sensitive: `en-US-AvaMultilingualNeural`
- Rate is percentage-based, not wpm (unlike macOS `say`)
- edge-tts outputs MP3 directly (no AIFF→MP3 conversion needed)

## Vocabulary Format

Every word entry in `Vocabulary.md`:
```markdown
### <word>
- **Type**: noun/verb/adj/adv
- **Meaning**: English definition | 中文释义
- **Example**: sentence using the word
- **Added**: YYYY-MM-DD
```

The `Added` field is REQUIRED — the parser uses it to distinguish real entries from templates. Without `Added`, the entry is silently skipped. The `### ` prefix is reserved for word entries.

## Vocabulary.md Stats

Update the Statistics section manually:
```markdown
- **Total words**: N
- **Mastered**: N
- **Target**: 20-30 new words/week
```

## Pitfalls

- **Always `--limit` first**: Never run full audio generation without testing a small sample. The user may want to adjust voice, speed, or format before committing to a full batch.
- **Dual-voice is NOT worth it**: Generating separate EN + CN voices per word (3 edge-tts calls/word) is ~30x slower than a single multilingual voice. One `AvaMultilingualNeural` call handles both languages naturally. The user tried this and it was unacceptably slow (80 words in 70+ minutes vs 50 words in 2 minutes).
- **edge-tts `--rate` syntax**: Must use `--rate=-5%` with `=`, not `--rate -5%` (the `-` gets parsed as a separate flag). This caused silent failures where every word showed the 10.0s fallback duration.
- **Background long TTS runs**: For >30 words, run in background (`terminal(background=true, notify_on_complete=true)`) since edge-tts is network-dependent and a single word takes 2-3 seconds.
- **Eudic CSV BOM**: The CSV starts with `\ufeff#`, not `#`. The import script handles this.
- **Short vs long definitions**: Eudic exports have brief Chinese definitions (~1-2s audio). Manually entered words with English | Chinese format have the English part stripped by `extract_chinese_meaning()` before TTS. Result: ~40 words per 5-minute batch.
- **Chinese words in Eudic entries**: Eudic CN→EN study mode may produce entries where the "word" itself is Chinese (e.g., "韧性"). Multilingual voice reads these fine, but the user may want to filter them.
- **`###` heading collision**: The `### ` prefix is reserved for word entries in Vocabulary.md. Use `##` or `####` for section titles. `###` headings without an `Added` field are parsed as word entries.
- **Audio output is wiped each run**: Scripts clear the output directory before generating. Don't store unrelated files there.
- **ffmpeg required**: `brew install ffmpeg` (provides both ffmpeg and ffprobe).
- **538 keyword count**: The name says "538" but the clean parsed list has ~376 real keywords. The rest are grammar notes (that*, and*, rather than*, thanks to*) that get filtered out.

## Language Transition

When the user has an active transition plan (Chinese → mixed → English), respect the current phase per `Study_Plan.md`. Default: Week 1 = Chinese with key English terms.
