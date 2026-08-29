# Инструкция по быстрому запуску

[🇬🇧 Quick Start Guide](QUICKSTART.en.md)

---

## Требования

| Компонент | Версия | Обязательно |
|-----------|--------|-------------|
| Python | 3.11+ | Да |
| Telemt MTProxy | с Control API | Да |

---

## Вариант 1: Docker (рекомендуется)

### 1. Скачать compose файл

```bash
curl -O https://raw.githubusercontent.com/vsibilev007/telemt-bot/main/docker-compose.yml
```

### 2. Создать конфигурацию

```bash
cp .env.example .env
nano .env
```

Заполните обязательные переменные:

```env
BOT_TOKEN=1234567890:AABBCCDDEEFFaabbccddeeff
ALLOWED_USERS=123456789
SERVER_URL=http://127.0.0.1:9091
SERVER_NAME=My Telemt
```

> `BOT_TOKEN` — получить у [@BotFather](https://t.me/BotFather).
> `ALLOWED_USERS` — Telegram user_id через запятую. Узнать: [@userinfobot](https://t.me/userinfobot).
> `SERVER_URL` — адрес Control API Telemt (по умолчанию `127.0.0.1:9091`).

### 3. Запустить

```bash
docker compose up -d
```

### 4. Проверить

```bash
docker compose logs -f
```

Откройте бота в Telegram и нажмите `/start`.

---

## Вариант 2: Из исходников

### 1. Установить Python и зависимости

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

### 2. Клонировать репозиторий

```bash
git clone https://github.com/vsibilev007/telemt-bot.git
cd telemt-bot
```

### 3. Создать виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Настроить

```bash
cp .env.example .env
nano .env
```

### 5. Запустить

```bash
source venv/bin/activate
python bot.py
```

---

## Вариант 3: systemd сервис

### Создать файл сервиса

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

### Включить и запустить

```bash
systemctl daemon-reload
systemctl enable --now telemt-bot
journalctl -u telemt-bot -f
```

---

## Дальнейшие шаги

- [Справочник конфигурации](CONFIGURATION.ru.md) — все переменные `.env`
- [Развёртывание](DEPLOYMENT.ru.md) — Docker hardening, бэкап, безопасность
- [WEB Proxy](WEB-PROXY.ru.md) — WEB proxy режим (Telemt 3.5.5+)
- [Агент проверки](PROXY-AGENT.ru.md) — удалённый агент диагностики
