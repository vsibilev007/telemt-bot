# Telemt Manager Bot

Telegram-бот для управления [Telemt MTProxy](https://github.com/telemt/telemt) через Control API v1.

## Возможности

- **Управление клиентами** — создание, редактирование, удаление, QR-коды, история трафика с графиками
- **Мониторинг** — дашборд, runtime, безопасность, DC/Writers, upstreams
- **Алерты** — 10 типов событий с настраиваемыми порогами и cooldown
- **Кластер HA** — write-операции на все узлы параллельно, агрегированное чтение
- **Мультисервер** — переключение между серверами и кластерами прямо из меню
- **Диагностика узлов** — DNS, TCP, SSH, Ping, MTProto проверки с агентами
- **Ссылки с SNI** — домены маскировки отображаются над каждым прокси
- **Редактирование конфига** — изменение настроек через бота (PATCH /v1/config)
- **Lite режим** — минимальный набор функций без алертов и графиков

---

## Требования

| Компонент | Версия | Обязательно |
|-----------|--------|-------------|
| Python | 3.11+ | Да |
| Telemt MTProxy | с Control API | Да |
| matplotlib | — | Для графиков |
| telethon + python-socks | — | Для MTProto-проверки прокси |

---

## Установка на свежей системе

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

### 3. Создать виртуальное окружение и установить зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Настроить конфигурацию

```bash
cp .env.example .env
nano .env
```

Заполни обязательные параметры:

```env
BOT_TOKEN=1234567890:AABBCCDDEEFFaabbccddeeff
ALLOWED_USERS=123456789
SERVER_URL=http://127.0.0.1:9091
SERVER_NAME=My Telemt
SERVER_AUTH=
```

> `BOT_TOKEN` — получить у [@BotFather](https://t.me/BotFather).
> `ALLOWED_USERS` — Telegram user_id через запятую. Узнать: [@userinfobot](https://t.me/userinfobot).
> `SERVER_URL` — адрес Control API Telemt (по умолчанию `127.0.0.1:9091`).

### 5. Запустить

```bash
source venv/bin/activate
python bot.py
```

Бот готов. Открой его в Telegram и нажми `/start`.

---

## Установка как systemd-сервис

### Бот

Создай файл `/etc/systemd/system/telemt-bot.service`:

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

> Замени `/opt/telemt-bot` на реальный путь к проекту.

```bash
systemctl daemon-reload
systemctl enable --now telemt-bot
journalctl -u telemt-bot -f
```

### Агент проверки прокси (опционально)

Агент нужен, если хочешь проверять доступность прокси с дополнительных серверов (RU, Asia и т.д.). Агент — отдельный скрипт `proxy_agent.py` без внешних зависимостей.

Скопируй `proxy_agent.py` на удалённый сервер и создай файл `/etc/systemd/system/proxy-agent.service`:

```ini
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
```

```bash
systemctl daemon-reload
systemctl enable --now proxy-agent
```

На основном сервере добавь в `.env`:

```env
AGENT_1_URL=http://IP_АГЕНТА:8765
AGENT_1_NAME=RU
AGENT_1_TOKEN=YOUR_TOKEN
AGENT_1_FLAG=🇷🇺
```

---

## Конфигурация (`.env`)

### Обязательные

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `ALLOWED_USERS` | Telegram user_id через запятую |

### Серверы

**Один сервер:**

```env
SERVER_URL=http://127.0.0.1:9091
SERVER_NAME=My Telemt
SERVER_AUTH=
```

**Несколько серверов:**

```env
SERVER_1_URL=http://10.0.0.1:9091
SERVER_1_NAME=Main
SERVER_1_AUTH=secret1

SERVER_2_URL=http://10.0.0.2:9091
SERVER_2_NAME=Backup
SERVER_2_AUTH=secret2
```

**Кластер HA** — серверы с одинаковым `GROUP`:

```env
SERVER_1_URL=http://10.0.0.1:9091
SERVER_1_NAME=HA_A
SERVER_1_GROUP=cluster_ha

SERVER_2_URL=http://10.0.0.2:9091
SERVER_2_NAME=HA_B
SERVER_2_GROUP=cluster_ha
```

### Прочие параметры

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `TZ` | Часовой пояс | системный |
| `LITE_MODE` | Минимальный режим | `false` |
| `LOG_LEVEL` | Уровень логов | `INFO` |
| `LOG_FILE` | Файл логов | — (stdout) |
| `LOG_MAX_MB` | Макс. размер файла | `10` |
| `LOG_BACKUPS` | Кол-во бэкапов | `3` |
| `NO_COLOR` | Отключить ANSI | — |
| `TELEMT_CONFIG_PATH` | Путь к telemt.toml | `/etc/telemt/telemt.toml` |
| `TELEGRAM_PROXY_URL` | Прокси для Telegram API | — |

### Пороги алертов

```env
ALERT_CONN_SPIKE_PCT=50        # всплеск соединений, %
ALERT_CONN_SPIKE_MIN_BASE=100  # мин. база для срабатывания
ALERT_WRITERS_LOW_PCT=80       # порог ME Writers coverage, %
ALERT_HS_TIMEOUT_SPIKE=50      # handshake timeout, +N за 2 мин
ALERT_BAD_CLIENT_SPIKE=100     # плохих TLS, +N за 2 мин
ALERT_QUOTA_PCT=80             # порог квоты клиента, %
```

### Прокси для Telegram API

```env
TELEGRAM_PROXY_URL=socks5://user:password@host:port
TELEGRAM_PROXY_URL=http://host:port
```

Поддержка SOCKS5, SOCKS4, HTTP. Логин/пароль скрывается в логах.

---

## Lite режим

`LITE_MODE=true` — минимальный набор без графиков и алертов:

| Остаётся | Отключается |
|----------|-------------|
| 🟢 Состояние сервера | 📊 Отчёт по трафику |
| 👥 Клиенты | ⚠️ Истекающие |
| ➕ Создание клиентов | 🔒 Безопасность, Upstreams, DC/Writers |
| ⚡ Runtime | 🔍 Проверка прокси |
| 📤 Бэкап | 🔔 Алерты и scheduler |

---

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и главное меню |
| `/menu` | Главное меню |
| `/help` | Справка |
| `/adduser имя [дней]` | Быстро создать клиента |
| `/find запрос` | Поиск клиента по имени |
| `/check tg://proxy?...` | Диагностика узла (DNS, TCP, SSH, Ping, MTProto) |
| `/alerts` | Настройки алертов |
| `/alert_log` | История последних 20 алертов |
| `/id` | Ваш Telegram ID |
| `/status` | Статус всех серверов |

---

## Алерты

| Тип | Событие | Cooldown |
|-----|---------|----------|
| `status_down` | Сервер недоступен | 5 мин |
| `status_up` | Сервер восстановился | — |
| `conn_spike` | Всплеск соединений >50% | 2 мин |
| `writers_low` | ME Writers coverage <80% | 2 мин |
| `version_change` | Обновление версии telemt | — |
| `bad_unknown_sni` | Неизвестный TLS SNI | 5 мин |
| `hs_timeout_spike` | Handshake timeout +50 за 2 мин | 2 мин |
| `bad_client_spike` | Плохих TLS клиентов +100 за 2 мин | 2 мин |
| `hs_conn_reset` | Сброс при handshake | 5 мин |
| `quota_warn` | Клиент использовал ≥80% квоты | 1 час |

Настройка через `/alerts`, история через `/alert_log`.

---

## Проверка MTProto прокси

Бот анализирует ссылки `tg://proxy?...` и `https://t.me/proxy?...`:

- Тип секрета: FakeTLS / DD / Simple
- SNI — домен маскировки (для FakeTLS)
- TCP + MTProto хэндшейк с EU-сервера
- TCP + TLS хэндшейк с агентов (RU и др.)

### Настройка агента

#### Шаг 1 — Скопировать `proxy_agent.py` на удалённый сервер

**Вариант A — Скачать из GitHub (самый простой):**

```bash
ssh root@IP_СЕРВЕРА
curl -o /opt/proxy_agent.py \
  https://raw.githubusercontent.com/vsibilev007/telemt-bot/main/proxy_agent.py
```

**Вариант B — Скопировать по SCP с основного сервера:**

```bash
scp /opt/telemt-bot/proxy_agent.py root@IP_СЕРВЕРА:/opt/proxy_agent.py
```

**Вариант C — Клонировать весь репозиторий:**

```bash
ssh root@IP_СЕРВЕРА
git clone https://github.com/vsibilev007/telemt-bot.git /opt/telemt-bot
# Агент будет: /opt/telemt-bot/proxy_agent.py
```

#### Шаг 2 — Проверить что работает

```bash
python3 /opt/proxy_agent.py --host 0.0.0.0 --port 8765 --token YOUR_TOKEN &

# В другом терминале:
curl "http://127.0.0.1:8765/health" -H "X-Token: YOUR_TOKEN"
# Ответ: {"status": "ok"}
```

#### Шаг 3 — Создать systemd-сервис

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

> Замени `0.0.0.0` на конкретный IP (например VPN-адрес `10.8.1.2`), если не нужно слушать все интерфейсы.

#### Шаг 4 — Настроить бота

Добавь в `.env` на основном сервере:

```env
AGENT_1_URL=http://IP_АГЕНТА:8765
AGENT_1_NAME=RU
AGENT_1_TOKEN=YOUR_TOKEN
AGENT_1_FLAG=🇷🇺
```

Перезапусти бота:

```bash
systemctl restart telemt-bot
```

При проверке прокси бот покажет результат с обеих точек:

```
📡 Доступность:
  🇪🇺 EU — TCP: 🟢 56 мс  |  MTProto: 🟢 3665 мс
  🇷🇺 RU — TCP: 🟢 4 мс   |  TLS: 🟢 185 мс
```

---

## Структура проекта

```
telemt-bot/
├── bot.py              # Точка входа
├── config.py           # Конфигурация из .env
├── handlers.py         # Обработчики команд и callback
├── keyboards.py        # Inline-клавиатуры
├── formatters.py       # HTML-форматирование ответов
├── charts.py           # Графики matplotlib
├── api_client.py       # HTTP-клиент + кластерные операции
├── database.py         # SQLite: трафик, алерты, сессии
├── scheduler.py        # Фоновые задачи и алерты
├── session.py          # Выбор сервера для пользователя
├── proxy_checker.py    # Проверка MTProto прокси
├── proxy_agent.py      # Агент проверки (только stdlib)
├── logging_setup.py    # Цветной вывод, ротация файла
├── tz.py               # Часовые пояса
├── middlewares.py      # Авторизация
├── states.py           # FSM состояния
├── sysinfo.py          # Системная информация (psutil)
├── qr_utils.py         # Генерация QR-кодов
├── export_toml.py      # Бэкап telemt.toml
├── export_utils.py     # Экспорт CSV/Excel
├── requirements.txt
├── pyproject.toml
├── .env.example
└── .gitignore
```

---

## Лицензия

MIT
