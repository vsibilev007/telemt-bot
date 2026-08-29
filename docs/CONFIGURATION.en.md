# Configuration Reference

[🇷🇺 Справочник конфигурации](CONFIGURATION.ru.md)

---

## Required Variables

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `ALLOWED_USERS` | Telegram user_id list, comma-separated |

---

## Server Configuration

### Single Server

```env
SERVER_URL=http://127.0.0.1:9091
SERVER_NAME=My Telemt
SERVER_AUTH=
```

### Multiple Servers

```env
SERVER_1_URL=http://10.0.0.1:9091
SERVER_1_NAME=Main
SERVER_1_AUTH=secret1

SERVER_2_URL=http://10.0.0.2:9091
SERVER_2_NAME=Backup
SERVER_2_AUTH=secret2
```

### HA Cluster

Servers with the same `GROUP` form a cluster. Write operations execute on all nodes in parallel; reads use the first available.

```env
SERVER_1_URL=http://10.0.0.1:9091
SERVER_1_NAME=HA_A
SERVER_1_GROUP=cluster_ha

SERVER_2_URL=http://10.0.0.2:9091
SERVER_2_NAME=HA_B
SERVER_2_GROUP=cluster_ha
```

---

## General Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `TZ` | Timezone | System |
| `LITE_MODE` | Minimal mode without alerts/charts | `false` |
| `LOG_LEVEL` | Log level | `INFO` |
| `LOG_FILE` | Log file path | stdout |
| `LOG_MAX_MB` | Max log file size | `10` |
| `LOG_BACKUPS` | Number of backups | `3` |
| `NO_COLOR` | Disable ANSI colors | — |
| `TELEMT_CONFIG_PATH` | Path to telemt.toml | `/etc/telemt/telemt.toml` |

---

## Alert Thresholds

| Variable | Description | Default |
|----------|-------------|---------|
| `ALERT_CONN_SPIKE_PCT` | Connection spike threshold, % | `50` |
| `ALERT_CONN_SPIKE_MIN_BASE` | Minimum base for spike detection | `100` |
| `ALERT_WRITERS_LOW_PCT` | ME Writers coverage threshold, % | `80` |
| `ALERT_HS_TIMEOUT_SPIKE` | Handshake timeout spike, +N per 2 min | `50` |
| `ALERT_BAD_CLIENT_SPIKE` | Bad TLS clients spike, +N per 2 min | `100` |
| `ALERT_QUOTA_PCT` | Client quota warning threshold, % | `80` |

---

## Telegram API Proxy

```env
# SOCKS5
TELEGRAM_PROXY_URL=socks5://user:password@host:port

# HTTP proxy
TELEGRAM_PROXY_URL=http://host:port
```

Supports SOCKS5, SOCKS4, HTTP. Credentials are masked in logs.

---

## Proxy Agent Configuration

```env
AGENT_1_URL=http://agent-ip:8765
AGENT_1_NAME=RU
AGENT_1_TOKEN=your-secret-token
AGENT_1_FLAG=🇷🇺

# Multiple agents
AGENT_2_URL=http://agent2-ip:8765
AGENT_2_NAME=Asia
AGENT_2_TOKEN=another-token
AGENT_2_FLAG=🇨🇳
```

---

## Example .env

```env
# Required
BOT_TOKEN=1234567890:AABBCCDDEEFFaabbccddeeff
ALLOWED_USERS=123456789,987654321

# Server
SERVER_URL=http://127.0.0.1:9091
SERVER_NAME=My Telemt
SERVER_AUTH=

# Optional
TZ=Europe/Moscow
LITE_MODE=false
LOG_LEVEL=INFO

# Alert thresholds
ALERT_CONN_SPIKE_PCT=50
ALERT_WRITERS_LOW_PCT=80
```

---

## See Also

- [Quick Start Guide](QUICKSTART.en.md)
- [Deployment Guide](DEPLOYMENT.en.md)
- [WEB Proxy Setup](WEB-PROXY.en.md)
