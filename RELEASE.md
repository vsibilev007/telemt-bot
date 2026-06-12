# Release: bug fixes + README rewrite + 3.4.18 features

## Новый функционал (3.4.14-3.4.18)

- **handlers.py** — сброс квоты пользователя (`POST /v1/users/{username}/reset-quota`, 3.4.11+)
- **handlers.py** — просмотр конфигурации (`GET /v1/config`, 3.4.16+)
- **api_client.py** — добавлены методы `reset_user_quota()`, `get_config()`, `patch_config()`
- **keyboards.py** — кнопка «🔄 Сбросить квоту» в карточке клиента
- **keyboards.py** — пункт «⚙️ Конфигурация» в главном меню
- **formatters.py** — форматер `format_config()` для TOML-конфига

## Исправления

- **bot.py** — утечка SOCKS-сессии: connector теперь корректно закрывается при остановке бота
- **formatters.py** — удалено дублирование `_now_str()`
- **handlers.py** — заменён deprecated `asyncio.get_event_loop()` на `get_running_loop()`
- **handlers.py** — добавлена обработка ошибок при удалении сообщений (try/except)
- **handlers.py** — убран повторный вызов `get_client()` в `cb_traffic_report`
- **handlers.py** — удалён лишний импорт `BufferedInputFile`/`InputMediaPhoto`
- **handlers.py** — добавлена валидация индексов в `cb_server_select`, `cb_users_page`, `cb_user_toggle`
- **keyboards.py** — удалён неиспользуемый параметр `has_result` в `proxy_check_kb()`
- **scheduler.py** — убран избыточный catch `(ApiError, Exception)` → `Exception`
- **sysinfo.py** — заменён deprecated `asyncio.get_event_loop()` на `get_running_loop()`
- **export_toml.py** — путь к `telemt.toml` теперь настраивается через `TELEMT_CONFIG_PATH`

## README

- Полностью переписан: пошаговая установка на Ubuntu/Debian/CentOS/Alpine
- Добавлены 3 варианта копирования агента на удалённый сервер (curl/scp/git)
- Готовые systemd unit-файлы для бота и агента
- Полная таблица конфигурации с описанием всех переменных
