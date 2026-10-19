"""Строки keyboards.py — тексты кнопок (prefix: kb.)."""

KEYBOARDS: dict[str, dict[str, str]] = {
    # ─── Главное меню ────────────────────────────────────────────────────────
    "kb.main.status":       {"ru": "{icon} Состояние сервера", "en": "{icon} Server status"},
    "kb.main.users":        {"ru": "👥 Все клиенты", "en": "👥 All clients"},
    "kb.main.new_client":   {"ru": "➕ Новый клиент", "en": "➕ New client"},
    "kb.main.backup":       {"ru": "📤 Бэкап", "en": "📤 Backup"},
    "kb.main.traffic_report": {"ru": "📊 Отчёт по трафику", "en": "📊 Traffic report"},
    "kb.main.expiring":     {"ru": "⚠️ Истекающие", "en": "⚠️ Expiring"},
    "kb.main.security":     {"ru": "🔒 Безопасность", "en": "🔒 Security"},
    "kb.main.proxy_check":  {"ru": "🔍 Проверить прокси", "en": "🔍 Check proxy"},
    "kb.main.config":       {"ru": "⚙️ Конфиг", "en": "⚙️ Config"},

    # ─── Общие кнопки ────────────────────────────────────────────────────────
    "kb.common.refresh":    {"ru": "🔄 Обновить", "en": "🔄 Refresh"},
    "kb.common.menu":       {"ru": "◀️ Меню", "en": "◀️ Menu"},
    "kb.common.back":       {"ru": "◀️ Назад", "en": "◀️ Back"},

    # ─── Список юзеров / массовый выбор ─────────────────────────────────────
    "kb.users.new":         {"ru": "➕ Новый", "en": "➕ New"},
    "kb.users.bulk":        {"ru": "➕➕ Массово", "en": "➕➕ Bulk"},
    "kb.users.search":      {"ru": "🔍 Поиск", "en": "🔍 Search"},
    "kb.users.select":      {"ru": "☑️ Выбрать", "en": "☑️ Select"},
    "kb.users.extra":       {"ru": "⚙️ Ещё", "en": "⚙️ More"},
    "kb.users.back_menu":   {"ru": "◀ Назад в меню", "en": "◀ Back to menu"},
    "kb.users.sel_disable": {"ru": "🔴 Откл ({n})", "en": "🔴 Disable ({n})"},
    "kb.users.sel_enable":  {"ru": "✅ Вкл ({n})", "en": "✅ Enable ({n})"},
    "kb.users.sel_delete":  {"ru": "🗑 Удалить ({n})", "en": "🗑 Delete ({n})"},
    "kb.users.sel_done":    {"ru": "✔ Готово", "en": "✔ Done"},
    "kb.users.sel_del_yes": {"ru": "🗑 Да, удалить ({count})", "en": "🗑 Yes, delete ({count})"},
    "kb.users.sel_cancel":  {"ru": "◀ Отмена", "en": "◀ Cancel"},

    # ─── Карточка юзера ──────────────────────────────────────────────────────
    "kb.user.enabled":      {"ru": "🟢 Вкл", "en": "🟢 On"},
    "kb.user.disabled":     {"ru": "🔴 Выкл", "en": "🔴 Off"},
    "kb.user.edit":         {"ru": "✏️ Редактировать", "en": "✏️ Edit"},
    "kb.user.delete":       {"ru": "🗑️ Удалить", "en": "🗑️ Delete"},
    "kb.user.links":        {"ru": "🔗 Ссылки", "en": "🔗 Links"},
    "kb.user.rotate":       {"ru": "🔄 Сменить секрет", "en": "🔄 Rotate secret"},
    "kb.user.reset_quota":  {"ru": "🔄 Сбросить квоту", "en": "🔄 Reset quota"},
    "kb.user.traffic":      {"ru": "📊 История трафика", "en": "📊 Traffic history"},
    "kb.user.to_list":      {"ru": "◀️ К списку", "en": "◀️ To list"},
    "kb.user.del_yes":      {"ru": "✅ Да, удалить", "en": "✅ Yes, delete"},
    "kb.user.del_cancel":   {"ru": "❌ Отмена", "en": "❌ Cancel"},
    "kb.user.f_secret":     {"ru": "🔑 Секрет", "en": "🔑 Secret"},
    "kb.user.f_expiration": {"ru": "📅 Срок действия", "en": "📅 Expiration"},
    "kb.user.f_quota":      {"ru": "💾 Квота", "en": "💾 Quota"},
    "kb.user.f_up":         {"ru": "⬆️ Лимит upload", "en": "⬆️ Upload limit"},
    "kb.user.f_down":       {"ru": "⬇️ Лимит download", "en": "⬇️ Download limit"},

    # ─── Ещё (extra) ─────────────────────────────────────────────────────────
    "kb.extra.expiring":        {"ru": "⏰ Истекающие", "en": "⏰ Expiring"},
    "kb.extra.quota":           {"ru": "📊 Квоты", "en": "📊 Quotas"},
    "kb.extra.active_ips":      {"ru": "🌐 Активные IP", "en": "🌐 Active IPs"},
    "kb.extra.delete_expired":  {"ru": "🧹 Удалить истёкших", "en": "🧹 Delete expired"},
    "kb.extra.more":            {"ru": "◀️ Ещё", "en": "◀️ More"},

    # ─── Трафик ──────────────────────────────────────────────────────────────
    "kb.tp.text":       {"ru": "📋 Текстовый отчёт", "en": "📋 Text report"},
    "kb.tp.chart":      {"ru": "📈 График", "en": "📈 Chart"},
    "kb.tp.chart_top":  {"ru": "📈 График топ-15", "en": "📈 Top-15 chart"},
    "kb.tp.d1":         {"ru": "24ч", "en": "24h"},
    "kb.tp.d7":         {"ru": "7 дней", "en": "7 days"},
    "kb.tp.d14":        {"ru": "14 дней", "en": "14 days"},
    "kb.tp.d30":        {"ru": "30 дней", "en": "30 days"},

    # ─── Безопасность / прокси / конфиг ──────────────────────────────────────
    "kb.security.limits":   {"ru": "⚙️ Лимиты", "en": "⚙️ Limits"},
    "kb.security.back":     {"ru": "◀️ Безопасность", "en": "◀️ Security"},
    "kb.proxy.again":       {"ru": "🔍 Проверить ещё", "en": "🔍 Check again"},
    "kb.cfg.apply":         {"ru": "💾 Применить", "en": "💾 Apply"},
    "kb.cfg.instant":       {"ru": "⚡ +instant", "en": "⚡ +instant"},
    "kb.cfg.drain":         {"ru": "🌙 +drain", "en": "🌙 +drain"},
    "kb.cfg.reload_instant": {"ru": "⚡ Reload instant", "en": "⚡ Reload instant"},
    "kb.cfg.reload_drain":  {"ru": "🌙 Reload drain", "en": "🌙 Reload drain"},
    "kb.cfg.to_section":    {"ru": "◀️ К секции", "en": "◀️ To section"},

    # ─── WEB Proxy ───────────────────────────────────────────────────────────
    "kb.web.status":          {"ru": "📊 Статус", "en": "📊 Status"},
    "kb.web.sessions":        {"ru": "👥 Сессии", "en": "👥 Sessions"},
    "kb.web.pause":           {"ru": "⏸ Пауза", "en": "⏸ Pause"},
    "kb.web.debug_clear":     {"ru": "🧹 Очистить debug", "en": "🧹 Clear debug"},
    "kb.web.carrier_reset":   {"ru": "🔄 Сброс learning", "en": "🔄 Reset learning"},
    "kb.web.more":            {"ru": "▶️ Ещё", "en": "▶️ More"},
    "kb.web.close":           {"ru": "🚫 Закрыть", "en": "🚫 Close"},
    "kb.web.back_sessions":   {"ru": "◀️ Сессии", "en": "◀️ Sessions"},

    # ─── Типы алертов (значения ALERT_LABELS — ключи, тексты здесь) ─────────
    "kb.alert.status_down":      {"ru": "Падение сервера", "en": "Server down"},
    "kb.alert.status_up":        {"ru": "Восстановление", "en": "Recovered"},
    "kb.alert.not_ready":        {"ru": "Готовность (admission/upstreams)",
                                  "en": "Readiness (admission/upstreams)"},
    "kb.alert.conn_spike":       {"ru": "Всплеск соединений", "en": "Connection spike"},
    "kb.alert.writers_low":      {"ru": "Writers coverage", "en": "Writers coverage"},
    "kb.alert.version_change":   {"ru": "Обновление версии", "en": "Version update"},
    "kb.alert.bad_unknown_sni":  {"ru": "Неизвестный SNI", "en": "Unknown SNI"},
    "kb.alert.hs_timeout_spike": {"ru": "Всплеск HS timeout", "en": "HS timeout spike"},
    "kb.alert.bad_client_spike": {"ru": "Всплеск плохих TLS", "en": "Bad TLS spike"},
    "kb.alert.hs_conn_reset":    {"ru": "Сброс при handshake", "en": "Reset during handshake"},
    "kb.alert.quota_warn":       {"ru": "Превышение квоты", "en": "Quota exceeded"},
}
