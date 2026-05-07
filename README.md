# Telemt Manager Bot

Telegram-бот для управления [Telemt MTProxy](https://github.com/telemt/telemt) через Control API v1.

## Главное меню

```
🟢 Состояние сервера    📊 Отчёт по трафику
👥 Все клиенты          ➕ Новый клиент
⚡ Runtime              ⚠️ Истекающие
🔒 Безопасность         🔗 Upstreams
📡 DC / Writers         📤 Бэкап
✅ Server 1             Server 2        ← переключатель серверов
```

## Возможности

| Раздел | Функции |
|--------|---------|
| 🟢 Состояние сервера | Dashboard telemt: статус, uptime, версия, соединения, bad-классы, handshake |
| 📊 Отчёт по трафику | Все клиенты за 1/7/30 дней, сортировка по потреблению, пометка истёкших |
| 👥 Клиенты | Список с пагинацией, трафик и кол-во соединений на кнопке |
| 🗒 Карточка клиента | Просмотр, редактирование полей, смена секрета, история трафика, QR-коды |
| ➕ Новый клиент | FSM-мастер (6 шагов) или быстрая команда `/adduser имя [дней]` |
| ⚠️ Истекающие | Список + массовое удаление истёкших |
| 📤 Бэкап | Выгрузка `telemt.toml` файлом в чат |
| ⚡ Runtime | Gates, Init, ME Quality, Upstream Quality, Events, Connections |
| 🔒 Безопасность | Posture, IP Whitelist, Effective Limits |
| 📡 DC / Writers | DC Status, ME Writers по DC |
| 🔗 Upstreams | Список апстримов с RTT и статусом |
| 🔔 Алерты | 9 типов: падение, восстановление, всплески SNI/TLS/timeout/reset, версия |
| 🖥 Мультисервер | Переключение между инстансами Telemt из главного меню |

## Требования

- Python 3.11+
- Telemt MTProxy с включённым Control API (`api_addr = "127.0.0.1:9091"`)

## Быстрый старт

```bash
# 1. Клонировать
git clone https://github.com/yourname/telemt-bot.git
cd telemt-bot

# 2. Виртуальное окружение
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Конфиг
cp .env.example .env
nano .env   # BOT_TOKEN, ALLOWED_USERS, SERVER_URL

# 4. Запуск
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
| `SERVER_URL` | URL Control API telemt | `http://127.0.0.1:9091` |
| `SERVER_NAME` | Имя сервера в меню | `My Telemt` |
| `SERVER_AUTH` | Authorization header (если задан) | `secret-token` |

### Несколько серверов

```env
SERVER_1_URL=http://10.0.0.1:9091
SERVER_1_NAME=RU Server
SERVER_1_AUTH=secret1

SERVER_2_URL=http://10.0.0.2:9091
SERVER_2_NAME=EU Server
SERVER_2_AUTH=secret2
```

## Алерты

Настраиваются командой `/alerts`. Каждый тип можно включить/выключить отдельно:

| Тип | Описание | Cooldown |
|-----|----------|----------|
| `status_down` | Сервер стал недоступен | 2 мин |
| `status_up` | Сервер восстановился | — |
| `conn_spike` | Всплеск соединений >50% | 2 мин |
| `writers_low` | ME Writers coverage <80% | 2 мин |
| `version_change` | Обновилась версия telemt | — |
| `bad_unknown_sni` | Неизвестный TLS SNI (любой рост) | 5 мин |
| `hs_timeout_spike` | Handshake timeout +50 за 2 мин | 2 мин |
| `bad_client_spike` | Плохих TLS клиентов +100 за 2 мин | 2 мин |
| `hs_conn_reset` | Сброс при handshake (любой рост) | 5 мин |

## Фоновые задачи

| Задача | Интервал | Описание |
|--------|----------|----------|
| Проверка здоровья + алерты | 2 мин | `GET /health`, `/stats/summary`, алерты |
| Сбор трафика | 15 мин | Снимки в SQLite для истории |
| Очистка БД | 24 ч | Удаление данных старше 30 дней |

## Структура проекта

```
telemt_bot/
├── bot.py            # Точка входа, инициализация
├── config.py         # Загрузка конфига из .env
├── handlers.py       # Все обработчики команд и callback
├── keyboards.py      # Inline-клавиатуры
├── formatters.py     # Форматирование ответов API в HTML
├── api_client.py     # HTTP-клиент для Telemt Control API
├── database.py       # SQLite: трафик, алерты, статусы
├── scheduler.py      # Фоновые задачи (APScheduler)
├── session.py        # Выбор активного сервера для юзера
├── middlewares.py    # Авторизация
├── states.py         # FSM-состояния
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
qrcode[pil]==8.2         # Генерация QR-кодов
Pillow==12.1.1           # Работа с изображениями
openpyxl==3.1.5          # Экспорт в Excel
psutil==7.2.2            # Системная информация
python-dotenv==1.2.2     # Загрузка .env
```

## Лицензия

MIT
