# Huawei `display poe power interface` Output Interpretation

## Command

```
display poe power interface <interface>
```

## Key Fields

| Field | Meaning | Diagnostic Value |
|-------|---------|-----------------|
| PD power | Current power draw (mW) | Real-time consumption |
| PD class | PD classification (0-8) | Maps to 802.3 standard |
| PD reference power | Reference power for this class (mW) | Expected max per standard |
| User set max power | Configured max (mW) | Admin limit |
| PD peak power | Peak observed (mW) | Burst demand |
| PD average power | Average observed (mW) | Sustained demand |

## PD Class → Standard Mapping

| Class | Standard | Max Power | Typical AP |
|-------|----------|-----------|------------|
| 0-3 | 802.3af (15.4W) | 13W | AP-303/303H |
| 4 | 802.3at / PoE+ (30W) | 25.5W | AP-515/535 (limited) |
| 5 | 802.3bt Type 3 (60W) | 51W | AP-555 (full) |
| 6 | 802.3bt Type 4 (90W) | 71W | AP-577/587 |

## Power Consumption State Interpretation

### Normal Boot Sequence (AP-5xx)

```
Snapshot 1:  ~4,200 mW  →  early boot (base system only)
Snapshot 2:  ~8,100 mW  →  radios initializing
Snapshot 3:  ~7,500 mW  →  radios on, idle
Full load:  15,000-35,000 mW → all radios under client load
```

Expected ramp-up: 4W → 8W → 15-35W over 2-5 minutes.

### Anomaly Patterns

| Pattern | Interpretation |
|---------|---------------|
| Stuck at 4-8W > 5 min | AP in reboot loop or discovery loop (can't reach WAC / get IP) |
| Stable at 4-8W indefinitely | Radios disabled or AP in low-power standby |
| Fluctuating 4-8W ↔ 15W+ | Intermittent radio state change (possible DFS events) |
| Consistently near PD reference power | AP running at full capacity (normal under load) |

## Cross-Reference with Port State

```
display interface <interface>
```

| Port State | PoE State | Root Cause |
|-----------|-----------|------------|
| UP | Delivering power | Link OK — check AP side |
| UP | No power | AP powered by DC adapter or different source |
| DOWN | Delivering power | Data pairs broken — PoE and data link negotiate independently |
| DOWN | No power | Switch PoE fault / budget exhausted / port disabled |
| UP | Delivering, but power < expected | Cable too long / poor quality / only 2-pair connected |

## Quick Diagnosis Flow

1. `display poe power interface <port>` → check PD class matches AP model
2. `display poe power` → check total budget remaining
3. If class correct but power < 15W after 5 min → AP likely stuck
4. If class wrong (e.g. class 4 on AP-555) → switch doesn't support 802.3bt, or LLDP power negotiation failed
5. Cross-check: `display interface <port>` + `display mac-address interface <port>`
