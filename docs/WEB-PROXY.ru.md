# WEB Proxy

[🇬🇧 WEB Proxy Setup](WEB-PROXY.en.md)

---

## Обзор

WEB Proxy режим проксирует MTProto трафик через HTTPS/WebSocket, совместимый с типом прокси `WEB` в Telegram Desktop. Доступен в Telemt 3.5.5+.

## Возможности

| Возможность | Описание |
|-------------|----------|
| **Статус** | Lifecycle, runtime, limits, streams, sessions, learning, debug |
| **Сессии** | Список активных WEB-сессий с пагинацией и деталями |
| **Управление** | Закрытие сессий, очистка debug, сброс carrier learning |
| **Ссылки** | Автоматическая генерация `tg://webproxy` ссылок |
| **Авто-профили** | WEB-профиль автоматически добавляется/удаляется при создании/удалении пользователя |

## Меню бота

| Кнопка | Описание |
|--------|----------|
| 📊 Статус | WEB runtime lifecycle, limits, streams, sessions |
| 👥 Сессии | Список активных сессий с фильтрами |
| 🧹 Очистить debug | Очистка debug-записей |
| 🔄 Сброс learning | Сброс carrier learning evidence |

## Генерация ссылок

Для серверов с Telemt 3.5.5+ бот генерирует WEB-ссылки:

```
WEB Proxy:
🌐 proxy.example.com
tg://webproxy?server=proxy.example.com&secret=dd...
```

Для серверов с Telemt 3.4.25 и ниже — только TLS-ссылки (старый формат).

## Проверка версии

Бот автоматически определяет версию Telemt и показывает соответствующие ссылки:

| Версия Telemt | Показываемые ссылки |
|---------------|---------------------|
| 3.5.5+ | WEB Proxy + MTProxy |
| 3.4.25 и ниже | Только MTProxy |

## API endpoints

| Endpoint | Описание |
|----------|----------|
| `GET /v1/runtime/web/status` | WEB runtime lifecycle и статус |
| `GET /v1/runtime/web/sessions` | Список активных сессий |
| `GET /v1/runtime/web/sessions/{ref}` | Детали сессии |
| `POST /v1/runtime/web/sessions/close` | Закрытие сессий |
| `POST /v1/runtime/web/debug/clear` | Очистка debug |
| `POST /v1/runtime/web/carrier-learning/reset` | Сброс carrier learning |

## Конфигурация Telemt

### Минимальный WEB конфиг

```toml
[general.links]
show = ["web-user"]
public_host = "proxy.example.com"
public_port = 443

[[server.listeners]]
ip = "127.0.0.1"
port = 18080
transport = "web"

[web]
enabled = true
carrier = "https"

[[web.vhosts]]
host = "proxy.example.com"
public_addr = "203.0.113.10:443"

[web.vhosts.decoy]
mode = "http_upstream"
upstream = "http://127.0.0.1:18081"

[[web.vhosts.profiles]]
user = "web-user"
secret_mode = "dd"
max_sessions = 8
max_streams = 512
max_streams_per_session = 64
```

### TLS терминация в NGINX

```nginx
map $http_upgrade $telemt_connection_upgrade {
    default upgrade;
    ''      '';
}

upstream telemt_web {
    server 127.0.0.1:18080;
    keepalive 64;
}

server {
    listen 443 ssl;
    http2 on;
    server_name proxy.example.com;
    access_log off;

    ssl_certificate     /etc/letsencrypt/live/proxy.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/proxy.example.com/privkey.pem;

    client_max_body_size 2m;

    location / {
        proxy_pass http://telemt_web;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $telemt_connection_upgrade;

        proxy_connect_timeout 5s;
        proxy_send_timeout 65s;
        proxy_read_timeout 65s;
        proxy_request_buffering off;
        proxy_buffering off;
        proxy_next_upstream off;
    }
}
```

---

## См. также

- [Инструкция по быстрому запуску](QUICKSTART.ru.md)
- [Справочник конфигурации](CONFIGURATION.ru.md)
- [Развёртывание](DEPLOYMENT.ru.md)
