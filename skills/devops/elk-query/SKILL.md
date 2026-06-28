---
name: elk-query
description: "Query ByteDance internal ELK (Kibana 6.8.0 at itelk.bytedance.net): SSO + native login, saved objects, Elasticsearch console proxy search. Covers fortinet-log index patterns and KV-encoded syslog queries."
version: 1.0.0
author: Hermes Agent
platforms: [macos]
metadata:
  hermes:
    tags: [elk, kibana, elasticsearch, bytedance, fortinet, logging]
---

# ELK 日志查询 (ByteDance Internal)

查询公司内部 ELK (Kibana 6.8.0 + Elasticsearch) 日志平台：`https://itelk.bytedance.net`。

## 架构

```
curl / Playwright → SSO 代理 (OAuth2) → Kibana 原生认证 → Elasticsearch
                    sso_user cookie       sid cookie         /api/console/proxy
```

Kibana 版本: **6.8.0**，有双层认证：
1. **SSO 代理层**：`sso_user` cookie（由 Playwright SSO state 自动处理）
2. **Kibana 原生认证层**：POST `/api/security/v1/login` → 返回 204 + `sid` cookie

## Space 空间

多个 Kibana 空间可通过 URL prefix 访问：
- Network: `/s/network/app/kibana/...`
- Service Desk: `/s/helpdesk/app/kibana/...`
- Service Operation: `/s/service-operation/app/kibana/...`

列出所有空间: `GET /api/spaces/space`

**重要**：Space-scoped API 用 `/s/{space}/api/...` 前缀（旧路径 `/s/{space}/app/kibana/api/...` 返回 404）。

## 认证方法

### 方法 1：Playwright（推荐，自动化）

使用已保存的 SSO state 文件自动登录：
```python
from playwright.sync_api import sync_playwright
STATE = "/Users/bytedance/script/NetDevOps_Byte/tasks/sso_state.json"
BASE = "https://itelk.bytedance.net"

with sync_playwright() as p:
    context = p.chromium.launch(headless=True).new_context(storage_state=STATE)
    page = context.new_page()
    page.goto(f"{BASE}/s/network/app/kibana/app/discover")
    if "/login" in page.url:
        page.locator("input[type='text']").first.fill(ELK_USER)
        page.locator("input[type='password']").first.fill(ELK_PASS)
        page.locator("button[type='submit']").first.click()
```

### 方法 2：curl（手动）

```bash
BASE="https://itelk.bytedance.net"

# Step 1: 登录获取 sid
curl -sk -c /tmp/elk_cookies.txt \
  -H 'kbn-xsrf: true' -H 'Content-Type: application/json' \
  -d "{\"username\":\"${ELK_USER}\",\"password\":\"${ELK_PASS}\"}" \
  "${BASE}/api/security/v1/login"

# Step 2: 验证登录
curl -sk -b /tmp/elk_cookies.txt -H 'kbn-xsrf: true' \
  "${BASE}/api/security/v1/me"
```

### Playwright 中调用 API（最方便）

登录后在同一 page context 中 fetch API：
```python
result = page.evaluate("""
    async () => {
        const r = await fetch('/api/console/proxy?path=fortinet-log-*/_search&method=POST', {
            method: 'POST',
            headers: { 'kbn-xsrf': 'true', 'Content-Type': 'application/json' },
            body: JSON.stringify({query: {match_all: {}}, size: 10})
        });
        return { status: r.status, body: JSON.stringify(await r.json()) };
    }
""")
```

## 可用的 API 端点

### 认证类
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/security/v1/login` | POST | 登录（body: `{username, password}`）→ 204 |
| `/api/security/v1/me` | GET | 当前用户信息 |

### Kibana 状态
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | Kibana 版本和状态（green/yellow/red） |
| `/api/stats` | GET | 详细统计（内存、请求数等） |

### 保存对象（Saved Objects）
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/saved_objects/_find?type=index-pattern&search=<keyword>` | GET | 搜索索引模式 |
| `/api/saved_objects/_find?type=search&search=<keyword>` | GET | 搜索保存的搜索 |
| `/api/saved_objects/_find?type=dashboard&per_page=20` | GET | 列出仪表盘 |
| `/api/saved_objects/index-pattern/<uuid>` | GET | 获取索引模式详情 |
| `/api/saved_objects/visualization/<uuid>` | GET | 获取可视化详情 |

