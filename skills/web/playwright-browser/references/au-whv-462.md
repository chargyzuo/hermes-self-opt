# Australian WHV Subclass 462 — Scraping Reference

## Target URLs

| Page | URL |
|------|-----|
| Main WHV 462 | `https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-462/first-work-holiday-462` |
| Ballot process | `https://immi.homeaffairs.gov.au/what-we-do/whm-program/latest-news/new-work-and-holiday-subclass-462-visa-pre-application-process` |
| Functional English | `https://immi.homeaffairs.gov.au/help-support/meeting-our-requirements/english-language/functional-english` |

## Access Notes

- **All URLs blocked** with curl (returns SharePoint JS shell, no content)
- **Headless Playwright blocked** — returns "Access Denied" with EdgeSuite reference ID
- **Headed Playwright succeeds** — real Chromium window on macOS passes bot detection
- Last verified: June 2026

## Page Structure

The main WHV page is a SharePoint SPA with tabbed interface:
- Overview | About this visa | Eligibility | Step by step | When you have this visa

Content is loaded dynamically — `wait_until="domcontentloaded"` + 3-5s sleep required.

Requirements are in collapsible "Details" sections (5+ per page). Each "Details" is a `<button class="btn btn-primary hidden-print">`. Clicking expands the content inline.

## China-Specific Requirements (from official site, June 2026)

- **Ballot required**: China, India, Vietnam must participate in random selection
- **Registration period 2026-2027**: June 4–25, 2026 (AEST)
- **Registration fee**: AUD 25 (non-refundable if not selected)
- **If selected**: 28 days to apply for visa
- **Visa fee**: AUD 670
- **All registrations expire**: April 30, 2027
- **Education**: Tertiary qualification OR 2 years undergraduate study (degrees, graduate certificates, diplomas accepted; Cert I-IV and Senior Secondary not accepted)
- **English**: Functional English — IELTS 4.5, PTE 24 (new format), TOEFL iBT 26 (new format) — test must be ≤ 12 months old
- **Letter of support**: NOT required for China
- **Funds**: ~AUD 5,000 + return fare
- **National ID card**: 身份证 required (both sides), must match between registration and application
- **Online/at-home English tests**: NOT accepted
