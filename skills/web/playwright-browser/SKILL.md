---
name: playwright-browser
description: |
  Use Playwright (Python) to browse websites that block built-in browser tools,
  curl, or headless browsers with aggressive bot detection. Also covers
  expanding dynamic/collapsed content, extracting text from JS-rendered pages,
  and OCR-ing user screenshots with tesseract.
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [web, scraping, playwright, bot-detection, ocr]
    category: web
---

# Playwright Browser for Bot-Detected Sites

## When to use this skill

Use Playwright when:

- `browser_navigate` returns "Access Denied" or a bot-detection page
- `curl` / `terminal` fetching returns JavaScript placeholders instead of content
- The site uses aggressive bot detection (Cloudflare, Imperva, Akamai, custom)
- The site loads critical content dynamically via JS (SPA, collapsible sections)
- The user already has Playwright installed and prefers it

Do NOT use this when:
- `browser_navigate` works fine — it's simpler and faster
- The endpoint is plain-text (`.md`, `.txt`, `.json`) — use `curl` or `web_extract`
- You just need a single API call — Playwright overhead isn't worth it

## Prerequisites

```bash
pip install playwright
playwright install chromium
```

Verify with:
```bash
playwright --version
```

## Core pattern: headed mode for bot sites

**Always use `headless=False` first** — many bot-detection systems check for headless mode and block it. If headed works, only then try headless for speed on subsequent pages from the same session.

### Minimal viable script

```python
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # VISIBLE browser
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    page.goto("https://target-site.com", timeout=30000, wait_until="domcontentloaded")
    time.sleep(3)

    print(f"Title: {page.title()}")
    text = page.evaluate("document.body.innerText")
    print(text[:5000])

    browser.close()
```

### User interaction during headed mode

When the user says "需要扫码/登录我来就行" (or similar), the headed browser window opens on their desktop. They can interact with it — log in, scan QR codes, dismiss popups — while the script waits. Use `time.sleep(N)` to give them time.

## SSO → API via Cookie Extraction

When a site uses SSO (OIDC/OAuth) and you have a Playwright `storage_state` JSON from a prior login, use the browser context to authenticate, then extract the session cookie for curl API calls:

```python
from playwright.sync_api import sync_playwright
import time, json

state_file = "/path/to/sso_state.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state=state_file)
    page = context.new_page()

    page.goto("https://target.internal.site/", timeout=30000, wait_until="domcontentloaded")
    time.sleep(3)

    # If still on /login/, look for SSO button
    if "/login/" in page.url:
        for sel in ["a[href*='sso']", "a:has-text('SSO')", "a:has-text('飞书')"]:
            el = page.query_selector(sel)
            if el:
                el.click()
                time.sleep(5)
                break

    # Extract cookies for curl
    cookies = context.cookies()
    cookie_str = "; ".join(
        f"{c['name']}={c['value']}"
        for c in cookies if "target" in c.get("domain", "")
    )
    with open("/tmp/target_cookies.txt", "w") as f:
        f.write(cookie_str)

    # Alternative: call API directly from browser context (no curl needed)
    resp = page.evaluate("""
        async () => {
            const r = await fetch('/api/endpoint/?limit=1');
            return { status: r.status, body: await r.json() };
        }
    """)
    print(json.dumps(resp, indent=2))

    browser.close()
```

**curl usage with extracted cookie:**
```bash
curl -sS -b "$(cat /tmp/target_cookies.txt)" "https://target.internal.site/api/endpoint/"
```

## Saving Output

Always save extracted text to a file — terminal output gets truncated:
```python
import os
os.makedirs("/tmp/output", exist_ok=True)
with open("/tmp/output/page.txt", 'w') as f:
    f.write(text)
```

Screenshots help verify what was captured:
```python
page.screenshot(path="/tmp/output/page.png", full_page=True)
```

## Wait Strategy

- Use `wait_until="domcontentloaded"` for JS-heavy sites (SharePoint, SPA) — `"load"` can hang indefinitely
- After navigation, `time.sleep(3–5)` to let dynamic content render
- After clicking elements that trigger DOM changes, `time.sleep(1–3)`

## Expanding dynamic/collapsed content

Many government and documentation sites use expandable "Details" sections that load content via JS only when clicked.

### Pattern: find and click all Details buttons

