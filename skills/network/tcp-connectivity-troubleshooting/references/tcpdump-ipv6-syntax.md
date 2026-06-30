# tcpdump IPv6 Filter Syntax Quick Reference

## Basic combinations

| Expression | Meaning | Valid? |
|------------|---------|--------|
| `port 443` | Any packet with src or dst port 443 | ✅ |
| `host fd00::1` | Any packet to/from that IPv6 address | ✅ |
| `port 443 and host fd00::1` | Both conditions | ✅ |
| `dst port 443 and src host fd00::1` | Client → Server on 443 | ✅ |
| `src port 443 and dst host fd00::1` | Server → Client on 443 | ✅ |
| `port 443 host fd00::1` | **SYNTAX ERROR** ❌ | ❌ |

## Keyword order matters

- ✅ `port X and host Y` — correct
- ✅ `dst port X and src host Y` — correct, directional
- ❌ `port X host Y` — parser can't tell which modifier belongs to what

## Common debugging patterns

```bash
# SYN packets only (new connection attempts)
tcpdump -i any 'tcp[tcpflags] & tcp-syn != 0' and dst port 443 -nn

# SYN + SYN-ACK (handshake check)
tcpdump -i any port 443 and host fd00::1 -nn

# IPv6 only (exclude IPv4 noise)
tcpdump -i any ip6 and port 443 -nn

# With interface
tcpdump -i eth0 dst host fd00::1 and dst port 443 -nn
```

## Useful flags

| Flag | Meaning |
|------|---------|
| `-nn` | No name resolution (faster, clearer) |
| `-e` | Show MAC addresses (identify L2 hops) |
| `-v` | Verbose (TTL, flags, options) |
| `-X` | Hex + ASCII dump (full packet content) |
| `-c 10` | Stop after 10 packets |
