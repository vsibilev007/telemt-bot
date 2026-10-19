"""Общие строки: описания команд, главное меню, базовые кнопки/ошибки."""

CORE: dict[str, dict[str, str]] = {
    # ─── Описания команд в меню Telegram (bot.py) ──────────────────────────
    "cmd.menu":        {"ru": "Главное меню", "en": "Main menu"},
    "cmd.help":        {"ru": "Справка по боту", "en": "Bot help"},
    "cmd.adduser":     {"ru": "Быстро создать клиента", "en": "Quick create client"},
    "cmd.find":        {"ru": "Поиск клиента по имени", "en": "Find client by name"},
    "cmd.id":          {"ru": "Ваш Telegram ID", "en": "Your Telegram ID"},
    "cmd.alerts":      {"ru": "Настройки алертов", "en": "Alert settings"},
    "cmd.alert_log":   {"ru": "История последних 20 алертов", "en": "Last 20 alerts"},
    "cmd.check":       {"ru": "Диагностика узла по прокси-ссылке", "en": "Node diagnostics via proxy link"},
    "cmd.reload":      {"ru": "Runtime reload без перезапуска", "en": "Runtime reload without restart"},

    # ─── Запуск/остановка (bot.py) ──────────────────────────────────────────
    "cmd.lite_suffix":  {"ru": " [lite]", "en": " [lite]"},
    "cmd.menu_set":     {"ru": "Меню бота установлено (%d команд)%s",
                         "en": "Bot menu set (%d commands)%s"},
    "cmd.lang_set":     {"ru": "Язык интерфейса: %s", "en": "UI language: %s"},
    "cmd.tg_proxy":     {"ru": "Telegram прокси: %s", "en": "Telegram proxy: %s"},
    "cmd.started":      {"ru": "Бот запущен | серверов: %d | юзеров: %d",
                         "en": "Bot started | servers: %d | users: %d"},
    "cmd.stopped":      {"ru": "Бот остановлен", "en": "Bot stopped"},

    # ─── Базовые кнопки (повторяются в нескольких клавиатурах) ─────────────
    "common.back_menu":  {"ru": "◀ Меню", "en": "◀ Menu"},
    "common.back":       {"ru": "◀ Назад", "en": "◀ Back"},
    "common.cancel":     {"ru": "❌ Отмена", "en": "❌ Cancel"},
    "common.refresh":    {"ru": "🔄 Обновить", "en": "🔄 Refresh"},
    "common.yes":        {"ru": "✅ Да", "en": "✅ Yes"},
    "common.no":         {"ru": "❌ Нет", "en": "❌ No"},
    "common.users_list": {"ru": "👥 К списку", "en": "👥 To users"},

    # ─── Частые ошибки ──────────────────────────────────────────────────────
    "common.err_unknown":     {"ru": "❌ Ошибка: {err}", "en": "❌ Error: {err}"},
    "common.err_api":         {"ru": "❌ {err}", "en": "❌ {err}"},
    "common.err_no_users":    {"ru": "❌ Не удалось получить список", "en": "❌ Failed to fetch the list"},
    "common.err_lite":        {"ru": "⛔ Недоступно в lite-режиме", "en": "⛔ Not available in lite mode"},
    "common.err_web_runtime": {"ru": "❌ WEB runtime недоступен", "en": "❌ WEB runtime unavailable"},
}
