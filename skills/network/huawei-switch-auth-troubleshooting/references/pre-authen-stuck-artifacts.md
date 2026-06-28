# Session Artifacts: Pre-authen Stuck User (2026-06-23)

## Device
CNSHA45-F11-A-S5731-ASW02 (100.80.130.82), Huawei S5731 VRP8

## Problem MAC
5081-402d-b9ac, VLAN 200, GE0/0/47

## Key Outputs

### User State (Pre-authen, No Authentication)

```
Basic:
  User ID                         : 1566
  Domain-name                     : -
  User MAC                        : 5081-402d-b9ac
  User IP address                 : 100.80.170.54
  User access Interface           : GigabitEthernet0/0/47
  User vlan event                 : Pre-authen
  QinQVlan/UserVlan               : 0/200
  User access time                : 2026/06/23 19:51:21
  User access type                : None
  Terminal Device Type            : Data Terminal

AAA:
  User authentication type        : No authentication
  Current authentication method   : None
  Current authorization method    : Local
  Current accounting method       : None
```

Note the indicators: Domain-name "-", "No authentication", "Pre-authen" — all signs that auth hasn't started.

### Authentication Profile Block

```
authentication-profile name dot1xmac_authen_profile
 dot1x-access-profile dot1x_access_profile
 mac-access-profile mac_access_profile
 access-domain dot1xmac.bytedance.com force
 authentication event authen-server-down action authorize service-scheme escape_vlan
 authentication event authen-server-up action re-authen
 authentication dot1x-mac-bypass
```

### RADIUS Template

```
Server-template-name: radius_for_dot1xmac
Timeout-interval: 2s
Retransmission: 5
Dead time: 5 min
Detect-interval: 60s
Detect timeout: 3s
Detect up-server: 0s
Server algorithm: master-backup based-user
Auth Server 1: 10.0.77.9:1812 weight 100 [up]
Auth Server 2: 10.71.246.9:1812 weight 80 [up]
Domain-included: YES
```

Special config: `radius-attribute set Service-Type 10 auth-type mac`

### RDAUTHDOWN Logs (truncated — 343281 overwritten messages)

```
Jun 23 2026 19:50:25 RDS/4/RDAUTHDOWN: RADIUS auth server 10.0.77.9 interrupted!
Jun 23 2026 19:21:55 RDS/4/RDAUTHDOWN: RADIUS auth server 10.0.77.9 interrupted!
Jun 23 2026 19:12:20 RDS/4/RDAUTHDOWN: RADIUS auth server 10.0.77.9 interrupted!
Jun 23 2026 18:36:54 RDS/4/RDAUTHDOWN: RADIUS auth server 10.0.77.9 interrupted!
...
Jun 12 2026 21:29:58 RDS/4/RDAUTHDOWN: RADIUS auth server 10.0.77.9 interrupted!
```

NO RDAUTHUP logs found — server never detected as recovered.

### Service Scheme (Escape VLAN)

```
service-scheme escape_vlan
 user-vlan 300
```

VLAN 300 = Guest VLAN.

### Dot1x Global Parameters

```
Quiet Period: 60s, Quiet-times: 10
Tx Period: 30s, Mac-By-Pass Delay: 30s
```

Dot1x phase: 30s × 2 retries = 60s max, then 30s bypass delay = ~90s before MAC auth.

## Root Cause Summary

1. RADIUS server 10.0.77.9 had ongoing intermittent failures (RDAUTHDOWN spanning weeks)
2. No RDAUTHUP events — server never confirmed recovered
3. User connected during a RADIUS outage window
4. With pre-authen access disabled and detect interval at 60s, users get stuck in Pre-authen
5. "Ping works but RADIUS fails" = UDP 1812/1813 application-layer issue, not network reachability
