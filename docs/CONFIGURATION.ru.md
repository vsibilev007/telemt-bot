# Справочник конфигурации

[🇬🇧 Configuration Reference](CONFIGURATION.en.md)

---

## Обязательные переменные

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен бота от [@BotFather](https://t.me/BotFather) |
| `ALLOWED_USERS` | Telegram user_id через запятую |

---

## Конфигурация серверов

### Один сервер

```env
SERVER_URL=http://127.0.0.1:9091
SERVER_NAME=My Telemt
SERVER_AUTH=
```

### Несколько серверов

```env
SERVER_1_URL=http://10.0.0.1:9091
SERVER_1_NAME=Main
SERVER_1_AUTH=secret1

SERVER_2_URL=http://10.0.0.2:9091
SERVER_2_NAME=Backup
SERVER_2_AUTH=secret2
```

### Кластер HA

Серверы с одинаковым `GROUP` образуют кластер. Write-операции выполняются параллельно на всех узлах; чтение — с первого доступного.

```env
SERVER_1_URL=http://10.0.0.1:9091
SERVER_1_NAME=HA_A
SERVER_1_GROUP=cluster_ha

SERVER_2_URL=http://10.0.0.2:9091
SERVER_2_NAME=HA_B
SERVER_2_GROUP=cluster_ha
```

---

## Общие настройки

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `TZ` | Часовой пояс | Системный |
| `LITE_MODE` | Минимальный режим | `false` |
| `LOG_LEVEL` | Уровень логов | `INFO` |
| `LOG_FILE` | Файл логов | stdout |
| `LOG_MAX_MB` | Макс. размер файла | `10` |
| `LOG_BACKUPS` | Кол-во бэкапов | `3` |
| `NO_COLOR` | Отключить ANSI | — |
| `TELEMT_CONFIG_PATH` | Путь к telemt.toml | `/etc/telemt/telemt.toml` |

---

## Пороги алертов

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `ALERT_CONN_SPIKE_PCT` | Всплеск соединений, % | `50` |
| `ALERT_CONN_SPIKE_MIN_BASE` | Мин. база для срабатывания | `100` |
| `ALERT_WRITERS_LOW_PCT` | Порог ME Writers coverage, % | `80` |
| `ALERT_HS_TIMEOUT_SPIKE` | Handshake timeout, +N за 2 мин | `50` |
| `ALERT_BAD_CLIENT_SPIKE` | Плохих TLS, +N за 2 мин | `100` |
| `ALERT_QUOTA_PCT` | Порог квоты клиента, % | `80` |

---

## Прокси для Telegram API

```env
# SOCKS5
TELEGRAM_PROXY_URL=socks5://user:password@host:port

# HTTP прокси
TELEGRAM_PROXY_URL=http://host:port
```

Поддержка SOCKS5, SOCKS4, HTTP. Логин/пароль скрывается в логах.

---

## Конфигурация агентов

```env
AGENT_1_URL=http://agent-ip:8765
AGENT_1_NAME=RU
AGENT_1_TOKEN=your-secret-token
AGENT_1_FLAG=🇷🇺

# Несколько агентов
AGENT_2_URL=http://agent2-ip:8765
AGENT_2_NAME=Asia
AGENT_2_TOKEN=another-token
AGENT_2_FLAG=🇨🇳
```

---

## Пример .env

```env
# Обязательные
BOT_TOKEN=1234567890:AABBCCDDEEFFaabbccddeeff
ALLOWED_USERS=123456789,987654321

# Сервер
SERVER_URL=http://127.0.0.1:9091
SERVER_NAME=My Telemt
SERVER_AUTH=

# Опционально
TZ=Europe/Moscow
LITE_MODE=false
LOG_LEVEL=INFO

# Пороги алертов
ALERT_CONN_SPIKE_PCT=50
ALERT_WRITERS_LOW_PCT=80
```

---

## См. также

- [Инструкция по быстрому запуску](QUICKSTART.ru.md)
- [Развёртывание](DEPLOYMENT.ru.md)
- [WEB Proxy](WEB-PROXY.ru.md)
