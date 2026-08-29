# WEB Proxy Setup

[🇷🇺 WEB Proxy](WEB-PROXY.ru.md)

---

## Overview

WEB Proxy mode proxies MTProto traffic through HTTPS/WebSocket, compatible with the `WEB` proxy type in Telegram Desktop. Available in Telemt 3.5.5+.

## Features

| Feature | Description |
|---------|-------------|
| **Status** | Lifecycle, runtime, limits, streams, sessions, learning, debug |
| **Sessions** | List active WEB sessions with pagination and details |
| **Management** | Close sessions, clear debug, reset carrier learning |
| **Links** | Auto-generate `tg://webproxy` links for users |
| **Auto-Profiles** | WEB profile auto-added/removed on user create/delete |

## Bot Menu

| Button | Description |
|--------|-------------|
| 📊 Status | WEB runtime lifecycle, limits, streams, sessions |
| 👥 Sessions | List active sessions with filters |
| 🧹 Clear debug | Clear debug records |
| 🔄 Reset learning | Reset carrier learning evidence |

## Link Generation

For servers with Telemt 3.5.5+, the bot generates WEB links:

```
WEB Proxy:
🌐 list.lympik.ru
tg://webproxy?server=list.lympik.ru&secret=dd...
```

For servers with Telemt 3.4.25 and below — only TLS links (legacy format).

## Version Check

The bot automatically detects the Telemt version and shows appropriate links:

| Telemt Version | Links Shown |
|----------------|-------------|
| 3.5.5+ | WEB Proxy + MTProxy |
| 3.4.25 and below | MTProxy only |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /v1/runtime/web/status` | WEB runtime lifecycle and status |
| `GET /v1/runtime/web/sessions` | List active sessions |
| `GET /v1/runtime/web/sessions/{ref}` | Session details |
| `POST /v1/runtime/web/sessions/close` | Close sessions |
| `POST /v1/runtime/web/debug/clear` | Clear debug |
| `POST /v1/runtime/web/carrier-learning/reset` | Reset carrier learning |

## Telemt Configuration

### Minimal WEB Config

```toml
[general.links]
show = ["web-user"]
public_host = "proxy.example.com"
public_port = 443

[[server.listeners]]
ip = "127.0.0.1"
port = 18080
transport = "web"

[web]
enabled = true
carrier = "https"

[[web.vhosts]]
host = "proxy.example.com"
public_addr = "203.0.113.10:443"

[web.vhosts.decoy]
mode = "http_upstream"
upstream = "http://127.0.0.1:18081"

[[web.vhosts.profiles]]
user = "web-user"
secret_mode = "dd"
max_sessions = 8
max_streams = 512
max_streams_per_session = 64
```

### NGINX TLS Termination

```nginx
map $http_upgrade $telemt_connection_upgrade {
    default upgrade;
    ''      '';
}

upstream telemt_web {
    server 127.0.0.1:18080;
    keepalive 64;
}

server {
    listen 443 ssl;
    http2 on;
    server_name proxy.example.com;
    access_log off;

    ssl_certificate     /etc/letsencrypt/live/proxy.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/proxy.example.com/privkey.pem;

    client_max_body_size 2m;

    location / {
        proxy_pass http://telemt_web;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $telemt_connection_upgrade;

        proxy_connect_timeout 5s;
        proxy_send_timeout 65s;
        proxy_read_timeout 65s;
        proxy_request_buffering off;
        proxy_buffering off;
        proxy_next_upstream off;
    }
}
```

---

## See Also

- [Quick Start Guide](QUICKSTART.en.md)
- [Configuration Reference](CONFIGURATION.en.md)
- [Deployment Guide](DEPLOYMENT.en.md)
