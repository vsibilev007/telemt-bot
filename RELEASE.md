# Release: Полная диагностика узла + бэкап через API + 3.4.18

## Диагностика узла (новое)

- **Команда `/check tg://proxy?...`** — полная диагностика узла
- Кнопка **🔍 Проверить прокси** теперь тоже использует полную диагностику
- Проверки: DNS резолв (IPv4+IPv6), TCP прокси, TCP SSH (22), Ping (ICMP), MTProto
- Вывод: статусы по каждому протоколу, диагностика, время проверки, итоговый статус (OK/PARTIAL/FAIL)
- Агенты (RU и др.) проверяются параллельно

## Бэкап конфигурации (новое)

- **📤 Бэкап** теперь работает через API (`GET /v1/config`), а не чтением с диска
- JSON-ответ конвертируется в TOML-файл
- В имени файла и caption — revision конфига
- Не требует доступа к файловой системе сервера

## API Telemt 3.4.14-3.4.18

- **Сброс квоты** — кнопка «🔄 Сбросить квоту» в карточке клиента (`POST /v1/users/{username}/reset-quota`)
- **api_client.py** — методы `reset_user_quota()`, `get_config()`, `patch_config()`

## Исправления

- **proxy_checker.py** — DNS резолв теперь параллельный (не блокирует TCP/SSH/Ping)
- **proxy_checker.py** — честная диагностика: "TCP доступен, но MTProto не работает" вместо "сервис отвечает штатно"
- **proxy_checker.py** — статус PARTIAL вместо TCP OK когда MTProto не работает
- **bot.py** — утечка SOCKS-сессии: connector корректно закрывается
- **handlers.py** — заменён deprecated `asyncio.get_event_loop()` на `get_running_loop()` (2 места)
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
