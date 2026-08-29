# Развёртывание

[🇬🇧 Deployment Guide](DEPLOYMENT.en.md)

---

## Docker

### Быстрый старт

```bash
curl -O https://raw.githubusercontent.com/vsibilev007/telemt-bot/main/docker-compose.yml
cp .env.example .env && nano .env
docker compose up -d
```

### Теги образов

| Тег | Описание |
|-----|----------|
| `latest` | Последний коммит в `main` |
| `v1.2.3` | Конкретная версия |
| `1.2` | Последний патч в мажоре |
| `sha-abc1234` | Конкретный коммит |

### Том данных

База данных хранится в named volume `telemt-data` (путь внутри контейнера — `/data`).

**Не используйте bind-mount** (`./data:/data`) — это перетирает права `appuser` и вызывает `unable to open database file`.

```bash
# Посмотреть данные
docker volume inspect telemt-data

# Бэкап тома
docker run --rm -v telemt-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/telemt-data.tar.gz -C /data .
```

### Бэкап конфигурации (telemt.toml)

Кнопка **📤 Бэкап** в меню бота отправляет файл `telemt.toml` прямо в чат. Контейнер не видит хостовый `/etc/telemt/telemt.toml` — нужно явно смонтировать файл.

**Шаг 1 — выставить права на хосте:**

```bash
chown 10001 /etc/telemt/telemt.toml
chmod 640 /etc/telemt/telemt.toml
```

Контейнер запускается как `appuser` (UID 10001) — файл должен быть ему доступен для чтения.

**Шаг 2 — раскомментировать mount в `docker-compose.yml`:**

```yaml
volumes:
  - telemt-data:/data
  - /etc/telemt/telemt.toml:/etc/telemt/telemt.toml:ro  # ← раскомментировать
```

Если `telemt.toml` лежит в другом месте:

```env
TELEMT_CONFIG_PATH=/path/to/telemt.toml
```

```yaml
- /path/to/telemt.toml:/etc/telemt/telemt.toml:ro
```

> **Альтернатива без изменения владельца:** используй POSIX ACL (требует пакет `acl`):
> ```bash
> setfacl -m u:10001:r /etc/telemt/telemt.toml
> ```

### Локальная сборка

```bash
docker build -t telemt-bot .
docker run -d --env-file .env -v telemt-data:/data --name telemt-bot telemt-bot
```

### Параметры безопасности (включены в compose)

- `read_only: true` — файловая система контейнера только для чтения
- `cap_drop: ALL` — сброс всех Linux capabilities
- `no-new-privileges: true` — запрет эскалации привилегий
- `mem_limit: 256m`, `pids_limit: 256` — лимиты ресурсов
- Non-root пользователь `appuser` (UID 10001)

---

## systemd сервис

### Сервис бота

Создайте файл `/etc/systemd/system/telemt-bot.service`:

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

## См. также

- [Инструкция по быстрому запуску](QUICKSTART.ru.md)
- [Справочник конфигурации](CONFIGURATION.ru.md)
- [WEB Proxy](WEB-PROXY.ru.md)
