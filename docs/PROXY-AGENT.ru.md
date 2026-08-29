# Агент проверки прокси

[🇬🇧 Proxy Agent Setup](PROXY-AGENT.en.md)

---

## Обзор

Агент проверки — это легковесный Python-скрипт (`proxy_agent.py`), который запускается на удалённых серверах для проверки доступности прокси из разных географических точек. Использует только стандартную библиотеку Python — без внешних зависимостей.

## Как это работает

```
┌─────────────┐     HTTP      ┌─────────────┐     MTProto     ┌─────────────┐
│  Telegram    │ ──────────── │  Proxy Agent │ ─────────────── │   Telemt    │
│    Бот       │              │  (RU, EU..)  │                 │   Сервер    │
└─────────────┘              └─────────────┘                 └─────────────┘
```

Бот отправляет запросы на проверку агентам. Агенты выполняют TCP, TLS и MTProto проверки и возвращают результаты.

## Установка

### Шаг 1 — Скопировать агента на удалённый сервер

**Вариант A — Скачать из GitHub:**

```bash
ssh root@УДАЛЁННЫЙ_СЕРВЕР
curl -o /opt/proxy_agent.py \
  https://raw.githubusercontent.com/vsibilev007/telemt-bot/main/proxy_agent.py
```

**Вариант B — Скопировать по SCP:**

```bash
scp proxy_agent.py root@УДАЛЁННЫЙ_СЕРВЕР:/opt/proxy_agent.py
```

### Шаг 2 — Проверить работу

```bash
python3 /opt/proxy_agent.py --host 0.0.0.0 --port 8765 --token YOUR_TOKEN &

# В другом терминале:
curl "http://127.0.0.1:8765/health" -H "X-Token: YOUR_TOKEN"
# Ответ: {"status": "ok"}
```

### Шаг 3 — Создать systemd-сервис

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

> Замените `0.0.0.0` на конкретный IP (например, VPN-адрес `10.8.1.2`), если не нужно слушать все интерфейсы.

### Шаг 4 — Настроить бота

Добавьте в `.env` на основном сервере:

```env
AGENT_1_URL=http://IP_АГЕНТА:8765
AGENT_1_NAME=RU
AGENT_1_TOKEN=YOUR_TOKEN
AGENT_1_FLAG=🇷🇺
```

Перезапустите бота:

```bash
systemctl restart telemt-bot
```

## Endpoint'ы агента

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/health` | GET | Проверка здоровья |
| `/check` | GET | TCP + TLS проверка |
| `/check_full` | GET | TCP + TLS + GeoIP + стабильность |

### Параметры проверки

| Параметр | Описание |
|----------|----------|
| `host` | Хост прокси |
| `port` | Порт прокси |
| `secret` | Секрет прокси |
| `sni` | SNI домен (опционально) |

## Пример вывода

При проверке прокси бот показывает результаты со всех агентов:

```
📡 Доступность:
  🇪🇺 EU — TCP: 🟢 56 мс  |  MTProto: 🟢 3665 мс
  🇷🇺 RU — TCP: 🟢 4 мс   |  TLS: 🟢 185 мс
```

## Безопасность

- Агент использует токен-аутентификацию (заголовок `X-Token`)
- Агент должен быть доступен только с сервера бота
- Используйте правила firewall для ограничения доступа

---

## См. также

- [Инструкция по быстрому запуску](QUICKSTART.ru.md)
- [Справочник конфигурации](CONFIGURATION.ru.md)
- [Развёртывание](DEPLOYMENT.ru.md)
