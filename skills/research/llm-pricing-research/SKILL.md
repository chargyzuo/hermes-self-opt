---
name: llm-pricing-research
description: "Compare LLM API token pricing across providers — official sites, Chinese cloud platforms (Alibaba Bailian, etc.), and resellers."
version: 1.0.0
author: Hermes Agent
platforms: [linux, macos, windows]
metadata:
  hermes:
    triggers:
      - User asks to compare model/provider pricing
      - deepseek/qwen/glm pricing or token cost comparison
      - Checking if a reseller markup is worth it
      - 价格对比 / token价格 / 模型价格
---

# LLM API Pricing Research

Compare token pricing for LLM APIs across official providers, Chinese cloud platforms (阿里云百炼, etc.), and resellers. Present results as clean comparison tables.

## Provider Pricing Pages

### Official Provider Pages

| Provider | Pricing URL | Extraction |
|----------|------------|------------|
| DeepSeek | `https://api-docs.deepseek.com/quick_start/pricing` | Clean HTML table — `browser_navigate` then `browser_snapshot` works directly |
| OpenAI | `https://openai.com/api/pricing/` | Standard page, browser tools OK |
| Anthropic | `https://www.anthropic.com/pricing` | Standard page |

### Chinese Cloud Platforms

| Platform | Pricing URL | Extraction |
|----------|------------|------------|
| 阿里云百炼 | `https://help.aliyun.com/zh/model-studio/model-pricing` | **SPA — must use browser_console** |
| 火山引擎 | TBD | TBD |

## Alibaba Bailian Scraping (Critical)

The Bailian docs site is an SPA. Direct `curl` / `terminal` scraping **does not work** — content is JSON-embedded in page props and has control characters that break `json.loads`. Static HTML snapshots show only shell structure with no pricing data.

**Working approach:**

1. Navigate to the pricing page with `browser_navigate`
2. Use `browser_console` to extract rendered text:
   ```js
   document.querySelector('main').innerText
   ```
3. Search for the model name within the extracted text:
   ```js
   (() => {
     const text = document.querySelector('main').innerText;
     const idx = text.indexOf('DeepSeek');
     return text.substring(idx, idx + 3000);
   })()
   ```
4. Parse the plain-text pricing table from the output

**Key URLs:**
- Model pricing page: `https://help.aliyun.com/zh/model-studio/model-pricing`
- Model catalog: `https://help.aliyun.com/zh/model-studio/getting-started/models` (no pricing here, just model cards linking to model market)

**Pricing notes:**
- Bailian prices are in **CNY (元)** per 1M tokens
- "上下文缓存享有折扣" = context caching discount available (price not disclosed)
- "Batch调用半价" = batch inference at 50% price
- New users get 100万Token free for 90 days after activation
- Convert to USD at ~7.2 CNY/USD for comparison (check current rate)

## Comparison Format

Present as a compact table comparing only the same-model-equivalent tiers:

```
deepseek-v4-flash (per 1M tokens)
  Input:  Official $0.14  |  Bailian 1元 ≈ $0.14  |  ~1x
  Output: Official $0.28  |  Bailian 2元 ≈ $0.28  |  ~1x

deepseek-v4-pro (per 1M tokens)
  Input:  Official $0.435 |  Bailian 12元 ≈ $1.67  |  ~3.8x
  Output: Official $0.87  |  Bailian 24元 ≈ $3.33  |  ~3.8x
```

Always include the premium multiplier so the user can decide at a glance.

## Reference Files

- `references/deepseek-v4-pricing-2026-06-26.md` — full pricing snapshot from both DeepSeek official and Alibaba Bailian, including comparison table and all legacy/distill model prices

## Pitfalls

- **web_search tool may not be available** — fall back to browser_navigate directly to known pricing pages
- **Alibaba SPA links don't navigate via click** — clicking sidebar links in the Alibaba docs SPA may not change the visible page. Use browser_console to check `window.location.href` after clicking, or navigate directly to known URLs
- **Alibaba 404s on guessed URLs** — `billing-for-model-calls`, `model-call-charging` both 404. The canonical URL is `/zh/model-studio/model-pricing`
- **Cache-hit vs cache-miss pricing** — DeepSeek official lists both; Bailian only shows base price (cache-miss equivalent) with a "discount available" note but no disclosed rate
- **Alibaba page content truncated in snapshots** — the SPA renders thousands of elements; `browser_snapshot` output is too large to show pricing tables inline. Always fall back to `browser_console` text extraction for actual data
