# IP Address Conflict Blocking Authentication (Docker Case)

Discovered on S5731 with `dot1x-mac-bypass` combined auth profile. Full case
documentation: `dot1x_mab_preauth_troubleshooting.md` (Obsidian vault:
From Agent/).

## Symptom
- MAC stuck in Pre-authen indefinitely — session keeps recreating (User ID changes)
- `dis access-user` shows:
  ```
  User authentication type: No authentication   ← auth hasn't started
  Domain-name: -                                  ← domain not assigned
  User vlan event: Pre-authen
  ```
- DHCP works (client gets 100.80.170.x subnet) but can't reach gateway
- Port shows frequent link flaps (down/up within seconds)
- `dis aaa online-fail-record mac-address XXXX-XXXX-XXXX` shows:
  ```
  User online fail reason: IP address conflict
  Conflict IP address: 172.17.0.1
  ```

## Dual-Mechanism: Why the MAC Can Never Authenticate

Docker on the client causes TWO independent blocking mechanisms:

### Mechanism A: IP Conflict (blocks MAB after RADIUS accepts)

```
Ubuntu (port 47)                       Wangjing (port 48)
  docker0: 172.17.0.1                     IP: 172.17.0.1
  MAC: 5081-402d-b9ac                     MAC: 1c69-7a63-7886
       │                                        │
       ├── Docker container traffic ──→          │
       │    source MAC = physical NIC MAC         │
       │    source IP  = 172.17.0.1              │
       │    (via docker0 bridge → SNAT → eth0)   │
       │                                        │
       ▼                                        │
  Switch's auth module detects:
  - MAC on port 47 claims IP 172.17.0.1
  - But port 48 user already holds 172.17.0.1
  → IP CONFLICT → Reject authentication
  → Record in online-fail-record
  → User stays Pre-authen
```

**Key insight**: This IP conflict detection is NOT an RFC standard. RADIUS (RFC 2865)
only cares about username/MAC/password — it does NOT validate client IP.
This is a Huawei switch LOCAL security feature, checked after RADIUS returns
Access-Accept but before the user is allowed online.

Vendor comparison:
| Vendor | Feature | Behavior |
|--------|---------|----------|
| **Huawei** | Auth module IP conflict check (default on) | Reject new user |
| **Cisco** | `ip device tracking` + `ip source guard` | Filter by DHCP snooping |
| **H3C** | `user-ip-conflict check enable` | Configurable action |
| **Juniper** | `arp-inspection` | ARP-based filtering |

### Mechanism B: Link Flap (prevents MAB from even triggering)

Docker's network stack operations (creating docker0 bridge, modifying iptables/nftables
rules, adding routes) trigger NetworkManager on Ubuntu to detect "network changes"
and reset the physical interface. This causes the switch port to flap (link down/up).

MAB bypass timing in a dot1x-mac-bypass setup:
```
dot1x Tx Period (30s) × 2 retries + MAC Bypass Delay (30s)
= ~90s before MAB RADIUS request is sent
```

If the link flaps more frequently than every ~90s, the auth timer resets each time
and MAB never triggers. The port in our case flapped with only **5 seconds** between
down and up — impossible for MAB to ever start.

### Double Lock: Why Neither Path Works

```
Docker on Ubuntu
    ├── docker0 BIP 172.17.0.1 → Mechanism A: IP Conflict
    │     (blocks MAB even if RADIUS accepts)
    └── network stack changes  → Mechanism B: Link Flap
          (blocks MAB from ever starting)
```

MAB either never starts (flap keeps resetting) OR starts but gets blocked by IP
conflict. The user cannot authenticate through either path.

## Detection Commands

### First-Tier (run these FIRST for any Pre-authen investigation)

```bash
# 1. Check user state
dis access-user mac-address XXXX-XXXX-XXXX

# 2. Check WHY auth failed ← THIS IS THE KEY COMMAND
dis aaa online-fail-record mac-address XXXX-XXXX-XXXX
```

### Second-Tier (after finding IP conflict)

```bash
# 3. Find who holds the conflicting IP
dis access-user | include <conflict-ip>

# 4. Check link stability
dis interface GigabitEthernet 0/0/<n> | include Last|flap
```

### On the Client

```bash
# Check Docker bridge IP
ip addr show docker0

# Check Docker containers
docker ps
docker network inspect bridge
```

## Resolution Options

### Immediate Fix (change Docker bridge IP)
Edit `/etc/docker/daemon.json`:
```json
{ "bip": "172.28.0.1/24" }
```
Then restart Docker:
```bash
sudo systemctl restart docker
```

### Verify
1. `ip addr show docker0` — confirm new BIP
2. Monitor switch port stability: `dis interface GigabitEthernet 0/0/<n>` — no more flaps
3. Check MAC auth success: `dis access-user mac-address XXXX-XXXX-XXXX`
4. If still stuck, `reset access-user mac-address XXXX-XXXX-XXXX` or shut/no shut the port

### Long-Term Prevention
1. **Plan Docker bridge subnets** across the team — avoid default 172.17.0.0/16
2. **RADIUS server side**: if RDAUTHDOWN is frequent, check service stability
3. **Switch side**: configure IP conflict to warn-only (VRP version dependent)
