---
name: elk-query
description: 查询 ELK 日志的通用 skill，支持双层认证（SSO + Kibana）
steps:
  # 0. 检查环境变量
  - name: check-credentials
    action: shell
    command: |
      if [ -z "$ELK_USER" ] || [ -z "$ELK_PASS" ]; then
        echo "ERROR: ELK_USER or ELK_PASS not set"
        exit 1
      fi

  # 1. 通过 SSO 获取代理 cookie
  - name: sso-auth
    action: playwright
    url: "https://itelk.bytedance.net"
    login: true
    output: sso_user_cookie

  # 2. 通过 Kibana API 登录获取 sid
  - name: kibana-login
    action: curl
    method: POST
    url: "https://itelk.bytedance.net/api/security/v1/login"
    headers:
      Cookie: "sso_user={{sso_user_cookie}}"
      Content-Type: application/json
    body: '{"username":"$ELK_USER","password":"$ELK_PASS"}'
    success_status: 204
    output: sid_cookie

  # 3. 设置通用 curl 参数
  - name: set-curl-args
    action: variable
    set:
      curl_base: "curl -s --cookie 'sso_user={{sso_user_cookie}}; sid={{sid_cookie}}' -H 'kbn-xsrf: reporting' "

  # 4. 探测需要的 API 端点
  - name: probe-apis
    action: shell
    command: |
      # 验证空间是否存在
      {{curl_base}} "https://itelk.bytedance.net/api/spaces/space/network" | jq .
      # 检查索引模式
      {{curl_base}} "https://itelk.bytedance.net/api/saved_objects/_find?type=index-pattern&search=fortinet-log-*" | jq .

  # 5. 执行查询（用户指定 index, space, query）
  - name: execute-query
    action: shell
    command: |
      {{curl_base}} -X POST "https://itelk.bytedance.net/elasticsearch/fortinet-log-*/_search?pretty" \
        -H 'Content-Type: application/json' \
        -d '{
          "size": 20,
          "query": {
            "bool": {
              "must": [
                { "match": { "devname.keyword": "EGCAI02-F04-M-121G-SPOKE01" } },
                { "match": { "logdesc": "Optional power supply not detected" } }
              ]
            }
          },
          "sort": [ { "@timestamp": { "order": "desc" } } ]
        }'

  # 6. 解析结果
  - name: parse-results
    action: shell
    command: |
      jq -r '.hits.hits[] | "\(._source["@timestamp"]) \(._source.logdesc) \(._source.logid)"' result.json

pitfalls:
  - devname 字段不是独立字段，需用 .keyword 后缀
  - 旧版本 Kibana API 路径可能不同（如 /api/elasticsearch  vs /elasticsearch）
  - 403 错误通常表示用户无该空间权限
  - 查询日志量过大时需指定 size 或使用 scroll
  - fortinet 日志字段名可能含特殊字符，用方括号引用
