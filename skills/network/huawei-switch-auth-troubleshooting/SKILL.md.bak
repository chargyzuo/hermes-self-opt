---
name: huawei-switch-auth-troubleshooting
description: "Diagnose switch dot1x/MAB/authentication issues — stuck pre-auth, RADIUS failures, IP conflicts. Covers Huawei VRP (S5731) and Arista EOS (720XP). See references/arista-dot1x-accounting.md for Arista-specific two-step auth flow and accounting behavior."
version: 1.3.0
author: Hermes Agent
platforms: [linux, macos]
metadata:
  hermes:
    tags: [huawei, switch, dot1x, mab, radius, authentication, troubleshooting, networking]
---

# Huawei Switch Authentication Troubleshooting

Diagnose dot1x / MAC Authentication Bypass (MAB) / RADIUS authentication issues on
switches. Covers Huawei VRP (S5731) and Arista EOS (720XP).

Use the `mcp_switch_switch_execute` tool to run commands on the switch.
**This tool supports ALL device types (Huawei, Arista, Cisco, etc.) via Netbox WebSSH proxy.**

For Arista EOS switches, load `references/arista-dot1x-accounting.md` FIRST — Arista has
a fundamentally different two-step auth flow and accounting behavior. Key differences:
- Arista `aaa accounting dot1x start-stop` sends ONLY Start/Stop, no periodic Interim-Update
- Arista uses "IP Locking" (address locking + DHCP Leasequery) to learn client IPs
- **Address Locking is NOT STP — it's a per-IP permit list at L3, not L2 port blocking.** Auth success + MAC in VLAN does NOT guarantee traffic will reach the gateway. See `references/arista-dot1x-accounting.md` → "Address Locking 不是 STP" and "Address Locking 排查 — Leasequery 回复分析" for the `show address locking counters` diagnostic methodology (compare LeaseActive vs LeaseUnknown ratios against a baseline switch)
- **DHCP Option 82 + Leasequery Mismatch** — When upstream DHCP relay has `ip dhcp relay information option` but Address Locking sends DHCPLEASEQUERY without Option 82, the DHCP server returns UNKNOWN and the client gets no IP. See `references/arista-dhcp-option82-leasequery-mismatch.md`
- Arista requires local ACL matching FreeRadius Filter-Id
- Arista has NO pre-auth VLAN — port is completely isolated until authentication succeeds
- **SUPPLICANT-TIMEOUT**: When the client doesn't respond to EAPOL, RADIUS is never contacted. AAA Server Returned is all empty/0xFFFFFFFF. The MAC lands in the auth-failure VLAN (`dot1x authentication failure action traffic allow vlan <N>`) with STATIC type. See `references/arista-supplicant-timeout.md`.
- **Arista dot1x host-mode**: Four modes — single-host, multi-host, multi-host authenticated, multi-domain. See `references/arista-host-mode.md`.
- Never enter `configure` mode — read-only access only
- Use `terminal length 0` to disable paging (not `screen-length 0 temporary` like Huawei)
- For packet capture and debug methods, load `references/arista-debug-and-capture.md`
- For real DHCP DORA capture with mac/ip/port details, see `references/arista-dhcp-dora-capture.md`
**The MCP switch tool supports ALL device types (Huawei, Arista, Cisco, etc.) via Netbox WebSSH proxy — it is not Huawei-only.**

For Arista EOS switches, see `references/arista-dot1x-accounting.md` for the Arista-specific
authentication + accounting flow, pitfalls, and command reference. Arista has a fundamentally
different two-step auth process (authentication then Filter-Id-based authorization) and
accounting behavior (no periodic Interim-Update by default unless `aaa accounting update periodic` is configured).

## Diagnostic Workflow

### 1. Check user authentication state

```bash
dis access-user mac-address XXXX-XXXX-XXXX
```

Key fields:
- **Status**: `Success` (authenticated) vs `Pre-authen` (stuck)
- **Domain-name**: `-` means no domain assigned yet
- **User authentication type**: `No authentication` means auth hasn't started;
  should show `MAC authentication` or `802.1X authentication` when in progress
- **User vlan event**: `Pre-authen` confirms stuck state
- **User access time**: tracks when the session was created

### 2. Check WHY authentication failed (FIRST-TIER for pre-auth)

```bash
dis aaa online-fail-record mac-address XXXX-XXXX-XXXX
```

This reveals WHY authentication is being rejected — e.g., `IP address conflict`,
`RADIUS timeout`, `Authentication rejected`. Run this BEFORE investigating
RADIUS connectivity, as the root cause may be local to the switch (IP conflict
with another user in the same VLAN, silent MAC timeout, etc.).

