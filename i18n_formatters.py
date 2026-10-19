"""Строки formatters.py — тексты ответов (prefix: fmt.)."""

FORMATTERS: dict[str, dict[str, str]] = {
    # ─── Общие ──────────────────────────────────────────────────────────────
    "fmt.common.connect":       {"ru": "Подключить", "en": "Connect"},
    "fmt.common.ms":            {"ru": "мс", "en": "ms"},
    "fmt.common.per_s":         {"ru": "с", "en": "s"},
    "fmt.common.per_min":       {"ru": "мин", "en": "min"},
    "fmt.common.min":           {"ru": "мин", "en": "min"},
    "fmt.common.updated":       {"ru": "Обновлено", "en": "Updated"},
    "fmt.common.updated_short": {"ru": "Обновлён", "en": "Updated"},
    "fmt.common.total":         {"ru": "Всего", "en": "Total"},
    "fmt.common.empty_list":    {"ru": "Список пуст", "en": "List is empty"},
    "fmt.common.reason":        {"ru": "Причина", "en": "Reason"},
    "fmt.common.age":           {"ru": "age", "en": "age"},
    "fmt.rt.backoff":           {"ru": "Backoff", "en": "Backoff"},
    "fmt.rt.budget":            {"ru": "Budget", "en": "Budget"},
    "fmt.common.backoff":       {"ru": "Backoff", "en": "Backoff"},
    "fmt.common.budget":        {"ru": "Budget", "en": "Budget"},
    "fmt.common.attempts":      {"ru": "Попыток", "en": "Attempts"},
    "fmt.common.attempts_short": {"ru": "попыток", "en": "attempts"},
    "fmt.common.ok_of":         {"ru": "Успешных", "en": "Successful"},
    "fmt.common.ok_short":      {"ru": "успешных", "en": "successful"},
    "fmt.common.errors_of":     {"ru": "Ошибок", "en": "errors"},
    "fmt.common.entries":       {"ru": "записей", "en": "entries"},
    "fmt.common.enabled":       {"ru": "Активен", "en": "Enabled"},
    "fmt.common.list":          {"ru": "Список:", "en": "List:"},
    "fmt.common.unique":        {"ru": "Уникальных", "en": "Unique"},
    "fmt.common.window":        {"ru": "Окно", "en": "Window"},
    "fmt.common.dropped":       {"ru": "Отброшено", "en": "Dropped"},
    "fmt.common.timeout_short": {"ru": "timeout", "en": "timeout"},
    "fmt.common.no_addresses":  {"ru": "— нет активных адресов —", "en": "— no active addresses —"},
    "fmt.common.no_events":     {"ru": "— нет событий —", "en": "— no events —"},
    "fmt.common.no_links":      {"ru": "— нет ссылок —", "en": "— no links —"},
    "fmt.common.more_suffix":   {"ru": "… ещё {n}", "en": "… {n} more"},

    # ─── fmt_uptime единицы ─────────────────────────────────────────────────
    "fmt.up.d": {"ru": "д", "en": "d"},
    "fmt.up.h": {"ru": "ч", "en": "h"},
    "fmt.up.m": {"ru": "м", "en": "m"},
    "fmt.up.s": {"ru": "с", "en": "s"},

    # ─── Дашборд ─────────────────────────────────────────────────────────────
    "fmt.dash.status":      {"ru": "Статус", "en": "Status"},
    "fmt.dash.version":     {"ru": "Версия", "en": "Version"},
    "fmt.dash.connections": {"ru": "Соединения", "en": "Connections"},
    "fmt.dash.bad":         {"ru": "Плохих", "en": "Bad"},
    "fmt.dash.online":      {"ru": "Онлайн", "en": "Online"},
    "fmt.dash.bad_title":   {"ru": "Плохие соединения", "en": "Bad connections"},
    "fmt.dash.hs_title":    {"ru": "Фейлы handshake", "en": "Handshake failures"},
    "fmt.dash.accepting":   {"ru": "Принимает", "en": "Accepting"},

    # ─── Классы ошибок дашборда ─────────────────────────────────────────────
    "fmt.bad.tls":          {"ru": "Плохой TLS клиент", "en": "Bad TLS client"},
    "fmt.bad.direct_off":   {"ru": "Прямой режим отключён", "en": "Direct modes disabled"},
    "fmt.bad.unknown_sni":  {"ru": "Неизвестный SNI", "en": "Unknown SNI"},
    "fmt.bad.bad_chello":   {"ru": "Некорректный ClientHello", "en": "Malformed ClientHello"},
    "fmt.hs.timeout":       {"ru": "Таймаут", "en": "Timeout"},
    "fmt.hs.eof":           {"ru": "Обрыв соединения", "en": "Connection dropped"},
    "fmt.hs.reset":         {"ru": "Сброс соединения", "en": "Connection reset"},
    "fmt.hs.other":         {"ru": "Прочее", "en": "Other"},

    # ─── Пользователи ────────────────────────────────────────────────────────
    "fmt.users.header":    {"ru": "Пользователи", "en": "Users"},
    "fmt.users.clients":   {"ru": "Клиенты", "en": "Clients"},
    "fmt.users.online":    {"ru": "онлайн", "en": "online"},
    "fmt.users.total":     {"ru": "всего", "en": "total"},
    "fmt.users.disabled":  {"ru": "Клиент отключён", "en": "Client disabled"},
    "fmt.users.conns":     {"ru": "Соединений", "en": "Connections"},
    "fmt.users.traffic":   {"ru": "Трафик", "en": "Traffic"},
    "fmt.users.active":    {"ru": "активных", "en": "active"},
    "fmt.users.recent":    {"ru": "недавних", "en": "recent"},
    "fmt.users.limits":    {"ru": "Лимиты", "en": "Limits"},
    "fmt.users.quota":     {"ru": "Квота", "en": "Quota"},
    "fmt.users.expires":   {"ru": "Истекает", "en": "Expires"},
    "fmt.users.links":     {"ru": "Ссылок", "en": "Links"},

    # ─── Квоты ───────────────────────────────────────────────────────────────
    "fmt.quota.title":   {"ru": "Квоты пользователей", "en": "User quotas"},
    "fmt.quota.none":    {"ru": "Квоты не заданы", "en": "No quotas configured"},
    "fmt.quota.not_set": {"ru": "квота не задана", "en": "quota not set"},

    # ─── Ссылки ──────────────────────────────────────────────────────────────
    "fmt.links.title":    {"ru": "Ссылки", "en": "Links"},
    "fmt.links.tap_hint": {"ru": "Нажмите «Подключить», чтобы добавить прокси",
                           "en": "Tap «Connect» to add the proxy"},

    # ─── Runtime ─────────────────────────────────────────────────────────────
    "fmt.rt.stage":      {"ru": "Стадия", "en": "Stage"},
    "fmt.rt.accepting":  {"ru": "Принимает соед.", "en": "Accepting"},
    "fmt.rt.mode":       {"ru": "Режим", "en": "Mode"},
    "fmt.rt.time":       {"ru": "Время", "en": "Time"},
    "fmt.rt.ready":      {"ru": "Готов", "en": "Ready"},
    "fmt.rt.components": {"ru": "Компоненты:", "en": "Components:"},

    # ─── Соединения (runtime edge) ───────────────────────────────────────────
    "fmt.conns.active_users": {"ru": "Активных юзеров", "en": "Active users"},
    "fmt.conns.top":          {"ru": "Топ по соединениям:", "en": "Top by connections:"},

    # ─── TLS fingerprints ────────────────────────────────────────────────────
    "fmt.fp.requires_beobachten": {"ru": "Требуется general.beobachten = true в конфиге",
                                   "en": "general.beobachten = true is required in config"},
    "fmt.fp.bad_probe":           {"ru": "плохих/зондов", "en": "bad/probe"},
    "fmt.fp.by_fp":               {"ru": "По fingerprint:", "en": "By fingerprint:"},
    "fmt.fp.bad_by_ip":           {"ru": "Плохие по IP:", "en": "Bad by IP:"},
    "fmt.fp.by_user":             {"ru": "По пользователям:", "en": "By user:"},

    # ─── Активные IP ─────────────────────────────────────────────────────────
    "fmt.ips.title": {"ru": "Активные IP", "en": "Active IPs"},

    # ─── WEB sessions ────────────────────────────────────────────────────────
    "fmt.web.no_sessions": {"ru": "Активных сессий нет.", "en": "No active sessions."},
    "fmt.web.shown_of":    {"ru": "Показано {n} из {total} (scan limit)",
                            "en": "Shown {n} of {total} (scan limit)"},
    "fmt.web.more_cursor": {"ru": "Есть ещё (cursor: {cursor}…)",
                            "en": "More available (cursor: {cursor}…)"},
    "fmt.web.ws_active":   {"ru": "WebSocket: активен", "en": "WebSocket: active"},
}
