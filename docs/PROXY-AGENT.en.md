# Proxy Agent Setup

[🇷🇺 Агент проверки прокси](PROXY-AGENT.ru.md)

---

## Overview

The proxy agent is a lightweight Python script (`proxy_agent.py`) that runs on remote servers to check proxy availability from different geographic locations. It uses only Python standard library — no external dependencies.

## How It Works

```
┌─────────────┐     HTTP      ┌─────────────┐     MTProto     ┌─────────────┐
│  Telegram    │ ──────────── │  Proxy Agent │ ─────────────── │   Telemt    │
│    Bot       │              │  (RU, EU..)  │                 │   Server    │
└─────────────┘              └─────────────┘                 └─────────────┘
```

The bot sends check requests to agents. Agents perform TCP, TLS, and MTProto checks and return results.

## Installation

### Step 1 — Copy agent to remote server

**Option A — Download from GitHub:**

```bash
ssh root@REMOTE_SERVER
curl -o /opt/proxy_agent.py \
  https://raw.githubusercontent.com/vsibilev007/telemt-bot/main/proxy_agent.py
```

**Option B — Copy via SCP:**

```bash
scp proxy_agent.py root@REMOTE_SERVER:/opt/proxy_agent.py
```

### Step 2 — Test

```bash
python3 /opt/proxy_agent.py --host 0.0.0.0 --port 8765 --token YOUR_TOKEN &

# In another terminal:
curl "http://127.0.0.1:8765/health" -H "X-Token: YOUR_TOKEN"
# Response: {"status": "ok"}
```

### Step 3 — Create systemd service

```bash
cat > /etc/systemd/system/proxy-agent.service << 'EOF'
[Unit]
Description=Proxy Check Agent
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /opt/proxy_agent.py --host 0.0.0.0 --port 8765 --token YOUR_TOKEN
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now proxy-agent
```

> Replace `0.0.0.0` with a specific IP (e.g., VPN address `10.8.1.2`) if you don't need to listen on all interfaces.

### Step 4 — Configure the bot

Add to `.env` on the main server:

```env
AGENT_1_URL=http://AGENT_IP:8765
AGENT_1_NAME=RU
AGENT_1_TOKEN=YOUR_TOKEN
AGENT_1_FLAG=🇷🇺
```

Restart the bot:

```bash
systemctl restart telemt-bot
```

## Agent Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/check` | GET | TCP + TLS check |
| `/check_full` | GET | TCP + TLS + GeoIP + stability |

### Check Parameters

| Parameter | Description |
|-----------|-------------|
| `host` | Proxy host |
| `port` | Proxy port |
| `secret` | Proxy secret |
| `sni` | SNI domain (optional) |

## Example Output

When checking a proxy, the bot shows results from all agents:

```
📡 Availability:
  🇪🇺 EU — TCP: 🟢 56 ms  |  MTProto: 🟢 3665 ms
  🇷🇺 RU — TCP: 🟢 4 ms   |  TLS: 🟢 185 ms
```

## Security

- Agent uses token-based authentication (`X-Token` header)
- Agent should be accessible only from the bot server
- Use firewall rules to restrict access

---

## See Also

- [Quick Start Guide](QUICKSTART.en.md)
- [Configuration Reference](CONFIGURATION.en.md)
- [Deployment Guide](DEPLOYMENT.en.md)