**Important**: This is the single most important command for a stuck pre-auth
user. RDAUTHDOWN logs are global and may be misleading. The online-fail-record
is per-MAC and tells you exactly why THIS user failed.

### 3. Check port configuration and stats

```bash
dis current-configuration interface GigabitEthernet 0/0/X
dis dot1x interface GigabitEthernet 0/0/X
dis mac-authen interface GigabitEthernet 0/0/X
```

Check for:
- `authentication-profile` applied
- `authentication dot1x-mac-bypass` (combined auth mode)
- EAPOL packet counts → high `Multicast Trigger` means switch keeps probing for dot1x
- `Enter Enquence` vs `Authentication Success` ratio → large gap means many incomplete auths

### 4. Check for link flaps

```bash
dis interface GigabitEthernet 0/0/X | include Last|flap|CRC
```

Link flaps reset the authentication timer. If flap interval < Mac-By-Pass Delay (default 30s),
MAB will never trigger. CRC=0 with frequent flaps usually means client-side disconnects.

### 5. Check RADIUS configuration and connectivity

```bash
dis radius-server configuration
```

Key fields:
- **Server algorithm**: `master-backup based-user` — all new sessions hit master first
- **[up]/[down]** status next to each server
- **Detect-interval**: how often the switch probes server health (default 60s)
- **Timeout-interval** (2s) × **Retransmission** (5) = ~12s before giving up on a server

### 6. Check RADIUS server logs on the switch

```bash
dis logbuffer | include RDAUTHDOWN
dis logbuffer | include RDAUTHUP
```

`RDAUTHDOWN` without corresponding `RDAUTHUP` means the server went down and the switch
hasn't detected its recovery yet.

### 7. Check the authentication profile and domain chain

```bash
dis current-configuration | begin authentication-profile name <name>
dis domain name <domain>
dis authentication-scheme
dis radius-server configuration template <template>
```

Trace the full chain: authentication-profile → access profiles → domain → auth scheme → RADIUS template.

## Common Pitfalls

### test-aaa is unreliable for MAB
`test-aaa` sends PAP/CHAP authentication requests. MAB uses `Service-Type=10` (Call-Check)
with `Calling-Station-Id` as the MAC. The RADIUS server will reject test-aaa for MAB users
even when real MAB works. Do NOT use test-aaa failure as proof of RADIUS issues.

### Path MTU is rarely the problem
RADIUS packets are typically 200-400 bytes. Path MTU 1500 (tested with `ping -s 1472 -f`)
is standard and sufficient. Only investigate MTU if you see RADIUS timeouts without
RDAUTHDOWN logs.

### Empty mac-access-profile
On combined auth profiles (`authentication dot1x-mac-bypass`), if the `mac-access-profile`
is empty (no domain configured), MAB may not know which RADIUS template to use. The
`access-domain <domain> force` in the authentication profile SHOULD force the domain,
but verify this on your VRP version.

### DHCP works in pre-auth
Huawei switches allow DHCP broadcast traffic in pre-auth state by default. A client
getting an IP does NOT mean authentication succeeded — the IP may be from a prior
successful session or DHCP is passing through the pre-auth filter.

### IP conflicts block authentication
If the switch detects an IP address conflict (via its local auth module, NOT DHCP
snooping — this is a vendor-specific check, not RFC 2865), it may reject
authentication. Docker's default bridge (172.17.0.1) on client machines is a common
source. Check `dis aaa online-fail-record` — this is per-user and tells you the
exact failure reason.

**Docker dual-mechanism**: Docker can cause TWO independent blocks:
1. **IP conflict**: docker0 bridge IP collides with another device in the same VLAN
   → switch rejects auth after RADIUS accepts
2. **Link flap**: Docker's network stack changes trigger NetworkManager to reset
   the interface → MAB timer never completes → auth never starts

Either one alone can block the user. Both together create a double lock.
See `references/ip-conflict-docker-auth-block.md` for full details.

## Path MTU Testing from Switch

```bash
ping -s 1472 -f -c 3 <radius-ip>   # max Ethernet payload with DF set
ping -s 2000 -f -c 3 <radius-ip>   # test beyond 1500 MTU
```

1472 data + 28 (ICMP+IP) = 1500 bytes. If 1472 passes and 2000 fails, path MTU = 1500.

## S5731 / VRP8 Command Reference

### Commands That WORK