**Space 限定版本**：`/s/{space}/api/saved_objects/...`

### Elasticsearch 代理（核心查询 API）
| 端点 | 说明 |
|------|------|
| `POST /api/console/proxy?path={index}/_search&method=POST` | ES 搜索 |
| `POST /api/console/proxy?path={index}/_count&method=GET` | ES 计数 |

**权限限制**：`_cat/indices`、`_cluster/health` 等监控类 API 返回 403（角色无 monitor 权限）。

## 查询示例

### fortinet-log 索引查询

fortinet-log 索引结构：
- 索引模式: `fortinet-log-*`（按月分片：`fortinet-log-2026.05`）
- 字段: `@timestamp`, `fromhost-ip`, `facility`, `msg`, `severity`
- **`msg` 字段是 Fortinet KV 编码的 syslog**：
  ```
  date=2026-05-13 time=13:07:45 devname="EGCAI02-F04-M-121G-SPOKE01"
  devid="FG121GTK25004677" logid="0100022106" type="event" subtype="system"
  level="information" logdesc="Optional power supply not detected"
  msg="Power Supply is not detected: PSU [2] LOST"
  ```
- **设备名 `devname` 不是独立字段** — 它在 `msg` 字段内部

### 按设备名 + 关键字搜索

```json
// ES Query DSL
{
  "query": {
    "bool": {
      "must": [
        {"match_phrase": {"msg": "EGCAI02-F04-M-121G-SPOKE01"}},
        {"match": {"msg": "power"}}
      ]
    }
  },
  "size": 20,
  "sort": [{"@timestamp": {"order": "desc"}}]
}
```

### 直接 ES 搜索（不指定索引，搜全部）

```
POST /api/console/proxy?path=_search&method=POST
```

### 统计设备日志总量

```json
{"query": {"match_phrase": {"msg": "DEVICE-NAME"}}, "size": 0}
```

## Pitfalls 常见陷阱

### devname 不是独立字段
Fortinet syslog 中的 `devname="...` 存储在 `msg` 字段内部，不能用 `{"term": {"devname": "..."}}` 查询。
**正确做法**：用 `match_phrase` 在 `msg` 字段中搜索。

### 旧 API 路径返回 404
`/s/network/app/kibana/api/*` 全部返回 404。
**正确路径**：
- 通用 API: `/api/*`
- Space API: `/s/{space}/api/*`

### _cat/_cluster 返回 403
`network_read` 角色没有 monitor 权限，`_cat/indices`、`_cluster/health` 等不可用。
**替代方案**：用 `_search` 或 `_count`，不指定索引通配搜全部。

### 登录 API 用 POST + JSON
不可以用 URL-encoded form。需要 `Content-Type: application/json` + `kbn-xsrf: true` header。

### 密码中的特殊字符
密码含 `@` 等特殊字符时，`write_file` 工具可能会截断。用 `patch` 工具单独修复含密码的行。

## 完整 curl 查询模板

```bash
#!/bin/bash
BASE="https://itelk.bytedance.net"
COOKIE_FILE="/tmp/elk_cookies.txt"

# 登录
curl -sk -c "$COOKIE_FILE" -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"${ELK_USER}\",\"password\":\"${ELK_PASS}\"}" \
  "${BASE}/api/security/v1/login"

# 查询（示例：搜设备 devname + power 关键字）
curl -sk -b "$COOKIE_FILE" -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"match_phrase": {"msg": "DEVICE-NAME"}},
          {"match": {"msg": "KEYWORD"}}
        ]
      }
    },
    "size": 20,
    "sort": [{"@timestamp": {"order": "desc"}}]
  }' \
  "${BASE}/api/console/proxy?path=fortinet-log-*/_search&method=POST" | \
  python3 -m json.tool
```

## 快速参考：Fortinet 日志解析

```python
# 将 fortinet KV syslog 解析为字典
msg = "date=2026-05-13 time=13:07:45 devname=\"DEV\" devid=\"ID\" ..."
fields = {}
for part in msg.split(' '):
    if '=' in part:
        k, v = part.split('=', 1)
        fields[k] = v.strip('"')
```

关键字段：`devname`（设备名）、`devid`（序列号）、`logid`（日志ID）、`logdesc`（描述）、`msg`（详情）、`level`、`type`、`subtype`。