```python
# Works for <button>Details</button>, <a>Details</a>, <span>Details</span>
page.evaluate("""() => {
    let count = 0;
    for (const el of document.querySelectorAll('button, a, span')) {
        if (el.textContent.trim() === 'Details') {
            try { el.click(); count++; } catch(e) {}
        }
    }
    return count;
}""")
time.sleep(2)  # Wait for content to load
```

### Pattern: click by visible text (Playwright selectors)

```python
# Click tab/accordion
page.click("a:has-text('Eligibility')")
# Click a specific link
page.click("text=Create ImmiAccount")
```

Note: `:has-text()` is a Playwright-specific pseudo-selector — do NOT use it inside `page.evaluate()` JavaScript (which only accepts standard CSS).

## Extracting text from JS-rendered pages

```python
# Full page text
text = page.evaluate("document.body.innerText")

# Main content only (if <main> exists)
text = page.evaluate("""() => {
    const main = document.querySelector('main');
    return (main || document.body).innerText;
}""")
```

## Finding links in the page

```python
for link in page.query_selector_all("a"):
    href = link.get_attribute('href') or ''
    txt = link.inner_text().strip()
    if 'keyword' in txt.lower():
        print(f"'{txt}' -> {href}")
```

## OCR for Chinese government table PNGs (分数线/一分一段)

Many Chinese government sites (省招考院, 公示平台) publish tabular data as PNG images with Chinese text — specifically gaokao 分数线 and 一分一段 tables. These need aggressive preprocessing:

```python
from PIL import Image, ImageEnhance, ImageFilter

img = Image.open('/tmp/gov_table.png').convert('L')

# Strong contrast — gov tables have thin dark text on light backgrounds
img = ImageEnhance.Contrast(img).enhance(3.0)

# Sharpen twice
img = img.filter(ImageFilter.SHARPEN)
img = img.filter(ImageFilter.SHARPEN)

# Binarize
img = img.point(lambda x: 0 if x < 100 else 255)

# Upscale 2-3x
img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)

img.save('/tmp/gov_table_enhanced.png')
```

Then OCR with:
```bash
tesseract /tmp/gov_table_enhanced.png stdout -l chi_sim --psm 6
```

Try PSM values 3, 4, 6, 11, 12 — PSM 6 (treat as uniform block) usually works best for tabular data.

**For tall tables** (> 5000px high, common for 一分一段):
- Split into vertical chunks of 1000-1200px each
- OCR each chunk separately
- Parse the structured columns: 分数段 | 本段人数 | 累计人数

Common pitfalls with gov table OCR: numbers get confused (6↔8, 0↔O, 4↔9), column headers may not survive, and the table often has TWO data columns side by side (left=文科/历史类, right=理科/物理类).

## OCR for user screenshots (tesseract)

When the user shares a screenshot and you don't have vision tools:

```bash
# Check if tesseract is installed
which tesseract

# OCR with English + Chinese (simplified) support
tesseract /path/to/screenshot.jpeg /tmp/output -l eng+chi_sim
cat /tmp/output.txt
```

Common languages:
- `eng` — English
- `chi_sim` — Simplified Chinese
- `chi_sim+eng` — Both (Chinese pages with English mixed in)
- `jpn` — Japanese

## Pitfalls

- **Headless mode blocked**: Switch to `headless=False`. Many sites (especially `.gov.au`) detect headless Chrome.
- **`wait_until="load"` times out**: Try `wait_until="domcontentloaded"` — some SPAs never fire the full "load" event.
- **`:has-text()` in `evaluate()`**: This Playwright selector does NOT work in JavaScript. Use `document.querySelectorAll` + `textContent.trim()` instead.
- **Page content not in initial HTML**: Many modern sites load content via XHR/fetch AFTER the DOM is ready. Add `time.sleep(3-5)` after `goto()`. If content is still missing, the site likely uses React/Vue/Angular and needs specific interaction (scroll, click tabs) to trigger loading.
- **Script times out**: Headed mode scripts can hang if a modal or dialog appears. Add a `signal.alarm(N)` hard timeout guard. Keep scripts under 80 lines — long headed-mode scripts with user-wait periods are fragile.
- **Button text is "Show steps" not "Details"**: Different sites use different labels. Always inspect the page first, then adapt the click pattern.

## Verification

After scraping, verify:
1. `page.title()` is not "Access Denied"
2. `page.evaluate("document.body.innerText")` contains real content, not just nav/footer boilerplate
3. The key sections you need are present in the extracted text
