# Release: Docker-образ + CI/CD + Диагностика узла + Runtime Reload + 3.4.25

## Runtime Reload (3.4.25+)

- **Команда /reload** — безопасная перезагрузка runtime-конфигурации без перезапуска процесса
  - `/reload instant` — мгновенное переключение, старые сессии отменяются
  - `/reload drain` — плавное завершение старых сессий
- **Команда /reload_status** — проверка статуса reload операции
- **api_client.py** — методы system_reload(), get_reload_status()
- **PATCH /v1/config** — поддержка параметра `?reload=instant|drain` для patch + reload за один запрос

## Docker-образ (новое)

- **Производственный Dockerfile** — двухстадийная сборка (builder → final) на python:3.11-slim-bookworm
- **Non-root пользователь** appuser (UID 10001) — контейнер не запускается от root
- **Hardening**: read_only, cap_drop: ALL, no-new-privileges, mem_limit: 256m, pids_limit: 256
- **Named volume** telemt-data:/data — безопасное хранение БД с правильными правами
- **Trim слоя**: удаляются __pycache__, тесты пакетов, .pyc/.pyx/.pyi — меньше итогового размера

## CI/CD (новое)

- **GitHub Actions** — пайплайн lint → build → scan → push при пуше в main и по тегам v*.*.*
- **Lint**: ruff check на каждый PR
- **Trivy scan** — сканирование HIGH/CRITICAL уязвимостей перед пушем; сборка падает при наличии фиксов
- **GHCR**: образ публикуется в ghcr.io с тегами latest, v1.2.3, 1.2, sha-abc1234
- **GHA cache**: BuildKit кеширует слои между запусками — быстрые повторные сборки

## Диагностика узла (новое)

- **Команда /check tg://proxy?...** — полная диагностика узла
- Кнопка **Проверить прокси** теперь тоже использует полную диагностику
- Проверки: TCP, TLS, MTProto (raw), стабильность, DPI-детекция, DNS, GeoIP
- Вывод: статусы по каждому протоколу, диагностика, время проверки, итоговый статус (OK/PARTIAL/FAIL)
- Агенты (RU и др.) проверяются параллельно

## Ссылки с доменами маскировки (новое)

- **Карточка клиента** — над каждой TLS-ссылкой показывается домен маскировки (SNI)
- **QR-кнопки** — показывают домен вместо generic QR (📷 domain.name)
- Извлечение SNI из FakeTLS-секрета автоматическое

## API Telemt 3.4.14-3.4.25

- **Сброс квоты** — кнопка "Сбросить квоту" в карточке клиента (POST /v1/users/{username}/reset-quota)
- **api_client.py** — методы reset_user_quota(), get_config(), patch_config(), system_reload(), get_reload_status()
- **Редактирование конфига** — кнопка "Конфиг" в главном меню, 6 секций через PATCH /v1/config
- **Runtime reload** — /reload instant|drain, /reload_status, PATCH /v1/config?reload=instant

## Бэкап конфигурации

- **Бэкап** — чтение полного telemt.toml с диска (API не отдаёт секции access/server/network)

## Исправления безопасности (зависимости)

- Pillow 12.1.1 → 12.3.0
- setuptools обновлен в Docker-образе

## Исправления

- **proxy_checker.py** — переписан на основе check_tg_proxy: raw MTProto, стабильность, DPI, GeoIP
- **proxy_checker.py** — обработка ValueError/OSError в MTProto-проверке
- **bot.py** — упрощена логика прокси (AiohttpSession(proxy=))
- **handlers.py** — исправлен fields is {} → fields == {}
- **handlers.py** — заменён deprecated asyncio.get_event_loop() на get_running_loop()
- **handlers.py** — обработка ошибок при удалении сообщений
- **handlers.py** — валидация индексов в cb_server_select, cb_users_page, cb_user_toggle
- **scheduler.py** — heartbeat-файл для Docker HEALTHCHECK
- **scheduler.py** — убран избыточный catch (ApiError, Exception)
- **database.py** — абсолютный путь к БД для systemd
- **formatters.py** — удалено дублирование _now_str()
- **export_toml.py** — путь к конфигу настраивается через TELEMT_CONFIG_PATH

## README

- Пошаговая установка на Ubuntu/Debian/CentOS/Alpine
- Systemd unit-файлы для бота и агента
- Docker-установка
- Настройка агентов проверки прокси
- Полная таблица конфигурации
