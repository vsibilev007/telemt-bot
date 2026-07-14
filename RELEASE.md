# Release: Docker-образ + CI/CD на GHCR

## Docker-образ (новое)

- **Производственный Dockerfile** — двухстадийная сборка (`builder` → `final`) на `python:3.11-slim-bookworm`
- **Non-root пользователь** `appuser` (UID 10001) — контейнер не запускается от root
- **Hardening**: `read_only`, `cap_drop: ALL`, `no-new-privileges`, `mem_limit: 256m`, `pids_limit: 256`
- **Named volume** `telemt-data:/data` — безопасное хранение БД с правильными правами
- **Trim слоя**: удаляются `__pycache__`, тесты пакетов, `.pyc`/`.pyx`/`.pyi` — меньше итогового размера

## CI/CD (новое)

- **GitHub Actions** — пайплайн `lint → build → scan → push` при пуше в `main` и по тегам `v*.*.*`
- **Lint**: `ruff check` на каждый PR
- **Trivy scan** — сканирование HIGH/CRITICAL уязвимостей перед пушем; сборка падает при наличии фиксов
- **GHCR**: образ публикуется в `ghcr.io/ddark008/telemt-bot` с тегами `latest`, `v1.2.3`, `1.2`, `sha-abc1234`
- **GHA cache**: BuildKit кеширует слои между запусками — быстрые повторные сборки

## Исправления безопасности (зависимости)

- `Pillow 12.1.1 → 12.3.0` (CVE-2026-40192 DoS, CVE-2026-42311 code execution)
- `setuptools → 83.0.0` — обновлены вендорные пакеты: `jaraco.context 6.1.0` (CVE-2026-23949), `wheel 0.46.3` (CVE-2026-24049)

---

# Release: Диагностика узла + ссылки с SNI-доменами + 3.4.18

## Диагностика узла (новое)

- **Команда `/check tg://proxy?...`** — полная диагностика узла
- Кнопка **🔍 Проверить прокси** теперь тоже использует полную диагностику
- Проверки: DNS резолв (IPv4+IPv6), TCP прокси, TCP SSH (22), Ping (ICMP), MTProto
- Вывод: статусы по каждому протоколу, диагностика, время проверки, итоговый статус (OK/PARTIAL/FAIL)
- Агенты (RU и др.) проверяются параллельно

## Ссылки с доменами маскировки (новое)

- **Карточка клиента** — над каждой TLS-ссылкой показывается домен маскировки (SNI)
- **QR-кнопки** — показывают домен вместоgeneric "QR" (📷 domain.name)
- Извлечение SNI из FakeTLS-секрета автоматическое

## API Telemt 3.4.14-3.4.18

- **Сброс квоты** — кнопка «🔄 Сбросить квоту» в карточке клиента (`POST /v1/users/{username}/reset-quota`)
- **api_client.py** — методы `reset_user_quota()`, `get_config()`, `patch_config()`
- **Редактирование конфига** — кнопка «⚙️ Конфиг» в главном меню, 6 секций через `PATCH /v1/config`

## Бэкап конфигурации

- **📤 Бэкап** — чтение полного `telemt.toml` с диска (API не отдаёт секции access/server/network)

## Исправления

- **proxy_checker.py** — DNS резолв параллельный (не блокирует TCP/SSH/Ping)
- **proxy_checker.py** — честная диагностика: "TCP доступен, но MTProto не работает"
- **proxy_checker.py** — статус PARTIAL вместо TCP OK когда MTProto не работает
- **proxy_checker.py** — обработка ValueError/OSError в MTProto-проверке
- **bot.py** — утечка SOCKS-сессии: connector корректно закрывается
- **handlers.py** — заменён deprecated `asyncio.get_event_loop()` на `get_running_loop()`
- **handlers.py** — обработка ошибок при удалении сообщений
- **handlers.py** — валидация индексов в `cb_server_select`, `cb_users_page`, `cb_user_toggle`
- **keyboards.py** — удалён неиспользуемый параметр `has_result`
- **scheduler.py** — убран избыточный catch `(ApiError, Exception)`
- **sysinfo.py** — заменён deprecated `asyncio.get_event_loop()` на `get_running_loop()`
- **formatters.py** — удалено дублирование `_now_str()`
- **export_toml.py** — путь к конфигу настраивается через `TELEMT_CONFIG_PATH`

## README

- Пошаговая установка на Ubuntu/Debian/CentOS/Alpine
- Systemd unit-файлы для бота и агента
- Настройка агентов проверки прокси
- Полная таблица конфигурации
