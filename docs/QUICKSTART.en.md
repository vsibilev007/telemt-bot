# Quick Start Guide

[🇷🇺 Инструкция по быстрому запуску](QUICKSTART.ru.md)

---

## Prerequisites

| Component | Version | Required |
|-----------|---------|----------|
| Python | 3.11+ | Yes |
| Telemt MTProxy | with Control API | Yes |

---

## Option 1: Docker (Recommended)

### 1. Download compose file

```bash
curl -O https://raw.githubusercontent.com/vsibilev007/telemt-bot/main/docker-compose.yml
```

### 2. Create configuration

```bash
cp .env.example .env
nano .env
```

Fill in the required variables:

```env
BOT_TOKEN=1234567890:AABBCCDDEEFFaabbccddeeff
ALLOWED_USERS=123456789
SERVER_URL=http://127.0.0.1:9091
SERVER_NAME=My Telemt
```

> `BOT_TOKEN` — get from [@BotFather](https://t.me/BotFather).
> `ALLOWED_USERS` — Telegram user_id, comma-separated. Get yours: [@userinfobot](https://t.me/userinfobot).
> `SERVER_URL` — Telemt Control API address (default: `127.0.0.1:9091`).

### 3. Start

```bash
docker compose up -d
```

### 4. Verify

```bash
docker compose logs -f
```

Open the bot in Telegram and press `/start`.

---

## Option 2: From Source

### 1. Install Python and dependencies

**Ubuntu / Debian:**
```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git
```

**CentOS / RHEL / AlmaLinux:**
```bash
sudo dnf install -y python3 python3-pip git
```

**Alpine:**
```bash
sudo apk add python3 py3-pip git
```

### 2. Clone repository

```bash
git clone https://github.com/vsibilev007/telemt-bot.git
cd telemt-bot
```

### 3. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure

```bash
cp .env.example .env
nano .env
```

### 5. Run

```bash
source venv/bin/activate
python bot.py
```

---

## Option 3: systemd Service

### Create service file

```bash
cat > /etc/systemd/system/telemt-bot.service << 'EOF'
[Unit]
Description=Telemt Manager Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/telemt-bot
EnvironmentFile=/opt/telemt-bot/.env
ExecStart=/opt/telemt-bot/venv/bin/python bot.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### Enable and start

```bash
systemctl daemon-reload
systemctl enable --now telemt-bot
journalctl -u telemt-bot -f
```

---

## Next Steps

- [Configuration Reference](CONFIGURATION.en.md) — all `.env` variables
- [Deployment Guide](DEPLOYMENT.en.md) — Docker hardening, backup, security
- [WEB Proxy Setup](WEB-PROXY.en.md) — WEB proxy mode (Telemt 3.5.5+)
- [Proxy Agent](PROXY-AGENT.en.md) — remote diagnostics agent
