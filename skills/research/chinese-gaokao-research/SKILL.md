---
name: chinese-gaokao-research
description: "Research Chinese gaokao score lines, score distributions, and make university recommendations."
version: 1.0.0
author: Hermes Agent
tags: [gaokao, china, education, admissions, yunnan]
category: research
platforms: [macos, linux]
---

# Chinese Gaokao Research Skill

## When to use

Use when the user asks about gaokao (高考) results — score lines, 一分一段 (one-score-per-segment) distribution tables, whether a score can get into 本科/专科, university recommendations for a given score and province. Applies to any province in China during 高考 season (June-July each year).

## Data Sources

| Source | URL | Notes |
|--------|-----|-------|
| 教育部阳光高考 | gaokao.chsi.com.cn | Official 一分一段 tables, links by province |
| 各省招考院 | e.g. ynzs.cn (云南) | Official score lines (as PNG images) |
| 掌上高考 | gaokao.cn | University search + score matching (JS-heavy) |
| 学信网 | chsi.com.cn | Education authority gateway |

## Key Sites and Their Access Patterns

### 教育部阳光高考 (gaokao.chsi.com.cn)
- Best aggregator — has 一分一段 links for most provinces
- `browser_navigate` works for the index page
- Each province's data is a link in the table — click through
- Content is server-rendered, no JS issues

### 云南省招考频道 (ynzs.cn)
- Official score lines are published as **PNG images** (not text)
- Example: https://www.ynzs.cn/upload/images/2026/6/e607aff838744f67.png
- Direct page access may redirect to 温馨提示 — download the image URL directly
- Also publishes 一分一段 as a large tall PNG (900x8000+ pixels)

## Workflow

### 1. Find score lines (批次线)

```
省份 + 2026年普通高校招生录取最低控制分数线
```

Start with 教育部阳光高考 page (gaokao.chsi.com.cn). Navigate via browser to the province-specific 分数线 page, or search for the province's 招考院 official announcement.

If the page is blocked or shows 温馨提示 → download the image directly (the PNG inside the page content).

### 2. OCR government score table images

Score table images (分数线 and 一分一段) are published as PNG with Chinese text. Use aggressive preprocessing:

```bash
python3 << 'PYEOF'
from PIL import Image, ImageEnhance, ImageFilter

img = Image.open('/tmp/table.png').convert('L')

# Strong contrast enhancement (score tables often have thin text on white bg)
img = ImageEnhance.Contrast(img).enhance(3.0)

# Sharpen
img = img.filter(ImageFilter.SHARPEN)

# Binarize — score line text is usually dark
img = img.point(lambda x: 0 if x < 100 else 255)

# Upscale 2-3x for better OCR
img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)

img.save('/tmp/enhanced.png')
PYEOF

tesseract /tmp/enhanced.png stdout -l chi_sim --psm 6
```

**PSM values to try**: 6 (block), 3 (default), 4 (column), 11 (sparse text), 12 (sparse text with OSD). PSM 6 usually works best for tabular data.

**For tall 一分一段 tables** (900x8000+ px):
- Split into vertical chunks of ~1000px each
- OCR each chunk independently
- Each half contains: 分数段 | 本段人数 | 累计人数
- Look for the target score (e.g. 440) in the left column
- The two columns are: left half = 历史类(文科), right half = 物理类(理科)

### 3. Fallback when Bing/Baidu blocked

Bing CN (国内版) aggressively filters gaokao-related results. Baidu requires CAPTCHA. Use:
- Direct province 招考院 websites (know the URL pattern)
- 教育部阳光高考 (chsi.com.cn) as the aggregator
- `browser_navigate` with headed Playwright (`headless=False`) + user interaction at `ynzs.cn`

### 4. Score data via browser tools (gaokao.cn/招考院)

**掌上高考 (gaokao.cn)**: The API endpoint at `api-gaokao.zjzw.cn` uses timestamp-based signature validation (`signsafe` param). Direct curl calls return 404. Use browser tools to view the rendered results; the Vue/React app loads data but the page is JS-heavy and login overlays may block automated access. Headed Playwright mode is the most reliable path.

**省招考院 PNG images**: Score line and 一分一段 images can be downloaded directly if you know the image URL (extracted from page HTML or DevTools network tab). The surrounding HTML page may show 温馨提示 but the image resource itself is accessible.

