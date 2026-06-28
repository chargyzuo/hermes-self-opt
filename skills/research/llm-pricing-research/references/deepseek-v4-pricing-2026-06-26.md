# DeepSeek V4 Pricing Snapshot — 2026-06-26

Data extracted live from both sources. These numbers will drift; re-scrape for current pricing.

## DeepSeek Official API

Source: https://api-docs.deepseek.com/quick_start/pricing

| Model | Input (cache hit) | Input (cache miss) | Output | Context | Max Output | Concurrency |
|-------|-------------------|---------------------|--------|---------|------------|-------------|
| deepseek-v4-flash | $0.0028 | $0.14 | $0.28 | 1M | 384K | 2500 |
| deepseek-v4-pro | $0.003625 | $0.435 | $0.87 | 1M | 384K | 500 |

Both support: Thinking mode, JSON Output, Tool Calls, Chat Prefix Completion, FIM Completion.

## Alibaba Cloud Bailian (阿里云百炼)

Source: https://help.aliyun.com/zh/model-studio/model-pricing
Updated: 2026-06-26

All prices in CNY (元) per 1M tokens. "上下文缓存享有折扣" noted but specific cache-hit prices not disclosed.

| Model ID | Input | Output | Notes |
|----------|-------|--------|-------|
| deepseek-v4-pro | 12元 | 24元 | Context caching discount available |
| deepseek-v4-flash | 1元 | 2元 | Context caching discount available |
| deepseek-v3.2 | 2元 | 3元 | — |
| deepseek-v3.2-exp | 2元 | 3元 | — |
| deepseek-v3.1 | 4元 | 12元 | — |
| deepseek-r1 | 4元 | 16元 | Batch 50% off |
| deepseek-r1-0528 | 4元 | 16元 | — |
| deepseek-v3 | 2元 | 8元 | Batch 50% off |
| deepseek-r1-distill-qwen-7b | 0.5元 | 1元 | — |
| deepseek-r1-distill-qwen-14b | 1元 | 3元 | — |
| deepseek-r1-distill-qwen-32b | 2元 | 6元 | — |
| deepseek-r1-distill-qwen-1.5b | Free | Free | Limited time |
| deepseek-r1-distill-llama-8b | Free | Free | Limited time |
| deepseek-r1-distill-llama-70b | Free | Free | Limited time; cannot call after quota exhausted |

New users: 100万Token free for 90 days after Bailian activation.

## Comparison Summary (CNY→USD at ~7.2)

| Model | Official USD | Bailian CNY | Bailian USD | Premium |
|-------|-------------|------------|-------------|---------|
| v4-flash input | $0.14 | 1元 | ~$0.14 | ~1x |
| v4-flash output | $0.28 | 2元 | ~$0.28 | ~1x |
| v4-pro input | $0.435 | 12元 | ~$1.67 | ~3.8x |
| v4-pro output | $0.87 | 24元 | ~$3.33 | ~3.8x |

Key takeaway: v4-flash pricing is near-identical; v4-pro has significant Bailian markup.
