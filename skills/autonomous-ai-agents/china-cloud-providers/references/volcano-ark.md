# 火山方舟 (Volcano Ark / Volcengine Ark)

> Setup session: June 2026, user confirmed API works with model IDs directly.
> Base region: Beijing (`ark.cn-beijing.volces.com`).

## Endpoint

```
https://ark.cn-beijing.volces.com/api/v3
```

## API Key Format

```
ark-<uuid4>-<hex-chunk>
```

The key is stored directly in `custom_providers[].api_key` in config.yaml (not in `.env`).

## Verified: Model IDs Work in Chat Completions

Tested with `curl` — Volcano Ark's `/api/v3/chat/completions` accepts model **IDs** (from `GET /api/v3/models`) directly in the `model` field. No endpoint `ep-xxx` needed for current-gen models.

**Successful test** (HTTP 200):
```json
{
  "model": "doubao-seed-2-1-pro-260628",
  "messages": [{"role": "user", "content": "Say hello in one word"}],
  "max_tokens": 20
}
```

Response included `reasoning_content` (thinking trace) and `content: "Hello"`.

## Config Format (Correct)

```yaml
custom_providers:
  - name: fangzhou                    # lowercase; used as provider:custom:fangzhou
    base_url: https://ark.cn-beijing.volces.com/api/v3
    api_key: ark-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx-xxxxx

model:
  default: doubao-seed-2-1-pro-260628
  provider: custom:fangzhou
```

## Available Active Models (LLM + tool calling, as of June 2026)

| Model ID | Context | Output | Notes |
|----------|---------|--------|-------|
| `doubao-seed-2-1-pro-260628` | 262K | 262K | Latest pro, VLM |
| `doubao-seed-2-1-turbo-260628` | 262K | 262K | Latest turbo, VLM |
| `doubao-seed-2-0-pro-260215` | 262K | 131K | VLM |
| `doubao-seed-2-0-lite-260215` | 262K | 131K | VLM |
| `doubao-seed-2-0-mini-260215` | 262K | 131K | VLM |
| `doubao-seed-1-6-250615` | 262K | 65K | VLM |
| `doubao-seed-1-6-flash-250615` | 262K | 32K | Fast, VLM |
| `doubao-seed-evolving` | 262K | 262K | Auto-follows latest |
| `doubao-seed-code-preview-251028` | 262K | 32K | Code-optimized |
| `doubao-1-5-pro-32k-250115` | 131K | 12K | Older but stable |
| `deepseek-v4-pro-260425` | 1M | 393K | DeepSeek V4 Pro |
| `deepseek-v4-flash-260425` | 1M | 393K | DeepSeek V4 Flash |
| `deepseek-v3-2-251201` | 131K | 32K | DeepSeek V3.2 |
| `glm-4-7-251222` | 200K | 131K | GLM-4 7B |
| `qwen3-32b-20250429` | — | — | Qwen3 32B |
| `kimi-k2-thinking-251104` | 262K | 32K | Kimi K2 thinking |

**Check active models**: `curl -s https://ark.cn-beijing.volces.com/api/v3/models -H "Authorization: Bearer $ARK_KEY" | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data'] if m.get('status') not in ('Shutdown','Retiring') and m.get('domain') in ('LLM','VLM','Router')]"`

## Switching Mid-Session

```text
/model custom:fangzhou:doubao-seed-2-1-pro-260628
/model custom:fangzhou:deepseek-v4-flash-260425
/model custom:fangzhou:doubao-seed-1-6-flash-250615
```

Note: each `/model` switch requires a subsequent API call — the model swap takes effect on the next assistant reply.

## Pitfalls

- **❌ Don't add `model: FangZhou` inside the `custom_providers` entry** — that field is not valid there. The model name goes in the main `model.default` field.
- **❌ Don't write config.yaml via write_file/patch/terminal** — Hermes security blocks it. Use `hermes config set` or editor.
- **You cannot see custom provider models in `hermes model` interactive picker** — they're not built-in providers. Use `/model custom:fangzhou:<id>` in-session.
- Some older models (status=Shutdown) require creating an endpoint in the console first. Check `status` from `/v3/models`.
- The api_key value in config.yaml appears in plaintext — keep `config.yaml` access-restricted.
- `reasoning_content` field appears in API responses — Hermes handles this automatically if the response format is OpenAI-compatible.
