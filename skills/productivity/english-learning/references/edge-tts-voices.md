# edge-tts Voice Reference

Full list of natural-sounding English voices from Microsoft Edge TTS.
Run `edge-tts --list-voices` for the complete, up-to-date list.

## ⭐ Default Choice

`en-US-AvaMultilingualNeural` — handles **both English and Chinese** naturally in a single TTS pass. This is the primary voice because the user's vocabulary has Chinese definitions. One call reads `"word. chinese_meaning. synonyms."` with natural language switching.

## Multilingual Voices (EN + CN + others)

| Voice | Gender | Style | Notes |
|-------|--------|-------|-------|
| `en-US-AvaMultilingualNeural` ⭐ | Female | Expressive, caring | **Default** — reads EN + CN naturally |
| `en-US-AndrewMultilingualNeural` | Male | Warm, confident | EN + CN |
| `en-US-BrianMultilingualNeural` | Male | Approachable | EN + CN |
| `en-US-EmmaMultilingualNeural` | Female | Cheerful | EN + CN |
| `en-AU-WilliamMultilingualNeural` | Male | Friendly | EN + CN, AU accent |

> **Why multilingual matters**: Using separate EN voice for words + CN voice for meanings = 3 TTS calls/word → unacceptably slow. One multilingual call handles everything naturally.

## Chinese Voices (zh-CN)

| Voice | Gender | Style | Notes |
|-------|--------|-------|-------|
| `zh-CN-XiaoxiaoNeural` | Female | Warm, news-style | Best Chinese female voice |
| `zh-CN-YunyangNeural` | Male | Professional, reliable | Best Chinese male voice |
| `zh-CN-XiaoyiNeural` | Female | Lively, cartoon | |
| `zh-CN-YunxiNeural` | Male | Lively, sunshine | |
| `zh-CN-YunjianNeural` | Male | Passionate | Sports style |

> Chinese-only voices are NOT needed in normal workflow. They're listed here only if the user explicitly asks for a CN-specific voice for definition audio (which multiplies TTS calls and should be avoided).

## US English (en-US)

| Voice | Gender | Style | Notes |
|-------|--------|-------|-------|
| `en-US-AvaNeural` | Female | Expressive, caring, pleasant | **Best overall quality** |
| `en-US-AndrewNeural` | Male | Warm, confident, authentic | Good for narration |
| `en-US-JennyNeural` | Female | Friendly, considerate | Natural conversational |
| `en-US-AriaNeural` | Female | Positive, confident | News/novel style |
| `en-US-EmmaNeural` | Female | Cheerful, clear | Conversational |
| `en-US-BrianNeural` | Male | Approachable, casual | |
| `en-US-ChristopherNeural` | Male | Reliable, authority | |
| `en-US-EricNeural` | Male | Rational | |
| `en-US-GuyNeural` | Male | Passionate | |
| `en-US-MichelleNeural` | Female | Friendly, pleasant | |
| `en-US-RogerNeural` | Male | Lively | |
| `en-US-SteffanNeural` | Male | Rational | |
| `en-US-AnaNeural` | Female | Cute, cartoon | Not for study |

## UK English (en-GB) — best for IELTS

| Voice | Gender | Style | Notes |
|-------|--------|-------|-------|
| `en-GB-RyanNeural` | Male | Friendly, positive | **Top pick for IELTS** |
| `en-GB-SoniaNeural` | Female | Friendly, positive | Warm tone |
| `en-GB-ThomasNeural` | Male | Friendly, positive | Stable, clear |
| `en-GB-LibbyNeural` | Female | Friendly, positive | |
| `en-GB-MaisieNeural` | Female | Friendly, positive | |

## Australian English (en-AU)

| Voice | Gender | Style | Notes |
|-------|--------|-------|-------|
| `en-AU-NatashaNeural` | Female | Friendly, positive | Main AU option |
| `en-AU-WilliamMultilingualNeural` | Male | Friendly, positive | |

## macOS `say` Fallback Voices

When offline or edge-tts unavailable, macOS built-in voices ranked by naturalness:

| Voice | Accent | Quality |
|-------|--------|---------|
| `Shelley (English (US))` | US | ★★★★ Neural |
| `Eddy (English (US))` | US | ★★★★ Neural |
| `Eddy (English (UK))` | UK | ★★★★ Neural |
| `Flo (English (US))` | US | ★★★☆ Neural |
| `Flo (English (UK))` | UK | ★★★☆ Neural |
| `Karen` | AU | ★★★ |
| `Samantha` | US | ★★☆ Legacy, robotic |
| `Daniel` | UK | ★★☆ Legacy |