| Command | Notes |
|---------|-------|
| `dis access-user mac-address <mac>` | Show specific user details |
| `dis access-user` | All authenticated/pre-auth users |
| `dis mac-address <mac>` | MAC table lookup |
| `dis mac-authen interface GigabitEthernet 0/0/<n>` | Port MAC auth stats |
| `dis dot1x interface GigabitEthernet 0/0/<n>` | Port dot1x stats |
| `dis radius-server configuration` | All RADIUS templates |
| `dis radius-server configuration template <name>` | Single template detail |
| `dis domain` | List all domains |
| `dis domain name <name>` | Domain detail |
| `dis authentication-scheme` | Auth schemes |
| `dis accounting-scheme` | Accounting schemes |
| `dis logbuffer \| include <pattern>` | Search logs |
| `dis current-configuration interface GigabitEthernet 0/0/<n>` | Interface config |
| `dis current-configuration \| include <pattern>` | Grep running config |
| `dis current-configuration \| begin <pattern>` | Config from pattern onward |
| `dis arp` | ARP table |
| `dis version` | Device model and version |

### Commands That DON'T Work on S5731

| Command | Error/Issue |
|---------|-------------|
| `dis mac-access-profile name <name>` | Unrecognized command |
| `dis dot1x-access-profile name <name>` | Unrecognized command |
| `dis authentication-profile name <name>` | Unrecognized command |
| `dis current-configuration \| section <pattern>` | Unrecognized — use `\| begin` instead |
| `dis logbuffer \| tail <n>` | Unrecognized |
| `dis radius statistics` | Ambiguous command |
| `dis radius-server active <port>` | Unrecognized |
| `dis radius-client statistics` | Unrecognized |

**Workaround for access-profile inspection:** Use `dis current-configuration | begin <profile-name>` to see the profile blocks inline.

### Output Truncation

When `dis current-configuration | begin ...` produces too much output:
- Use `dis current-configuration | include <specific pattern>` for targeted searches
- Chain multiple targeted `include` queries rather than one big `begin`

## Profile Chain Architecture (Huawei Combined Auth)

```
Interface
  └── authentication-profile <name>
        ├── dot1x-access-profile <name>    (EAP method, reauth, timers)
        ├── mac-access-profile <name>      (domain, username format)
        ├── access-domain <domain> [force] (domain assignment)
        ├── authentication dot1x-mac-bypass
        ├── authentication event authen-server-down action authorize ...
        └── authentication event authen-server-up action re-authen
              │
              ▼
        RADIUS template <name>
          ├── radius-server authentication <ip> <port> weight <n>
          ├── radius-server accounting <ip> <port> weight <n>
          └── (detect, timeout, dead-time settings)
              │
              ▼
        Domain <name>
          ├── authentication-scheme <name>   (→ RADIUS/Local/HWTACACS)
          ├── accounting-scheme <name>
          └── radius-server <template>
```

Access profiles may appear empty in running config — this means they use defaults.

## Pre-authen Diagnostics — Extended Phase Workflow

### Phase 1: Quick Triage

```bash
dis access-user mac-address <mac>
dis access-user
dis mac-address <mac>
```

### Phase 2: Authentication Profile Chain

```bash
dis current-configuration interface GigabitEthernet 0/0/<port>
dis current-configuration | begin authentication-profile name <profile_name>
dis domain name <domain>
dis authentication-scheme
dis accounting-scheme
```

### Phase 3: RADIUS Investigation

```bash
dis radius-server configuration
dis radius-server configuration template <template_name>
dis mac-authen interface GigabitEthernet 0/0/<port>
dis dot1x interface GigabitEthernet 0/0/<port>
dis logbuffer | include AUTHD
dis logbuffer | include RDAUTHUP
```

### Phase 4: Escape/Critical VLAN Check

```bash
dis current-configuration | include authen-server
dis current-configuration | include service-scheme
```
Look for `authentication event authen-server-down action authorize service-scheme <name>` and `undo authentication pre-authen-access enable`.

## References

- `references/arista-dot1x-accounting.md` — Arista-specific two-step auth flow and accounting behavior
- `references/arista-supplicant-timeout.md` — Arista SUPPLICANT-TIMEOUT: client unreachable by EAPOL, RADIUS never contacted, auth-failure VLAN placement
- `references/arista-host-mode.md` — Arista dot1x host-mode: single-host, multi-host, multi-host authenticated, multi-domain; interaction with MAB and quiet-period
- `references/arista-dhcp-option82-leasequery-mismatch.md` — DHCP Option 82 + Leasequery mismatch
- `references/arista-debug-and-capture.md` — Arista packet capture and debug methods
- `references/arista-dhcp-dora-capture.md` — Real DHCP DORA capture
- `references/ip-conflict-docker-auth-block.md` — Docker IP conflict and auth block
- `references/s5731-command-quirks.md` — S5731-specific command quirks
- `references/pre-authen-stuck-artifacts.md` — Real session outputs from a Pre-authen stuck user
