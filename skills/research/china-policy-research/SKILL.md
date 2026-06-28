---
name: china-policy-research
description: Research Chinese government policies, administrative regulations, and official documents. Use when the user asks about any Chinese government policy, regulation, housing/hukou/tax/social-security rules, or local administrative measures. Covers navigating .gov.cn portals, finding official documents, and interpreting Chinese administrative announcements.
---

# Chinese Government Policy Research

## When to Use
- User asks about any Chinese government policy, regulation, or administrative measure
- User needs to find official documents from Chinese government websites (.gov.cn)
- User asks about housing provident fund (公积金), social insurance (社保), hukou (户口), tax policies, or any local/provincial regulation
- User wants to verify current policy status or eligibility for government programs

### Alternative: National Laws Database (国家法律法规数据库)

For **national-level legislation** (法律/法规 by 全国人大 or 国务院), bypass .gov.cn and go directly to:

- **Portal**: `https://flk.npc.gov.cn/` — the official 国家法律法规数据库 run by 全国人大常委会
- This database covers: 宪法, 法律, 行政法规, 监察法规, 地方法规, 司法解释
- **Search by title**: type the law name (e.g. "中华人民共和国劳动法") in the search box, select 模糊 search
- **Download**: results include a download button for PDF and a detail view with the full text
- **Limitations**: the site is JS-heavy and uses dynamic detail URLs (`detail2.html?<base64>`). Navigation via `browser_navigate` often redirects to the homepage due to SPA routing. Use `browser_type` + `browser_click` to fill the search form and click the search button, then click a result to see its preview. For reliable text extraction, scrape the visible text from the result list's expanded preview (the "命中展示" / "相关资料" sections).

### Key law URLs (known stable IDs for common laws):
- 劳动法 (2018修正, 有效): `flk.npc.gov.cn` search → "中华人民共和国劳动法" (2018-12-29 version, 有效)
- For other laws, always search by full title on flk.npc.gov.cn

### Step 1: Identify the responsible government body
Chinese policies are published by specific agencies. For housing provident fund questions, it's the city-level 住房公积金管理中心. For other topics, determine which level (national, provincial, city) and which agency.

### Step 2: Go directly to the government portal
DO NOT start with general search engines. Chinese government websites follow predictable patterns:
- City government: `https://www.<city-pinyin>.gov.cn` (e.g., baoshan.gov.cn)
- Provincial government: `https://www.<province>.gov.cn`
- Specialized subdomains may not resolve in all environments — use the main portal instead

### Step 3: Use the on-site search
Every .gov.cn portal has a search box. Use it with Chinese keywords relevant to the policy. The on-site search indexes all official documents, policy interpretations, and announcements across departments.

### Step 4: Look for these document types
Chinese government sites organize policy content into categories:
- **规范性文件** (normative documents) — the actual regulation text
- **政策解读** (policy interpretation) — plain-language explanations, often more accessible
- **文字解读** (text interpretation) — detailed line-by-line analysis
- **通知公告** (notices and announcements) — recent updates or changes
- **在线访谈** (online interviews) — Q&A with officials, good for current status

### Step 5: Check the dynamic/conditional clauses
Many Chinese policies have conditional triggers (e.g., "this program operates when X < 75% and suspends when X ≥ 85%"). Always read the full document to identify these — they determine whether the policy is actually in effect.

### Step 6: Verify currency
- Check the effective date and expiration date (施行日期 / 有效期)
- Look for any subsequent amendments or suspension notices
- If in doubt, recommend the user call the agency directly

## Pitfalls

### General search engines are unreliable for Chinese policy
- Baidu: requires CAPTCHA verification, blocks automated access
- Google: frequently blocked or returns network errors
- Bing (Chinese edition): notoriously returns irrelevant results for policy queries (entertainment content, unrelated pages)
- Strategy: bypass search engines entirely — navigate directly to the government portal

### Government subdomains may not resolve
Subdomains like `gjj.baoshan.gov.cn` or `zfgjj.baoshan.gov.cn` often fail DNS resolution in non-Chinese network environments. The main `www.<city>.gov.cn` domain is more reliable and contains cross-department search.

### Policy interpretation is often more useful than the regulation itself
The 政策解读 (policy interpretation) document typically includes:
- Concrete examples with numbers
- Eligibility checklists
- Procedural steps
- The rationale behind rules

Read the interpretation first, then consult the regulation text for precise legal language.

### Dynamic management mechanisms are common
Many Chinese local policies (especially housing-related) use "dynamic management" (动态管理): the program activates or suspends based on metrics like fund balance ratios. Always flag this to the user and recommend calling the agency to confirm current status.

## Key Terms Glossary
| Chinese | English |
|---------|---------|
| 商转公 | Commercial-to-Provident Fund Loan Conversion |
| 公积金 | Housing Provident Fund |
| 双边缴存 | Bilateral contribution (employer + employee) |
| 贷款直转 | Direct loan transfer (no bridge financing needed) |
| 先还后转 | Pay-off-first-then-convert |
| 组合贷款 | Combined loan (provident fund + commercial) |
| 不动产权证书 | Real Estate Title Certificate |
| 顺位抵押 | Subordinated mortgage registration |
| 贷款率 | Loan-to-deposit ratio |
| 动态管理 | Dynamic management (conditional activation) |

## References
- `references/baoshan-shang-zhuang-gong-2023.md` — Full policy analysis for Baoshan City's commercial-to-provident-fund conversion (2023-2026)
- `references/overtime-pay-law-劳动法.md` — 中国加班工资法律规定: 劳动法第44条、第41条、第42条, 法定节假日列表, 计算基数规则
- `references/gaokao-score-image-extraction.md` — OCR workflow for extracting gaokao score lines and distribution tables from Chinese government PNG images (招生考试院 published as images, not HTML). Covers tesseract preprocessing, common pitfalls, psm values, and fallback strategies.

## Related Skills
- `ocr-and-documents` — PDF/scanned document extraction (pymupdf/marker-pdf); complements this skill for non-PNG government documents
- `playwright-browser` — headed browser approach when government sites block automated access
