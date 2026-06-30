---
name: tcp-connectivity-troubleshooting
title: TCP Connectivity Troubleshooting
description: Systematic diagnosis of TCP port connectivity failures — "telnet port refused but tcpdump shows packets arriving". Covers IPv4/IPv6 mismatch, firewall rules, service binding, and SELinux/AppArmor.
category: network
tags: [tcp, connectivity, port, firewall, ipv6, iptables, nftables, troubleshooting]
---

# TCP Connectivity Troubleshooting

Systematic workflow when a client cannot connect to a TCP port on a remote server.

## Trigger

- `telnet <server> <port>` → `Connection refused`
- `curl -v <url>` → `Connection refused`
- But **tcpdump on the server shows the SYN packet arriving**

## The Diagnostic Pyramid

### Layer 1: Is the service listening at all?

```bash
ss -tlnp | grep :<PORT>
```

**Interpretation**:
| Output | Meaning | Action |
|--------|---------|--------|
| `LISTEN 0.0.0.0:<PORT>` | IPv4 only | ✅ OK for IPv4 clients |
| `LISTEN [::]:<PORT>` | IPv6 (dual-stack usually on by default) | ✅ OK for IPv6 + IPv4 |
| `LISTEN 127.0.0.1:<PORT>` | Loopback only | ❌ External cannot reach |
| (empty) | Service not running | ❌ Start the service |

## Pitfalls

1. **Python http.server IPv6**: Default IPv4-only. `--bind ::` only works Python ≥ 3.8. Python 3.7 needs custom `TCPServer` subclass with `address_family = AF_INET6`, and even then may silently fail with IPv6 connections.
2. **apt "newest" is distro-scoped**: `apt install python3` showing "python3 is already the newest version" only means latest in the current Debian release repo, NOT latest upstream. Add backports/deadsnakes for newer binary packages instead of compiling from source.
3. **socat printf caveat**: `SYSTEM:'printf "..."'` breaks `\r\n` in shell — use `FILE:` with a pre-written binary response.
4. **ss not on macOS**: Use `lsof -iTCP -sTCP:LISTEN -P -n` instead.

## Quick Test Listeners (no Python needed)

When Python compilation isn't practical (slow network, old distro), use `socat` for a one-command HTTP listener:

```bash
# 1. Write a valid HTTP response to a file
printf 'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 12\r\nConnection: close\r\n\r\nHello World!' > /tmp/http-response.bin

# 2. Start IPv6 listener
socat TCP6-LISTEN:443,reuseaddr,fork FILE:/tmp/http-response.bin
```

Client test:
```bash
curl -6 http://[<IPv6_ADDR>]:443 -v
```

> ⚠️ Avoid `EXEC:/script.sh` or `SYSTEM:'printf ...'` — shell interpolation of `\r\n` in `printf` arguments breaks HTTP headers (`Content-Type: not found`). Use `FILE:` with a pre-written binary response instead.

### Layer 2: Address family mismatch (THE MOST COMMON ROOT CAUSE)

If tcpdump sees the SYN but client gets `Connection refused`:

```bash
# Confirm what protocol the service listens on
ss -tlnp | grep :<PORT>
```

#### The key question:
**Is the client connecting via IPv6, but the service only listens on IPv4?**

> IPv6 SYN reaches the NIC (tcpdump catches it at the raw socket level).
> But the kernel's IPv6 stack finds no socket at `[::]:<PORT>`.
> Kernel sends RST → client sees "Connection refused".

**Fix**: Reconfigure the service to also listen on `[::]:<PORT>`.

#### Common tools and their IPv6 defaults:

| Tool | IPv6 default | Fix |
|------|-------------|-----|
| `python3 -m http.server 443` | ❌ IPv4 only | `python3 -m http.server 443 --bind ::` (Python 3.8+) |
| `nginx` | ❌ Need explicit `listen [::]:443` | `listen 443 ssl; listen [::]:443 ssl;` |
| `nc -l -p 443` | ❌ IPv4 only | `nc -6 -l -p 443` |
| `socat TCP-LISTEN:443` | ❌ IPv4 only | `socat TCP6-LISTEN:443,...` |

#### Python 3.7–3.8 (where `--bind ::` is not supported):

```bash
# ✅ Correct: must subclass TCPServer and set address_family to AF_INET6
python3 -c "
import socketserver, http.server, socket

class IPv6TCPServer(socketserver.TCPServer):
    address_family = socket.AF_INET6

s = IPv6TCPServer(('::', 443), http.server.SimpleHTTPRequestHandler)
print('HTTP server on [::]:443', flush=True)
s.serve_forever()
"
```

> ❌ `socketserver.TCPServer(('::', 443), ...)` without address_family override fails with `socket.error` — TCPServer defaults to `AF_INET` and rejects IPv6 addresses.

> ⚠️ Python 3.7's `http.server` may still have bugs with IPv6 connections (no response after TCP handshake). If the above gives silent failures, skip Python entirely and use `socat` (see Quick Test Listeners below).

Or use a raw TCP socket:
```bash
python3 -c "
import socket
s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('::', 443))
s.listen(5)
while True:
    conn, addr = s.accept()
    conn.close()
"
```

### Layer 3: Firewall inspection

```bash
# iptables (all)
iptables -L INPUT -n -v | grep :<PORT>

# nftables
nft list ruleset

# firewalld (RHEL/CentOS/Rocky)
firewall-cmd --list-all

# ufw (Ubuntu)
ufw status verbose
```

**Look for**:
- `REJECT` → client gets "Connection refused" immediately
- `DROP` → client hangs/times out (no response at all)
- Missing `ACCEPT` rule when default policy is `DROP`

### Layer 4: Mandatory Access Control

```bash
# SELinux (RHEL family)
getenforce
ausearch -m avc -ts recent | grep <PORT>

# AppArmor (Debian/Ubuntu)
sudo aa-status | grep <service>
sudo journalctl -k -f | grep DENIED
```

### Layer 5: Confirm with tcpdump

```bash
# TCP SYN only — exactly what the kernel sees
tcpdump -i any 'tcp[tcpflags] & tcp-syn != 0' and dst port <PORT> -nn

# For a specific client IPv6
tcpdump -i any dst host <IPv6_ADDR> and dst port <PORT> and 'tcp[tcpflags] & tcp-syn != 0' -nn

# Full handshake
tcpdump -i any host <CLIENT_IP> and port <PORT> -nn
```

**tcpdump IPv6 syntax note**: Use `and` to combine conditions:
- ✅ `port 443 and host fd00::1`
- ✅ `dst port 443 and src host fd00::1`
- ❌ `port 443 host fd00::1` (syntax error)

## The Golden Flow for "SYN arrives, RST comes back"

```
tcpdump shows SYN ✅
         ↓
ss shows LISTEN at 0.0.0.0:<PORT> but NOT [::]:<PORT>
         ↓
Client is connecting from IPv6
         ↓
ROOT CAUSE: Service not listening on IPv6
         ↓
Fix: Add IPv6 listen directive
```

## Verification

```bash
# From the server itself (bypasses most firewall)
curl -6 https://[::1]:<PORT> -k -v    # IPv6 loopback
curl -4 http://127.0.0.1:<PORT> -v   # IPv4 loopback

# From client, after fix
telnet <SERVER_IPv6> <PORT>
```

## References

See `references/tcpdump-ipv6-syntax.md` for quick reference on IPv6 tcpdump filter syntax.
See `references/ipv6-service-binding.md` for common server software IPv6 binding configuration.
