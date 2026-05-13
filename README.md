# Telemt Manager Bot

Telegram-бот для управления [Telemt MTProxy](https://github.com/telemt/telemt) через Control API v1.

## Главное меню

```
🟢 Состояние сервера    📊 Отчёт по трафику
👥 Все клиенты          ➕ Новый клиент
⚡ Runtime              ⚠️ Истекающие
🔒 Безопасность         🔗 Upstreams
📡 DC / Writers         📤 Бэкап
✅ Server 1               Server 2       ← переключатель серверов
```

## Возможности

| Раздел | Функции |
|--------|---------|
| 🟢 Состояние сервера | Dashboard: статус, uptime, версия, соединения, bad-классы, handshake-ошибки, время обновления |
| 📊 Отчёт по трафику | Все клиенты за 1/7/30 дней, сортировка по потреблению, пометка истёкших, 📈 график топ-15 |
| 👥 Клиенты | Список с пагинацией, 🔍 поиск по имени, трафик и соединения на кнопке |
| 🗒 Карточка клиента | Просмотр, редактирование полей, смена секрета, 📊 история трафика с 📈 графиком (24ч/7/14/30д), QR-коды |
| ➕ Новый клиент | FSM-мастер (6 шагов) или быстрая команда `/adduser имя [дней]` |
| ⚠️ Истекающие | Список клиентов с истекающим сроком + массовое удаление истёкших |
| 📤 Бэкап | Выгрузка `telemt.toml` файлом в чат |
| ⚡ Runtime | Gates, Init, ME Quality, Upstream Quality, Events, Connections |
| 🔒 Безопасность | Posture, IP Whitelist, Effective Limits |
| 📡 DC / Writers | DC Status, ME Writers по датацентрам |
| 🔗 Upstreams | Список апстримов с RTT и статусом |
| 🔔 Алерты | 9 типов + алерт квоты. Настройка через `/alerts`, история через `/alert_log` |
| 🖥 Мультисервер | Переключение между инстансами из главного меню, выбор сохраняется между перезапусками |

## Команды

| Команда | Описание |
|---------|----------|
| `/menu` | Главное меню |
| `/help` | Справка по боту |
| `/adduser имя [дней]` | Быстро создать клиента, пример: `/adduser vasya 30` |
| `/find запрос` | Поиск клиента по имени, пример: `/find vas` |
| `/alerts` | Включить / выключить алерты |
| `/alert_log` | История последних 20 алертов |
| `/id` | Ваш Telegram ID |

## Требования

- Python 3.11+
- Telemt MTProxy с включённым Control API (`api_addr = "127.0.0.1:9091"`)
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
[[Unit]
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

| Переменная | Описание | Пример |
|-----------|----------|--------|
| `BOT_TOKEN` | Токен бота от @BotFather | `1234:AABBcc...` |
| `ALLOWED_USERS` | Telegram user_id через запятую | `123456,789012` |
| `SERVER_URL` | URL Control API telemt | `http://IP:9091` |
| `SERVER_NAME` | Имя сервера в меню | `My Telemt` |
| `SERVER_AUTH` | Authorization header (если задан) | `secret-token` |
| `TZ` | Часовой пояс для отображения времени | `Europe/Moscow` |

### Несколько серверов

```env
SERVER_1_URL=http://IP:9091
SERVER_1_NAME= Server 1
SERVER_1_AUTH=secret1

SERVER_2_URL=http://IP:9091
SERVER_2_NAME= Server 2
SERVER_2_AUTH=secret2
```

### Пороги алертов (опционально)

```env
ALERT_CONN_SPIKE_PCT=50       # всплеск соединений, %
ALERT_CONN_SPIKE_MIN_BASE=100 # мин. база соединений для срабатывания
ALERT_WRITERS_LOW_PCT=80      # порог coverage ME Writers, %
ALERT_HS_TIMEOUT_SPIKE=50     # handshake timeout, +N за 2 мин
ALERT_BAD_CLIENT_SPIKE=100    # плохих TLS клиентов, +N за 2 мин
ALERT_QUOTA_PCT=80            # алерт при использовании N% квоты клиента
```

### Логирование

```env
LOG_LEVEL=INFO          # DEBUG / INFO / WARNING / ERROR
LOG_FILE=telemt_bot.log # путь к файлу (пусто = только stdout)
LOG_MAX_MB=10           # макс. размер файла до ротации
LOG_BACKUPS=3           # кол-во резервных файлов
NO_COLOR=1              # отключить цвета (для non-tty окружений)
```

## Алерты

Настраиваются командой `/alerts`. Каждый тип включается/выключается отдельно:

| Тип | Описание | Cooldown |
|-----|----------|----------|
| `status_down` | Сервер стал недоступен | 5 мин |
| `status_up` | Сервер восстановился | — |
| `conn_spike` | Всплеск соединений >50% | 2 мин |
| `writers_low` | ME Writers coverage <80% | 2 мин |
| `version_change` | Обновилась версия telemt | — |
| `bad_unknown_sni` | Неизвестный TLS SNI (любой рост) | 5 мин |
| `hs_timeout_spike` | Handshake timeout +50 за 2 мин | 2 мин |
| `bad_client_spike` | Плохих TLS клиентов +100 за 2 мин | 2 мин |
| `hs_conn_reset` | Сброс при handshake (любой рост) | 5 мин |
| `quota_warn` | Клиент использовал ≥80% квоты | 1 час |

История сработавших алертов — команда `/alert_log`.

## Фоновые задачи

| Задача | Интервал | Описание |
|--------|----------|----------|
| Проверка здоровья + алерты | 2 мин | `GET /health`, `/stats/summary`, все алерты |
| Сбор трафика | 15 мин | Снимки трафика в SQLite для графиков и истории |
| Очистка БД | 24 ч | Удаление данных старше 30 дней |

## Структура проекта

```
telemt_bot/
├── bot.py            # Точка входа, инициализация, команды Меню
├── config.py         # Загрузка конфига из .env, пороги алертов
├── handlers.py       # Все обработчики команд и callback
├── keyboards.py      # Inline-клавиатуры (chart_mode и текстовый режим)
├── formatters.py     # Форматирование ответов API в HTML
├── charts.py         # Графики трафика через matplotlib (тёмная тема)
├── api_client.py     # HTTP-клиент для Telemt Control API (semaphore, timeout)
├── database.py       # SQLite: трафик, алерты, статусы, сессии пользователей
├── scheduler.py      # Фоновые задачи (APScheduler) с safe_job декоратором
├── session.py        # Выбор активного сервера (хранится в БД)
├── logging_setup.py  # Цветной logging с ротацией файла
├── tz.py             # Работа с часовыми поясами через TZ из .env
├── middlewares.py    # Авторизация по ALLOWED_USERS
├── states.py         # FSM-состояния (Create, Edit, Search)
├── sysinfo.py        # Системная информация (psutil)
├── qr_utils.py       # Генерация QR-кодов
├── export_toml.py    # Бэкап telemt.toml
├── export_utils.py   # Экспорт CSV/Excel
├── requirements.txt
└── .env.example
```

## Зависимости

```
aiogram==3.27.0          # Telegram Bot API framework
aiohttp==3.13.5          # HTTP-клиент для API telemt
aiosqlite==0.22.1        # Асинхронный SQLite
APScheduler==3.11.2      # Планировщик фоновых задач
matplotlib==3.10.3       # Графики трафика
qrcode[pil]==8.2         # Генерация QR-кодов
Pillow==12.1.1           # Работа с изображениями
openpyxl==3.1.5          # Экспорт в Excel
psutil==7.2.2            # Системная информация
python-dotenv==1.2.2     # Загрузка .env
```

## Лицензия

MIT
