# S5731 VRP8 Command Quirks

Tested on CNSHA45-F11-A-S5731-ASW02. These commands behave differently
from what you'd expect on other Huawei models or documentation.

## Commands that DON'T work

| Command | Error | Workaround |
|---------|-------|------------|
| `dis radius-server statistics` | Unrecognized | Not available on this version |
| `dis radius-server statistics template X` | Unrecognized | Not available |
| `dis radius-client statistics` | Unrecognized | Not available |
| `dis mac-access-profile name X` | Unrecognized | Use `dis current-configuration \| begin mac-access-profile` |
| `dis dot1x-access-profile name X` | Unrecognized | Use `dis current-configuration \| begin dot1x-access-profile` |
| `dis access-profile name X` | Unrecognized | See workarounds above |
| `dis aaa statistics` | Incomplete command | Try `dis aaa online-fail-record` or `dis aaa abnormal-offline-record` |
| `dis radius-server active 1812` | Unrecognized | Use `dis radius-server configuration` |
| `reset access-user mac-address X` | Unrecognized | Try `cut access-user` or port bounce |
| `dis dot1x statistics interface X` | Too many parameters | Use `dis dot1x interface X` |

## Commands that DO work

| Command | Notes |
|---------|-------|
| `dis current-configuration \| begin <keyword>` | Works for config blocks |
| `dis current-configuration \| include <pattern>` | Works but only shows matching lines, not full blocks |
| `dis current-configuration \| section <keyword>` | Does NOT work on this version |
| `dis current-configuration interface X` | Works for single interface |
| `dis aaa online-fail-record mac-address X` | Critical for finding auth failure reasons |
| `dis aaa abnormal-offline-record all` | Needs Y/N confirmation; shows offline reasons |
| `dis logbuffer \| include <pattern>` | Works but 343K+ overwritten messages; recent events only |
| `dis logbuffer \| tail 30` | Does NOT work; `tail` unsupported |
| `ping -s <size> -f -c 3 <ip>` | Path MTU testing works correctly |

## Session-specific: 100.80.130.82 details

- Model: S5731 (ASW02 — access switch)
- Auth profile: `dot1xmac_authen_profile` (dot1x → MAB bypass)
- RADIUS template: `radius_for_dot1xmac`
  - Primary: 10.0.77.9:1812 (weight 100)
  - Backup: 10.71.246.9:1812 (weight 80)
- Domain: `dot1xmac.bytedance.com`
- Escape VLAN: 300 (Guest) on RADIUS-down
- Pre-auth access: disabled (`undo authentication pre-authen-access enable`)
