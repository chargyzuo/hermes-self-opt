# 飞连 SWG vs Zscaler: Identifying the True Blocking Source

## Case Context

**Problem**: Telegram APP shows "connecting", cannot send/receive messages. Web Telegram works fine. Device has two zero-trust components: Zscaler and 飞连 SWG.

**Initial Misdiagnosis**: First analysis incorrectly blamed Zscaler for blocking MTProto protocol.

**User Correction**: User clarified that `30.200.x.x` is 飞连 SWG's DNS proxy, not Zscaler. Both components could proxy traffic.

## Key Evidence Chain

### 1. TTL Analysis — The Smoking Gun

| Traffic Path | TTL | Interpretation |
|-------------|-----|----------------|
| VPN tunnel → 91.108.56.117 SYN-ACK | **64** | VPN exit proxy (NOT real Telegram server) |
| VPN tunnel → 91.108.56.117 RST | **64** | VPN exit security device blocking |
| Direct → 91.108.56.117 SYN-ACK | **47** | Real Telegram server (Netherlands, after network hops) |

**Conclusion**: RST packets came from VPN tunnel exit, not Zscaler cloud gateway or real Telegram server.

### 2. VPN Tunnel Architecture

```
WireGuard VPN:
- Tunnel endpoint: 34.143.197.141 (Google Cloud)
- Local tunnel IP: 192.168.5.134 (utun4 interface)
- Zero-trust: 飞连 SealSuite (sealsuite.bytedance.com → Akamai 23.220.203.147)
```

### 3. Traffic Routing Evidence

**Telegram (hardcoded IP 91.108.56.117)**:
- No DNS query observed (app uses hardcoded IPs)
- Traffic routed through VPN tunnel (192.168.5.134)
- Blocked by VPN exit security gateway

**DNS-resolved traffic** (e.g., gateway.zscalertwo.net):
- DNS returns 飞连 SWG proxy IP: `30.200.4.128`
- Traffic goes through 飞连 SWG first
- Then to actual destination (Zscaler gateway)

### 4. 飞连 SWG vs Zscaler Relationship

```
┌─────────────────────────────────────────────────────┐
│ Flow for DNS-resolved traffic:                      │
│ App → DNS → 飞连 SWG (30.200.x.x) → Destination     │
│                                                     │
│ Zscaler traffic ALSO goes through 飞连 SWG:         │
│ gateway.zscalertwo.net → 30.200.4.128 → Zscaler     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Flow for hardcoded IP (Telegram):                   │
│ Telegram APP → VPN tunnel → VPN exit security       │
│ → detects MTProto → RST block                       │
│ (Bypasses DNS proxy entirely)                       │
└─────────────────────────────────────────────────────┘
```

### 5. RST Blocking Pattern

```
Time 0.284s (first attempt):
- Client sends 169 bytes (MTProto data)
- RST arrives with ack=170 (exactly data+1)
- TTL=64 (from VPN exit, not real server)
```

Pattern: Security device analyzed packet content and immediately blocked.

## Correct Diagnosis

**Blocking Source**: 飞连 VPN tunnel exit security gateway, NOT Zscaler.

**Reason**:
1. Telegram uses hardcoded IPs → no DNS lookup → bypasses 飞连 SWG DNS proxy
2. Hardcoded IP traffic routed to VPN tunnel
3. VPN exit security gateway detects MTProto protocol
4. Gateway sends TTL=64 RST to block connection

**Why Web Telegram Works**:
- Web version uses standard HTTPS (web.telegram.org)
- Domain gets DNS resolution → goes through 飞连 SWG
- HTTPS can be proxied/inspected → allowed

## Resolution Steps

1. **飞连 VPN policy**: Add Telegram IP ranges to whitelist
   - 91.108.56.0/22, 149.154.160.0/20, 128.14.110.0/24
   
2. **VPN routing**: Exclude Telegram IPs from tunnel routing
   - Let Telegram go direct (en0) instead of VPN tunnel

3. **飞连 security**: Allow MTProto protocol detection bypass

## tshark Commands Used

```bash
# TTL comparison - key evidence
tshark -r capture.pcap -Y "ip.addr==91.108.56.117 and tcp.flags.syn==1 and tcp.flags.ack==1" -T fields -e ip.ttl

# VPN tunnel detection
tshark -r capture.pcap -Y "wg" -T fields -e ip.src -e ip.dst

# DNS proxy signature
tshark -r capture.pcap -Y "dns.a" -T fields -e dns.qry.name -e dns.a

# RST source identification
tshark -r capture.pcap -Y "ip.addr==91.108.56.117 and tcp.flags.reset==1" -T fields -e ip.src -e ip.ttl -e tcp.seq -e tcp.ack

# SNI for proxy target identification
tshark -r capture.pcap -Y "tls.handshake.extensions_server_name" -T fields -e ip.src -e ip.dst -e tls.handshake.extensions_server_name
```

## Lesson Learned

When multiple security components exist:
1. **Don't assume** blocking based on component names alone
2. **Use TTL forensics** to identify actual packet source
3. **Trace traffic path**: DNS-resolved vs hardcoded IP have different routes
4. **Check proxy relationships**: Some components may proxy others (Zscaler via 飞连 SWG)