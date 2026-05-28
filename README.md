# Telemt Manager Bot

Telegram-бот для управления [Telemt MTProxy](https://github.com/telemt/telemt) через Control API v1.

## Возможности

- **Управление клиентами** — создание, редактирование, удаление, QR-коды, история трафика с графиками
- **Мониторинг** — дашборд, runtime, безопасность, DC/Writers, upstreams
- **Алерты** — 10 типов событий с настраиваемыми порогами и cooldown
- **Кластер HA** — write-операции на все узлы параллельно, агрегированное чтение
- **Мультисервер** — переключение между серверами и кластерами прямо из меню
- **Проверка прокси** — анализ MTProto-ссылок с нескольких точек (EU, RU и др.)
- **Lite режим** — минимальный набор функций без алертов и графиков

## Требования

- Python 3.11+
- [Telemt MTProxy](https://github.com/telemt/telemt) с включённым Control API (`api_addr = "127.0.0.1:9091"`)
- `matplotlib` — для графиков трафика *(опционально)*
- `telethon` + `python-socks` — для MTProto-проверки прокси *(опционально)*

## Быстрый старт

```bash
git clone https://github.com/vsibilev007/telemt-bot.git
cd telemt-bot

# Установка зависимостей
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Конфигурация
cp .env.example .env
nano .env

# Запуск
python bot.py
```

## Установка через systemd

```ini
# /etc/systemd/system/telemt-bot.service
[Unit]
Description=Telemt Manager Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/telemt_bot
EnvironmentFile=/root/telemt_bot/.env
ExecStart=/root/telemt_bot/venv/bin/python bot.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> ⚠️ Замени `/root/telemt_bot` на реальный путь к боту.

```bash
systemctl daemon-reload
systemctl enable --now telemt-bot
journalctl -u telemt-bot -f
```

## Конфигурация

Все настройки задаются через файл `.env`. Пример — `.env.example`.

### Обязательные параметры

```env
BOT_TOKEN=1234567890:AABBCCDDEEFFaabbccddeeff
ALLOWED_USERS=123456789
```

### Серверы Telemt

**Один сервер:**
```env
SERVER_URL=http://127.0.0.1:9091
SERVER_NAME=My Telemt
SERVER_AUTH=
```

**Несколько серверов:**
```env
SERVER_1_URL=http://127.0.0.1:9091
SERVER_1_NAME=Main
SERVER_1_AUTH=

SERVER_2_URL=http://10.0.0.2:9091
SERVER_2_NAME=Backup
SERVER_2_AUTH=
```

**Кластер HA** — серверы с одинаковым `GROUP` объединяются в кластер. В меню отображаются как одна кнопка `⚙️ cluster_ha`:
```env
SERVER_1_URL=http://10.0.0.1:9091
SERVER_1_NAME=HA_A
SERVER_1_GROUP=cluster_ha

SERVER_2_URL=http://10.0.0.2:9091
SERVER_2_NAME=HA_B
SERVER_2_GROUP=cluster_ha

SERVER_3_URL=http://10.0.0.3:9091
SERVER_3_NAME=Backup
# GROUP не задан — одиночный сервер
```

### Прочие параметры

| Переменная | Описание | Значение по умолчанию |
|-----------|----------|-----------------------|
| `TZ` | Часовой пояс | системный |
| `LITE_MODE` | Минимальный режим без алертов и графиков | `false` |
| `LOG_LEVEL` | Уровень логов | `INFO` |
| `LOG_FILE` | Файл логов (пусто = только stdout) | — |

### Пороги алертов *(опционально)*

```env
ALERT_CONN_SPIKE_PCT=50       # всплеск соединений, %
ALERT_WRITERS_LOW_PCT=80      # минимальный coverage ME Writers, %
ALERT_HS_TIMEOUT_SPIKE=50     # handshake timeout, +N за 2 мин
ALERT_BAD_CLIENT_SPIKE=100    # плохих TLS клиентов, +N за 2 мин
ALERT_QUOTA_PCT=80            # порог квоты, %
```

## Lite режим

`LITE_MODE=true` оставляет только базовый функционал:

| Остаётся | Отключается |
|----------|-------------|
| 🟢 Состояние сервера | 📊 Отчёт по трафику |
| 👥 Клиенты | ⚠️ Истекающие |
| ➕ Создание клиентов | 🔒 Безопасность |
| ⚡ Runtime | 📡 DC / Writers |
| 📤 Бэкап | 🔍 Проверка прокси |
| | 🔔 Алерты и scheduler |

## Проверка MTProto прокси

Бот анализирует ссылки вида `tg://proxy?...` или `https://t.me/proxy?...`:

- Тип секрета: FakeTLS / DD / Simple
- SNI — домен маскировки (для FakeTLS)
- TCP + MTProto хэндшейк с EU-сервера
- TCP + TLS хэндшейк с дополнительных агентов (RU и др.)

### Установка агента на дополнительный сервер

Агент (`proxy_agent.py`) — лёгкий HTTP-сервис без внешних зависимостей.
Запускается на RU-сервере (или любом другом) и позволяет боту проверять
доступность прокси с этой точки.

**Шаг 1 — Скопировать агент на сервер**

```bash
# На сервере где запущен бот — скачать агент из репозитория
curl -o /root/proxy_agent.py \
  https://raw.githubusercontent.com/vsibilev007/telemt-bot/main/proxy_agent.py

# Или скопировать с основного сервера по SCP
scp /root/telemt_bot/proxy_agent.py root@IP:/root/proxy_agent.py
```

**Шаг 2 — Проверить что работает**

```bash
python3 /root/proxy_agent.py --host 127.0.0.1 --port 8765 --token YOUR_TOKEN
# В другом терминале:
curl "http://127.0.0.1:8765/health" -H "X-Token: YOUR_TOKEN"
# Ожидаемый ответ: {"status": "ok"}
```

**Шаг 3 — Создать systemd сервис**

```bash
cat > /etc/systemd/system/proxy-agent.service << EOF
[Unit]
Description=Proxy Check Agent
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /root/proxy_agent.py --host IP --port 8765 --token YOUR_TOKEN
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

> ⚠️ Замени `IP` на адрес интерфейса который доступен с основного сервера  
> (например VPN-адрес `10.8.1.2`, или `0.0.0.0` чтобы слушать на всех).  
> Замени `YOUR_TOKEN` на произвольный секретный токен.

**Шаг 4 — Запустить и проверить**

```bash
systemctl daemon-reload
systemctl enable --now proxy-agent
systemctl status proxy-agent
journalctl -u proxy-agent -f
```

**Шаг 5 — Настроить бота**

Добавь в `.env` на основном сервере:

```env
AGENT_1_URL=http://IP:8765
AGENT_1_NAME=RU
AGENT_1_TOKEN=YOUR_TOKEN
AGENT_1_FLAG=🇷🇺
```

Перезапусти бота:

```bash
systemctl restart telemt-bot
```

После этого при проверке прокси бот будет показывать результат с обеих точек:

```
📡 Доступность:
  🇪🇺 EU — TCP: 🟢 56 мс  |  MTProto: 🟢 3665 мс
  🇷🇺 RU — TCP: 🟢 4 мс   |  TLS: 🟢 185 мс
```

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

## Команды

| Команда | Описание |
|---------|----------|
| `/menu` | Главное меню |
| `/help` | Справка |
| `/adduser имя [дней]` | Быстро создать клиента |
| `/find запрос` | Поиск клиента |
| `/alerts` | Настройки алертов |
| `/alert_log` | История последних 20 алертов |
| `/id` | Ваш Telegram ID |

## Зависимости

```
aiogram==3.27.0        # Telegram Bot API
aiohttp==3.13.5        # HTTP-клиент
aiosqlite==0.22.1      # SQLite
APScheduler==3.11.2    # Планировщик задач
matplotlib==3.10.3     # Графики (опционально)
telethon==1.43.2       # MTProto проверка прокси (опционально)
python-socks==2.7.1    # SOCKS для Telethon
qrcode[pil]==8.2       # QR-коды
Pillow==12.1.1
openpyxl==3.1.5        # Экспорт Excel
psutil==7.2.2          # Системная информация
python-dotenv==1.2.2
```

## Лицензия

MIT
