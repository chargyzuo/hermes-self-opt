# Common Server Software IPv6 Binding Configuration

## Nginx

```nginx
# IPv4 + IPv6 dual stack
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    ...
}
```

Or force IPv6 only:
```nginx
listen [::]:443 ssl ipv6only=on;
```

## Apache

```apache
# Dual stack
Listen 443
Listen [::]:443
```

Or in VirtualHost:
```apache
<VirtualHost *:443 [::]:443>
    ...
</VirtualHost>
```

## Python http.server

```bash
# Python 3.8+
python3 -m http.server 443 --bind ::

# Python 3.7 (workaround)
python3 -c "
import socketserver, http.server
s = socketserver.TCPServer(('::', 443), http.server.SimpleHTTPRequestHandler)
s.serve_forever()
"
```

## socat

```bash
# IPv6 only
socat TCP6-LISTEN:443,reuseaddr,fork -

# IPv6 → IPv4 relay
socat TCP6-LISTEN:443,reuseaddr,fork TCP4:127.0.0.1:443
```

## netcat

```bash
# Traditional nc
nc -6 -l -p 443

# ncat (nmap)
ncat -6 -l 443 --keep-open
```

## SSH

```bash
# /etc/ssh/sshd_config
ListenAddress ::
```

## Verify IPv6 listening

```bash
ss -tlnp | grep ':443\b'
# Should see: LISTEN [::]:443

# Explicit IPv6 socket check
ss -tlnp -6 | grep :443
```