### 4. University recommendations

Match score against province score lines:

| Score vs 本科线 | Recommendation |
|----------------|---------------|
| Above 本科线 by 10+ | Can try provincial 二本/民办本科 |
| At 本科线 ±5 | 专科保底，冲本科 |
| Well below 本科线 | Focus on 专科 (高职) |

For **出省专科推荐** with scores at/below 本科线:
- 440 points in Yunnan 理科 (本科线 ~435) is strong for 专科
- Target 沿海 + 大城市: Shenzhen, Guangzhou, Hangzhou, Ningbo, Suzhou, Xiamen
- Good 专科 choices at this range: 深圳职业技术大学, 广东交通职业技术学院, 浙江交通职业技术学院, etc.
- English major (商务英语/旅游英语) is viable at 沿海专科 but less competitive than 工科/计算机/护理

### 6. Reference: 《英语面经群聊精选》 Notion page

The user's Notion page (https://sweet-paneer-eff.notion.site/d9c7b10d49ed4533bc6420ed41f2c0d6) contains a curated database of network engineer interview experience. Under section **"8-资源信息"**, it links to:

| Resource | URL | Topic |
|----------|-----|-------|
| DegreeForum (学历加速) | https://www.degreeforum.net/mybb/ | US degree acceleration via CLEP/DSST/Sophia/Study.com credits → WGU/TESU/UMPI |
| BIRD Internet Routing Daemon | https://en.wikipedia.org/wiki/BIRD_Internet_Routing_Daemon | Routing protocol implementation |
| Tech Vault interview Q&A | https://github.com/moabukar/tech-vault | DevOps/Linux/networking interview questions, CLI-compatible |
| Quark 网盘 (群精华文档) | https://pan.quark.cn/s/7f9d0d9d5630 (code: Type) | Full reader group archive — 《网络工程师的英语面经》精华文档 |

This page is Notion's database view — links are embedded in database entries, not directly in the page HTML. Only `browser_console` with `document.body.innerText` can extract the full text content; Notion's JS-rendered DOM doesn't expose all links in the accessibility tree.

## Key terminology translation

| Chinese | English equivalent |
|---------|-------------------|
| 理科/物理类 | Science/Physics track |
| 文科/历史类 | Arts/History track |
| 本科线 | Bachelor's admission threshold |
| 专科线 | Diploma admission threshold |
| 一分一段 | One-score-per-segment distribution table |
| 双高计划 | National top-tier vocational college program |
| 征集志愿 | Supplementary application round (after regular录取) |

## Pitfalls

- **Score line images are NOT OCR-friendly**: government PNGs have thin strokes and small fonts. Always enhance contrast and upscale before OCR. Multiple OCR passes with different PSM values may be needed.
- **Bing CN blocks gaokao searches**: Use the international version (cc=us) or skip Bing entirely — go directly to 阳光高考 or 省招考院.
- **ynzs.cn direct page access**: The content page redirects to 温馨提示 if accessed directly. Download the image URL found in the page HTML instead.
- **一分一段 has TWO columns**: The image is split left=历史类/文科, right=物理类/理科. Don't mix them up.
- **Tesseract Chinese OCR quality**: Score tables often have OCR errors for numbers (6→8, 0→O, etc.). Cross-validate by looking at the pattern (累计人数 should be monotonically decreasing).
- **Tesseract fails on certain PNGs**: Some PNG files cause Leptonica errors (`Error in fopenReadStream`). Workaround: convert to JPEG first with PIL (`img.convert('RGB').save('/tmp/file.jpg')`), then OCR the JPEG.
- **Notion page content extraction**: Notion's database view renders entries as interactive components, not plain text. Links inside database entries are NOT exposed in the accessibility tree. Use `browser_console` with `document.body.innerText` to extract full page text, then search for keywords. Individual entries can be expanded by clicking, but entry titles in the database view are truncated — the `innerText` gives the full text.
- **gaokao.cn school list is ranked by 录取概率 not score**: The search page shows all schools by default ranked by admission probability (清华北大 first), NOT filtered by the entered score. The score filter is applied through JS API calls with signature that can't be replicated via curl. Use headed Playwright to interact with the page.
- **Notion.sites from 面经**: The 《英语面经群聊精选》 Notion page contains external resource links under the "8-资源信息" section, including degreeforum.net for 加速学历.
