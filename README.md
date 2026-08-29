# Telemt Manager Bot

[![Docker](https://github.com/vsibilev007/telemt-bot/actions/workflows/docker.yml/badge.svg)](https://github.com/vsibilev007/telemt-bot/actions/workflows/docker.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Telegram bot for managing [Telemt MTProxy](https://github.com/telemt/telemt) servers via Control API v1.

**Compatibility:** Telemt 3.4.14 — 3.5.5+

[🇷🇺 README на русском](README.ru.md)

---

## Quick Start

```bash
# One-line Docker setup
curl -O https://raw.githubusercontent.com/vsibilev007/telemt-bot/main/docker-compose.yml
cp .env.example .env && nano .env
docker compose up -d
```

- [Quick Start Guide](docs/QUICKSTART.en.md)
- [Инструкция по быстрому запуску](docs/QUICKSTART.ru.md)

---

## Features

| Category | Capabilities |
|----------|-------------|
| **Client Management** | Create, edit, delete users; QR codes; traffic history with charts |
| **Monitoring** | Dashboard, runtime, security, DC/Writers, upstreams |
| **Alerts** | 10 event types with configurable thresholds and cooldowns |
| **HA Cluster** | Parallel write operations across nodes, aggregated reads |
| **Multi-Server** | Switch between servers and clusters from the menu |
| **Node Diagnostics** | DNS, TCP, SSH, Ping, MTProto checks with remote agents |
| **WEB Proxy** | Status, sessions, debug, carrier learning management (Telemt 3.5.5+) |
| **Config Editor** | Modify server settings via bot (PATCH /v1/config) |
| **Runtime Reload** | Reload configuration without process restart (Telemt 3.4.25+) |
| **Lite Mode** | Minimal feature set without alerts and charts |

---

## Documentation

- [Quick Start Guide](docs/QUICKSTART.en.md)
- [Configuration Reference](docs/CONFIGURATION.en.md)
- [Deployment Guide](docs/DEPLOYMENT.en.md)
- [WEB Proxy Setup](docs/WEB-PROXY.en.md)
- [Proxy Agent Setup](docs/PROXY-AGENT.en.md)

---

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome and main menu |
| `/menu` | Main menu |
| `/help` | Help |
| `/adduser name [days]` | Quick create client |
| `/find query` | Search client by name |
| `/check tg://proxy?...` | Node diagnostics |
| `/reload [instant\|drain]` | Runtime reload (3.4.25+) |
| `/alerts` | Alert settings |
| `/id` | Your Telegram ID |

---

## Docker Images

```bash
docker pull ghcr.io/vsibilev007/telemt-bot:latest
```

| Tag | Description |
|-----|-------------|
| `latest` | Latest commit on `main` |
| `v1.2.3` | Specific version |
| `sha-abc1234` | Specific commit |

---

## Project Structure

```
telemt-bot/
├── bot.py              # Entry point
├── config.py           # Configuration from .env
├── handlers.py         # Command and callback handlers
├── keyboards.py        # Inline keyboards
├── formatters.py       # HTML response formatting
├── api_client.py       # HTTP client + cluster operations
├── database.py         # SQLite: traffic, alerts, sessions
├── scheduler.py        # Background tasks and alerts
├── proxy_checker.py    # MTProto proxy verification
├── proxy_agent.py      # Remote check agent (stdlib only)
├── docs/               # Detailed documentation
└── docker-compose.yml  # Docker Compose configuration
```

---

## Support

If you find this project helpful, consider supporting its development:

**USDT (TON):**
```
UQDly-HkY2hukMN8d1O6epG5PliTbxmlKyjt_7Mrn-gN93Fv
```

---

## License

[MIT](LICENSE)
