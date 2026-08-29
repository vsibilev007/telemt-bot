# Deployment Guide

[🇷🇺 Развёртывание](DEPLOYMENT.ru.md)

---

## Docker

### Quick Start

```bash
curl -O https://raw.githubusercontent.com/vsibilev007/telemt-bot/main/docker-compose.yml
cp .env.example .env && nano .env
docker compose up -d
```

### Image Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest commit on `main` |
| `v1.2.3` | Specific version |
| `1.2` | Latest patch in major |
| `sha-abc1234` | Specific commit |

### Data Volume

Database is stored in named volume `telemt-data` (path inside container: `/data`).

**Do NOT use bind-mount** (`./data:/data`) — it overrides `appuser` permissions and causes `unable to open database file`.

```bash
# Inspect data
docker volume inspect telemt-data

# Backup volume
docker run --rm -v telemt-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/telemt-data.tar.gz -C /data .
```

### Config Backup (telemt.toml)

The **📤 Backup** button in the bot menu sends `telemt.toml` directly to chat. The container cannot see host's `/etc/telemt/telemt.toml` — you must mount it explicitly.

**Step 1 — Set permissions on host:**

```bash
chown 10001 /etc/telemt/telemt.toml
chmod 640 /etc/telemt/telemt.toml
```

The container runs as `appuser` (UID 10001) — the file must be readable by this user.

**Step 2 — Uncomment mount in `docker-compose.yml`:**

```yaml
volumes:
  - telemt-data:/data
  - /etc/telemt/telemt.toml:/etc/telemt/telemt.toml:ro  # ← uncomment
```

If `telemt.toml` is in a different location:

```env
TELEMT_CONFIG_PATH=/path/to/telemt.toml
```

```yaml
- /path/to/telemt.toml:/etc/telemt/telemt.toml:ro
```

> **Alternative without changing owner:** use POSIX ACL (requires `acl` package):
> ```bash
> setfacl -m u:10001:r /etc/telemt/telemt.toml
> ```

### Local Build

```bash
docker build -t telemt-bot .
docker run -d --env-file .env -v telemt-data:/data --name telemt-bot telemt-bot
```

### Security Hardening (included in compose)

- `read_only: true` — read-only filesystem
- `cap_drop: ALL` — drop all Linux capabilities
- `no-new-privileges: true` — prevent privilege escalation
- `mem_limit: 256m`, `pids_limit: 256` — resource limits
- Non-root user `appuser` (UID 10001)

---

## systemd Service

### Bot Service

Create `/etc/systemd/system/telemt-bot.service`:

```ini
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
```

```bash
systemctl daemon-reload
systemctl enable --now telemt-bot
journalctl -u telemt-bot -f
```

---

## See Also

- [Quick Start Guide](QUICKSTART.en.md)
- [Configuration Reference](CONFIGURATION.en.md)
- [WEB Proxy Setup](WEB-PROXY.en.md)
