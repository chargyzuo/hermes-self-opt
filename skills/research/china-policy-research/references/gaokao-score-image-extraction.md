# Gaokao Score Image Extraction

Many Chinese provincial education bureaus (招考院) publish **gaokao admission score lines** and **one-section distribution tables** (一分一段表) as static PNG/JPEG images rather than HTML tables. This reference covers how to extract them.

## Common Sources

| Source | URL Pattern | Authentication |
|--------|-------------|----------------|
| 教育部阳光高考 (chsi) | `gaokao.chsi.com.cn/gkxx/ss/...` | None (accessible) |
| 云南省招考频道 | `www.ynzs.cn/html/.../content_....html` | Blocks direct access (returns 温馨提示/404 for some URLs) |
| 各省招考院 | `www.<province>.zsksy.cn` or `www.<province>.gov.cn` | Varies |

## The Image Problem

Government gaokao images have specific characteristics that make OCR difficult:

- **Score line image**: ~2000×700 px, RGB, tabular layout with Chinese headers (类别, 文史类/历史类, 理工类/物理类, 本科, 专科, 艺术类, 体育类)
- **Distribution table**: ~900×8500 px (very tall), two-column layout (left=历史类, right=物理类), each column has 分数段 | 本段人数 | 累计人数
- **Common quality issues**: low contrast, thin fonts, light gray text on white background, anti-aliased text

## Extraction Approaches

### 1. Direct OCR (image already downloaded)

```bash
# Install dependencies
pip install Pillow
brew install tesseract  # macOS
tesseract --list-langs  # Check if chi_sim is installed

# For score line images (~2000px wide) — preprocess aggressively:
python3 << 'PYEOF'
from PIL import Image, ImageEnhance, ImageFilter
img = Image.open('/path/to/image.png').convert('L')
enh = ImageEnhance.Contrast(img).enhance(3.0)  # Strong contrast
sharp = enh.filter(ImageFilter.SHARPEN)
big = sharp.resize((sharp.width*2, sharp.height*2), Image.LANCZOS)
bw = big.point(lambda x: 0 if x < 100 else 255)  # Binarize
bw.save('/tmp/processed.png')
PYEOF

tesseract /tmp/processed.png stdout -l chi_sim --psm 6
```

### 2. Browser + human verification (Playwright headed)

```python
from playwright.sync_api import sync_playwright
import time
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto("URL", timeout=30000, wait_until="domcontentloaded")
    time.sleep(3)
    # Let the user see the image directly
    page.screenshot(path="/tmp/page.png")
    # User can visually verify
```

### 3. Direct download + user visual verification

```bash
cp /tmp/image.png ~/Desktop/gaokao_scores.png
echo "Image saved to Desktop — user can see it"
```

### 4. Web-based tools (for users)

When all automated approaches fail, tell the user to visit a tool like:
- The **Yunnan Zhaokao Channel image URL** directly in their browser
- Or upload to an online OCR tool

## OCR Pitfalls on Government Images

| Issue | Symptom | Fix |
|-------|---------|-----|
| tesseract PNG read failure | `Error in fopenReadStream` | Convert to JPEG (`img.convert('RGB').save('file.jpg')`) |
| Empty OCR output | No text detected after processing | Reduce binarization threshold (`x < 80` instead of `x < 100`) |
| Garbled numbers | `3` → `8`, `4` → `4中`, `0` → `o` | Increase scale factor (3x-4x), enhance contrast |
| Chinese chars missing | Text but no CJK characters | Verify `chi_sim` lang pack installed (`tesseract --list-langs`) |
| Only headers detected | "本段人数" visible but data rows blank | Crop image to data region only, avoid header noise |
| Two-column table confusion | Columns merged into one | Split image vertically, OCR each half separately |
| tesseract writes 0-byte output | File exists but empty | Try different `--psm` value (3, 4, 6, 11, 12) |

## Best psm Values for Tabular Gaokao Data

| Image type | Recommended psm | Notes |
|------------|----------------|-------|
| Score line (simple table) | `--psm 6` | Uniform block of text |
| Score line (with merged cells) | `--psm 3` | Fully automatic page segmentation |
| Distribution table (dense) | `--psm 6` | Single text block |
| Any image with poor results | `--psm 4` | Assume single column of text |

## Known Score Line Layout (confirmed for Yunnan 2026)

Official Yunnan 2026 format — a table with these rows/columns:

```
类别               文科(历史类)    理科(物理类)
本科               [465]          [435]
专科               180            180
特殊类型录取资格线   ~345           ~325
艺术类本科          ~380           ~365
体育类本科          ~380           ~365
```

Note: The "历史类/物理类" naming is used in Yunnan and other provinces transitioning to the new gaokao format. Older provinces may still use "文史类/理工类".

## Workflow Summary

1. **First attempt**: `browser_navigate` to the official source — many work in headed mode
2. **Image found**: Download via `curl` or extract the `src` from the gallery
3. **OCR**: Preprocess (grayscale → contrast 3x → scale 2x → binarize threshold 100) + tesseract with `--psm 6 -l chi_sim`
4. **Verify**: Compare multiple OCR runs for consistency
5. **Fallback**: Save to Desktop and ask the user to visually verify
6. **Last resort**: Point the user to the image URL directly
