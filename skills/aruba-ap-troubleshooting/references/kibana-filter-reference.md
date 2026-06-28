# Kibana 日志过滤 — Aruba WAC syslog 专用

Kibana Discover 中查 WAC syslog 的 KQL 过滤语法速查。

## KQL 基本语法

| 运算符 | 示例 | 说明 |
|--------|------|------|
| AND | `a AND b AND c` | 全部满足 |
| OR | `a OR b` | 满足任意 |
| NOT | `NOT a` | 排除 |
| 引号 | `"has space"` | 含空格/特殊字符必须加引号 |

## Aruba WAC 常用模板

### AP 下线日志（stm 进程）

```
"stm" AND "down" AND "<AP名>"
```

### AP 下线 + 恢复（宽口径）

```
"<AP名>" AND ("down" OR "reboot" OR "heartbeat" OR "lost" OR "up")
```

### AP 认证失败

```
"<AP名>" AND ("auth" OR "authentication" OR "failed" OR "cert")
```

### 按 MAC 查

```
"<MAC: xx:xx:xx:xx:xx:xx>" AND ("down" OR "reboot" OR "heartbeat")
```

### 按 IP 查

```
"<AP IP>" AND "stm"
```

## WAC syslog 关键进程

| 进程名 | 全称 | 作用 |
|--------|------|------|
| stm | Station Management | 终端关联/漫游/上下线 |
| sapd | AP Daemon | AP 注册/配置下发/隧道 |
| fpapps | Firewall Policy Apps | 防火墙/ACL/角色策略 |
| authmgr | Auth Manager | 802.1x/MAC 认证/Captive Portal |
| nanny | Process Nanny | 进程守护/重启监控 |

## WAC syslog 格式

```
Jun 26 13:07:05  10.76.184.130  stm[1234]: <501065> <WARN> 
AP CNPEK144-F02-AP11-640D: AM 74:9e:75:c9:64:0d: AP down
```

常见下线原因：`reboot` `restart` `configuration change` `heartbeat lost` `power off` `crash`

## KQL vs Lucene

| 特性 | KQL | Lucene |
|------|-----|--------|
| 空格处理 | 必须引号 | 默认 AND 分词 |
| 默认语法 | Kibana 7.0+ | 旧版 |

KQL 是当前默认语法，优先用。
