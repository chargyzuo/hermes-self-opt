---
name: probe-internal-api-access
description: 探测企业内部 API 端点的可访问性，处理多层认证（SSO + 应用认证）
triggers:
  - user asks “probe this URL” or “check if this API is accessible”
  - user provides an internal URL (e.g., ELK, Kibana, Grafana)
steps:
  1. Perform initial curl/wget request to the target URL without any cookies/headers.
     - Record HTTP status, redirects, and response body.
  2. If response contains SSO login page or redirect (e.g., OAuth2, SAML), note first-layer SSO.
     - Optionally check if user has existing SSO state/cookies from other services (e.g., sso_state.json).
     - If available, try to reuse those cookies; but note cross-domain limitations.
  3. If SSO is required, attempt to obtain SSO session via Playwright or browser automation:
     - Use user's credentials or already stored SSO tokens.
     - Wait for OAuth2 callback to complete and capture session cookies.
  4. With SSO cookies, re-request the target URL.
     - If response is a full HTML SPA shell or a login form (different from SSO), note second-layer application authentication.
     - If response is JSON/API data, note successful access and reveal endpoints.
  5. If all attempts fail, document the exact authentication layers:
     - Layer 1: proxy/SSO (type, provider)
     - Layer 2: application credentials
  6. Summarize in structured output: accessible? double-auth? which endpoints are reachable?
---

# Probe Internal API Access

1. **Initial recon** – `curl -v <URL>` to see if SSO redirects.
2. **Reuse existing SSO** – check user's `sso_state.json` or similar; attempt with appropriate domain.
3. **Playwright SSO flow** – run headless browser, fill SSO form, capture cookies.
4. **Re-request with cookies** – `curl --cookie <cookies> <URL>`.
5. **Detect second-layer auth** – if HTML includes login form for app, note it.
6. **Report** – return JSON with authentication chain and accessible endpoints (if any).