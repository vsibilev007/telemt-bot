# Telemt Manager Bot

[![Docker](https://github.com/vsibilev007/telemt-bot/actions/workflows/docker.yml/badge.svg)](https://github.com/vsibilev007/telemt-bot/actions/workflows/docker.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Telegram-бот для управления [Telemt MTProxy](https://github.com/telemt/telemt) серверами через Control API v1.

**Совместимость:** Telemt 3.4.14 — 3.5.5+

[🇬🇧 README in English](README.md)

---

## Быстрый старт

```bash
# Однострочная установка через Docker
curl -O https://raw.githubusercontent.com/vsibilev007/telemt-bot/main/docker-compose.yml
cp .env.example .env && nano .env
docker compose up -d
```

- [Инструкция по быстрому запуску](docs/QUICKSTART.ru.md)
- [Quick Start Guide](docs/QUICKSTART.en.md)

---

## Возможности

| Категория | Функции |
|-----------|---------|
| **Управление клиентами** | Создание, редактирование, удаление; QR-коды; история трафика с графиками |
| **Мониторинг** | Дашборд, runtime, безопасность, DC/Writers, upstreams |
| **Алерты** | 10 типов событий с настраиваемыми порогами и cooldown |
| **Кластер HA** | Параллельные write-операции на все узлы, агрегированное чтение |
| **Мультисервер** | Переключение между серверами и кластерами из меню |
| **Диагностика узлов** | DNS, TCP, SSH, Ping, MTProto проверки с агентами |
| **WEB Proxy** | Статус, сессии, debug, carrier learning (Telemt 3.5.5+) |
| **Редактирование конфига** | Изменение настроек через бота (PATCH /v1/config) |
| **Runtime reload** | Перезагрузка конфигурации без перезапуска (3.4.25+) |
| **Lite режим** | Минимальный набор функций без алертов и графиков |

---

## Документация

- [Инструкция по быстрому запуску](docs/QUICKSTART.ru.md)
- [Справочник конфигурации](docs/CONFIGURATION.ru.md)
- [Развёртывание](docs/DEPLOYMENT.ru.md)
- [WEB Proxy](docs/WEB-PROXY.ru.md)
- [Агент проверки прокси](docs/PROXY-AGENT.ru.md)

---

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и главное меню |
| `/menu` | Главное меню |
| `/help` | Справка |
| `/adduser имя [дней]` | Быстро создать клиента |
| `/find запрос` | Поиск клиента по имени |
| `/check tg://proxy?...` | Диагностика узла |
| `/reload [instant\|drain]` | Runtime reload (3.4.25+) |
| `/alerts` | Настройки алертов |
| `/id` | Ваш Telegram ID |

---

## Docker образы

```bash
docker pull ghcr.io/vsibilev007/telemt-bot:latest
```

| Тег | Описание |
|-----|----------|
| `latest` | Последний коммит в `main` |
| `v1.2.3` | Конкретная версия |
| `sha-abc1234` | Конкретный коммит |

---

## Структура проекта

```
telemt-bot/
├── bot.py              # Точка входа
├── config.py           # Конфигурация из .env
├── handlers.py         # Обработчики команд и callback
├── keyboards.py        # Inline-клавиатуры
├── formatters.py       # HTML-форматирование ответов
├── api_client.py       # HTTP-клиент + кластерные операции
├── database.py         # SQLite: трафик, алерты, сессии
├── scheduler.py        # Фоновые задачи и алерты
├── proxy_checker.py    # Проверка MTProto прокси
├── proxy_agent.py      # Агент проверки (только stdlib)
├── docs/               # Детальная документация
└── docker-compose.yml  # Docker Compose конфигурация
```

---

## Лицензия

[MIT](LICENSE)
