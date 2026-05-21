# Telemt Manager Bot

Telegram-бот для управления [Telemt MTProxy](https://github.com/telemt/telemt) через Control API v1.

## Главное меню

```
🟢 Состояние сервера    📊 Отчёт по трафику
👥 Все клиенты          ➕ Новый клиент
⚡ Runtime              ⚠️ Истекающие
🔒 Безопасность         🔗 Upstreams
📡 DC / Writers         📤 Бэкап
🔍 Проверить прокси
✅ cluster_ha           BS    ← переключатель серверов/кластеров
```

## Возможности

| Раздел | Функции |
|--------|---------|
| 🟢 Состояние сервера | Dashboard: статус, uptime, версия, соединения, bad-классы, handshake-ошибки |
| 📊 Отчёт по трафику | Все клиенты за 1/7/30 дней, сортировка, пометка истёкших, 📈 график топ-15 |
| 👥 Клиенты | Список с пагинацией, 🔍 поиск, трафик, соединения, IP-шаринг индикатор |
| 🗒 Карточка клиента | Просмотр, редактирование, смена секрета, история трафика с 📈 графиком, QR-коды |
| ➕ Новый клиент | FSM-мастер (6 шагов) или `/adduser имя [дней]` |
| ⚠️ Истекающие | Список + массовое удаление истёкших |
| 📤 Бэкап | Выгрузка `telemt.toml` файлом в чат |
| ⚡ Runtime | Gates, Init, ME Quality, Upstream Quality, Events, Connections |
| 🔒 Безопасность | Posture, IP Whitelist, Effective Limits |
| 📡 DC / Writers | DC Status, ME Writers по датацентрам |
| 🔗 Upstreams | Список апстримов с RTT и статусом |
| 🔔 Алерты | 10 типов, настройка через `/alerts`, история через `/alert_log` |
| 🖥 Мультисервер | Переключение между серверами и кластерами из главного меню |
| ⚙️ Кластер HA | Write-операции на все узлы параллельно, чтение с первого доступного |
| 🔍 Проверка прокси | MTProto ссылки: SNI, тип секрета, TCP + TLS с нескольких точек |

## Команды

| Команда | Описание |
|---------|----------|
| `/menu` | Главное меню |
| `/help` | Справка |
| `/adduser имя [дней]` | Быстро создать клиента |
| `/find запрос` | Поиск клиента по имени |
| `/alerts` | Настройки алертов |
| `/alert_log` | История последних 20 алертов |
| `/id` | Ваш Telegram ID |

## Требования

- Python 3.11+
- Telemt MTProxy с включённым Control API (`api_addr = "IP:9091"`)
- `matplotlib` — для графиков трафика (опционально, бот работает и без него)
- uv

## Быстрый старт

```bash
# 1. Клонировать
git clone https://github.com/vsibilev007/telemt-bot.git
cd telemt-bot

# Виртуальное окружение
uv sync
# ЛИБО: Системно (Windows)
pip install -r requirements.txt

# 3. Конфиг
cp .env.example .env
nano .env   # BOT_TOKEN, ALLOWED_USERS, SERVER_URL

# Запуск с uv
uv run bot.py
# ЛИБО: Запуск
python bot.py
```

## Установка через systemd

> ⚠️ **Замени `/root/telemt_bot` на реальный путь к боту на своём сервере.**

```ini
# /etc/systemd/system/telemt-bot.service
[Unit]
Description=Telemt Manager Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/telemt_bot        # ← путь к директории бота
EnvironmentFile=/opt/telemt_bot/.env    # ← путь к .env файлу
ExecStart=/opt/telemt_bot/.venv/bin/python bot.py  # ← путь к venv
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

## Переменные окружения

### Основные

| Переменная | Описание | Пример |
|-----------|----------|--------|
| `BOT_TOKEN` | Токен от @BotFather | `1234:AABBcc...` |
| `ALLOWED_USERS` | Telegram user_id через запятую | `123456,789012` |
| `TZ` | Часовой пояс | `Europe/Moscow` |
| `LITE_MODE` | Минимальный режим (без алертов/графиков) | `false` |

### Один сервер

```env
SERVER_URL=http://IP:9091
SERVER_NAME=My Telemt
SERVER_AUTH=secret
```

### Несколько серверов

```env
SERVER_1_URL=http://IP:9091
SERVER_1_NAME=Main
SERVER_1_AUTH=

SERVER_2_URL=http://IP:9091
SERVER_2_NAME=Backup
SERVER_2_AUTH=
```

### Кластер HA

Серверы с одинаковым `SERVER_N_GROUP` объединяются в кластер.
Write-операции (создание/удаление/редактирование) выполняются параллельно на всех узлах.
В меню кластер отображается как одна кнопка `⚙️` с именем группы.

```env
SERVER_1_URL=http://IP:9091
SERVER_1_NAME=HA_A
SERVER_1_AUTH=
SERVER_1_GROUP=cluster_ha

SERVER_2_URL=http://IP:9092
SERVER_2_NAME=HA_B
SERVER_2_AUTH=
SERVER_2_GROUP=cluster_ha

SERVER_3_URL=http://IP:9091
SERVER_3_NAME=Backup
SERVER_3_AUTH=
# SERVER_3_GROUP не задан — одиночный сервер
```

### Lite режим

```env
LITE_MODE=true
```

Отключает: алерты, scheduler, графики, отчёт по трафику, истекающие,
безопасность, upstreams, DC/Writers, проверку прокси.

Оставляет: состояние сервера, клиенты, создание клиентов, runtime, бэкап.

### Агенты проверки прокси

Агент (`proxy_agent.py`) запускается на дополнительных серверах для проверки
доступности прокси с разных точек (RU, EU и т.д.).

```env
AGENT_1_URL=http://IP:8765
AGENT_1_NAME=RU
AGENT_1_TOKEN=secret-token
AGENT_1_FLAG=🇷🇺

AGENT_2_URL=http://IP:8765
AGENT_2_NAME=Asia
AGENT_2_TOKEN=secret-token
# AGENT_2_FLAG не задан — определится по GeoIP автоматически
```

### Пороги алертов

```env
ALERT_CONN_SPIKE_PCT=50
ALERT_CONN_SPIKE_MIN_BASE=100
ALERT_WRITERS_LOW_PCT=80
ALERT_HS_TIMEOUT_SPIKE=50
ALERT_BAD_CLIENT_SPIKE=100
ALERT_QUOTA_PCT=80
```

### Логирование

```env
LOG_LEVEL=INFO
LOG_FILE=telemt_bot.log
LOG_MAX_MB=10
LOG_BACKUPS=3
NO_COLOR=1
```

## Алерты

| Тип | Описание | Cooldown |
|-----|----------|----------|
| `status_down` | Сервер недоступен | 5 мин |
| `status_up` | Восстановился | — |
| `conn_spike` | Всплеск соединений >50% | 2 мин |
| `writers_low` | ME Writers <80% | 2 мин |
| `version_change` | Обновление версии | — |
| `bad_unknown_sni` | Неизвестный SNI | 5 мин |
| `hs_timeout_spike` | Handshake timeout +50 за 2 мин | 2 мин |
| `bad_client_spike` | Плохих TLS +100 за 2 мин | 2 мин |
| `hs_conn_reset` | Сброс при handshake | 5 мин |
| `quota_warn` | Клиент использовал ≥80% квоты | 1 час |

## Проверка MTProto прокси

Бот проверяет прокси-ссылки вида `tg://proxy?...` или `https://t.me/proxy?...`:

- Тип секрета: FakeTLS / DD / Simple
- SNI — домен под который маскируется прокси
- TCP RTT + TLS handshake с каждой точки (EU, RU и др.)

## Установка агента через systemd

> ⚠️ **Замени `/root/proxy_agent.py` на реальный путь к агенту на своём сервере.**


# systemd сервис
cp proxy_agent.py /root/

cat > /etc/systemd/system/proxy-agent.service << EOF
 [Unit]
 Description=Proxy Check Agent
 After=network.target
 [Service]
 Type=simple
 User=root
 ExecStart=/usr/bin/python3 /root/proxy_agent.py --host 127.0.0.1 --port 8765 --token МОЙ_СЕКРЕТ  # ← путь к директории агента 
 Restart=on-failure
 RestartSec=5
 [Install]
 WantedBy=multi-user.target
 EOF
systemctl daemon-reload
systemctl enable --now proxy-agent
systemctl restart proxy-agent.service


```

## Структура проекта

```
telemt_bot/
├── bot.py            # Точка входа
├── config.py         # Конфиг из .env (серверы, кластеры, агенты, lite режим)
├── handlers.py       # Все обработчики команд и callback
├── keyboards.py      # Inline-клавиатуры
├── formatters.py     # Форматирование ответов API в HTML
├── charts.py         # Графики трафика (matplotlib)
├── api_client.py     # HTTP-клиент + кластерные операции
├── database.py       # SQLite: трафик, алерты, сессии
├── scheduler.py      # Фоновые задачи + алерты
├── session.py        # Выбор сервера (хранится в БД)
├── proxy_checker.py  # Проверка MTProto прокси
├── proxy_agent.py    # Агент проверки (запускается на RU-сервере)
├── logging_setup.py  # Цветной logging с ротацией
├── tz.py             # Часовые пояса
├── middlewares.py    # Авторизация
├── states.py         # FSM-состояния
├── sysinfo.py        # Системная информация
├── qr_utils.py       # QR-коды
├── export_toml.py    # Бэкап конфига
├── export_utils.py   # Экспорт CSV/Excel
├── requirements.txt
└── .env.example
```

## Зависимости

```
aiogram==3.27.0
aiohttp==3.13.5
aiosqlite==0.22.1
APScheduler==3.11.2
matplotlib==3.10.3      # графики (опционально)
telethon==1.43.2        # проверка прокси (опционально)
qrcode[pil]==8.2
Pillow==12.1.1
openpyxl==3.1.5
psutil==7.2.2
python-dotenv==1.2.2
python-socks==2.7.1
```

## Лицензия

MIT
