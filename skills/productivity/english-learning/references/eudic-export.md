# Eudic (欧路词典) Export Details

## CSV Format

Eudic exports CSV in UTF-8 with BOM:

```
﻿#,单词,音标,解释,笔记
1,"delegation","英:/ˌdelɪ'ɡeɪʃn/ 美:/ˌdelɪ'ɡeɪʃn/","n. 代表团",
2,"severity","英:/sɪ'verəti/ 美:/sɪ'verəti/","- n. 严格, 严厉, 苛刻",
```

| Column | Content | Notes |
|--------|---------|-------|
| `﻿#` | Row number | BOM prefix `\ufeff` before `#` |
| `单词` | Word | May be quoted if contains commas |
| `音标` | Phonetic (UK/US) | Often empty |
| `解释` | Definition | May have leading `- ` or prefix like `n. ` |
| `笔记` | User notes | Often empty |

## Export Steps (macOS Eudic)

1. Open 欧路词典
2. Menu → 生词本 (or快捷键)
3. Select words (Cmd+A for all)
4. File → 导出 (Export)
5. Choose **CSV (UTF-8)**
6. Save to Desktop

## Account Info (for reference)

- Login: `779260457@qq.com`
- Nickname: `Z哲蛰`
- Auth token available in `~/Library/Preferences/com.eusoft.eudic.plist` under `AUTH_AccessToken`
- Word book is stored encrypted locally (`dailyWords.db` in Group Containers — not directly readable)

## Definition Quality

Eudic definitions are typically brief Chinese glosses:

| Word | Eudic Definition | Audio Duration |
|------|-----------------|----------------|
| delegation | n. 代表团 | ~0.9s |
| severity | - n. 严格, 严厉, 苛刻 | ~1.2s |
| instruct | vt. 命令；教授；指导；通知 | ~1.1s |

vs manually entered English definitions:

| Word | Manual Definition | Audio Duration |
|------|------------------|----------------|
| ubiquitous | present, appearing, or found everywhere \| 无处不在的 | ~3.2s |
| exacerbate | make a problem worse \| 加剧，恶化 | ~4.5s |

This 3-4x duration difference affects batch sizes at the 5-minute target.
