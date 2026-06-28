---
name: pcap-analysis
description: Analyze pcap packet captures for network troubleshooting — TTL forensics, VPN tunnel detection, security proxy identification, and protocol blocking diagnosis.
tags: [network, troubleshooting, pcap, tshark, wireshark, security-proxy, vpn]
---

# pcap Packet Capture Analysis

Analyze pcap files to diagnose network connectivity issues, identify blocking sources, and trace traffic through VPN tunnels and security proxies.

## When to Load

- User provides a pcap file for analysis
- Troubleshooting "connecting" issues, blocked traffic, or unreachable services
- Need to identify which security component is blocking traffic
- Analyzing VPN routing and tunnel behavior

## Core Methodology

### 1. Initial Assessment

```bash
# Basic pcap info
capinfos capture.pcap

# Protocol distribution
tshark -r capture.pcap -q -z io,phs

# Top conversations
tshark -r capture.pcap -q -z conv,ip
tshark -r capture.pcap -q -z conv,tcp
```

### 2. TTL Forensics — Critical Technique

**TTL reveals packet source**: Real servers have TTL reduced by network hops (~40-50 for international), while local/proxy responses have TTL=64 (default for Linux/local).

```bash
# Compare TTL of SYN-ACK vs RST packets
tshark -r capture.pcap -Y "ip.addr==TARGET_IP and tcp.flags.syn==1 and tcp.flags.ack==1" -T fields -e ip.ttl

tshark -r capture.pcap -Y "ip.addr==TARGET_IP and tcp.flags.reset==1" -T fields -e ip.src -e ip.ttl
```

**Interpretation**:
| TTL | Source |
|-----|--------|
| 64 | Local/VPN exit/proxy device (NOT real server) |
| 40-50 | Real remote server (after network hops) |

### 3. VPN Tunnel Detection

Identify VPN interfaces and routing:

```bash
# WireGuard tunnel packets
tshark -r capture.pcap -Y "wg" -T fields -e ip.src -e ip.dst

# VPN interface traffic (e.g., utun4)
tshark -r capture.pcap -Y "ip.src==VPN_LOCAL_IP or ip.dst==VPN_LOCAL_IP" -T fields -e ip.src -e ip.dst
```

**Compare paths**:
- Direct traffic: `192.168.1.x` → target (check TTL of response)
- VPN tunnel: `192.168.5.x` → target (check TTL of response)

### 4. Security Proxy Identification

When multiple security components exist (e.g., Zscaler + 飞连 SWG), use evidence to identify the blocking source:

**DNS Proxy Signature**:
```bash
# DNS responses returning internal IPs indicate proxy
tshark -r capture.pcap -Y "dns.a" -T fields -e dns.qry.name -e dns.a
```
- Internal IP ranges (e.g., `30.200.x.x`) = DNS proxy active
- Real public IPs = No DNS proxy intervention

**Hardcoded IP Traffic**:
- Apps using hardcoded IPs bypass DNS proxy entirely
- These go direct to VPN tunnel, subject to VPN exit security

**Zscaler Signature**:
- Local proxy port `127.0.0.1:9000` (ZCC Client Connector)
- Gateway domain: `gateway.zscalertwo.net`

### 5. RST Blocking Analysis

When TCP RST blocks connections:

```bash
# Full sequence including TTL, seq, ack
tshark -r capture.pcap -Y "ip.addr==TARGET_IP and tcp.flags.reset==1" -T fields -e ip.src -e ip.ttl -e tcp.seq -e tcp.ack

# Timing pattern — security devices RST immediately after data detection
tshark -r capture.pcap -Y "ip.addr==TARGET_IP" -T fields -e frame.time_relative -e tcp.flags.str -e tcp.len
```

**Pattern for security blocking**:
- SYN → SYN-ACK → ACK → Client sends data → Immediate RST (within milliseconds)
- RST ack value matches client data length + 1 = "analyzed and blocked"

### 6. Protocol Blocking Diagnosis

**MTProto Blocking** (Telegram):
- Data packets ~150-185 bytes
- RST immediately after first data packet
- Web version works (HTTPS), app blocked (MTProto)

**SSL/TLS Interception**:
- Look for TLS handshake failures
- Certificate validation errors
- SNI mismatch or missing

## Pitfalls

### ❌ Assume blocking based on DNS proxy alone
DNS proxy handles DNS-resolved traffic, but hardcoded IPs bypass it entirely. Check the actual traffic path.

### ❌ Blame the wrong security component
When multiple zero-trust components exist (Zscaler + 飞连, etc.), use TTL analysis to pinpoint the actual blocking source.

### ❌ Trust IP address as real server
TTL=64 means the packet is from a local/proxy source masquerading as the target. Verify with TTL comparison.

## Key tshark Filters

```bash
# RST packets with details
tshark -r capture.pcap -Y "tcp.flags.reset==1" -T fields -e ip.src -e ip.dst -e ip.ttl -e tcp.seq -e tcp.ack

# SYN-ACK TTL comparison
tshark -r capture.pcap -Y "tcp.flags.syn==1 and tcp.flags.ack==1" -T fields -e ip.src -e ip.ttl

# SNI extraction
tshark -r capture.pcap -Y "tls.handshake.extensions_server_name" -T fields -e ip.src -e ip.dst -e tls.handshake.extensions_server_name

# WireGuard tunnels
tshark -r capture.pcap -Y "wg" -q -z conv,ip

# VPN vs direct traffic split
tshark -r capture.pcap -Y "ip.src==VPN_IP or ip.dst==VPN_IP" -q -z conv,tcp
tshark -r capture.pcap -Y "ip.src==DIRECT_IP or ip.dst==DIRECT_IP" -q -z conv,tcp
```

## Session Reference

See `references/feilian-vs-zscaler.md` for a detailed case study analyzing Telegram blocking with 飞连 SWG + Zscaler environment.