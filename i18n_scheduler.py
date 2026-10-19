"""Тексты алертов и фоновых джоб (scheduler.py)."""

SCHEDULER: dict[str, dict[str, str]] = {
    # ─── Заголовок алерта ───────────────────────────────────────────────────
    "sch.alert_header": {"ru": "🚨 <b>Алерт</b>", "en": "🚨 <b>Alert</b>"},

    # ─── Статус сервера ────────────────────────────────────────────────────
    "sch.status_down":   {"ru": "🔴 <b>{srv}</b> — статус изменился: <b>{status}</b>",
                          "en": "🔴 <b>{srv}</b> — status changed: <b>{status}</b>"},
    "sch.status_up":     {"ru": "🟢 <b>{srv}</b> — статус восстановлен: <b>OK</b>",
                          "en": "🟢 <b>{srv}</b> — status recovered: <b>OK</b>"},
    "sch.unreachable":   {"ru": "🔴 <b>{srv}</b> — сервер недоступен: {err}",
                          "en": "🔴 <b>{srv}</b> — server unreachable: {err}"},

    # ─── Готовность (not_ready) ────────────────────────────────────────────
    "sch.reason_admission": {"ru": "приём соединений закрыт",
                             "en": "admission is closed"},
    "sch.reason_upstreams": {"ru": "нет здоровых upstream'ов",
                             "en": "no healthy upstreams"},
    "sch.not_ready":        {"ru": "⚠️ <b>{srv}</b> — не принимает новых клиентов: {reason}",
                             "en": "⚠️ <b>{srv}</b> — not accepting new clients: {reason}"},
    "sch.not_ready_ok":     {"ru": "🟢 <b>{srv}</b> — готовность восстановлена: принимает клиентов",
                             "en": "🟢 <b>{srv}</b> — readiness restored: accepting clients"},

    # ─── Соединения / writers / версия ─────────────────────────────────────
    "sch.conn_spike":   {"ru": "⚡ <b>{srv}</b> — всплеск соединений: {prev:,} → {cur:,} (+{pct:.0f}%)",
                         "en": "⚡ <b>{srv}</b> — connection spike: {prev:,} → {cur:,} (+{pct:.0f}%)"},
    "sch.writers_low":  {"ru": "⚠️ <b>{srv}</b> — ME Writers coverage: {coverage:.0f}%",
                         "en": "⚠️ <b>{srv}</b> — ME Writers coverage: {coverage:.0f}%"},
    "sch.version_new":  {"ru": "🏷 <b>{srv}</b> — обновление telemt: <b>v{old}</b> → <b>v{new}</b>",
                         "en": "🏷 <b>{srv}</b> — telemt update: <b>v{old}</b> → <b>v{new}</b>"},

    # ─── Счётчики handshake/bad clients ────────────────────────────────────
    "sch.bad_unknown_sni":  {"ru": "⚠️ <b>{srv}</b> — неизвестный SNI: +{n} за 2 мин",
                             "en": "⚠️ <b>{srv}</b> — unknown SNI: +{n} in 2 min"},
    "sch.hs_timeout":       {"ru": "⚠️ <b>{srv}</b> — всплеск handshake timeout: +{n} за 2 мин",
                             "en": "⚠️ <b>{srv}</b> — handshake timeout spike: +{n} in 2 min"},
    "sch.bad_client":       {"ru": "⚠️ <b>{srv}</b> — всплеск плохих TLS клиентов: +{n} за 2 мин",
                             "en": "⚠️ <b>{srv}</b> — bad TLS client spike: +{n} in 2 min"},
    "sch.hs_conn_reset":    {"ru": "⚠️ <b>{srv}</b> — сброс соединений при handshake: +{n} за 2 мин",
                             "en": "⚠️ <b>{srv}</b> — connection resets during handshake: +{n} in 2 min"},

    # ─── Квота клиента ─────────────────────────────────────────────────────
    "sch.quota_warn":   {"ru": "📊 <b>{srv}</b> — клиент <code>{user}</code> использовал {pct:.0f}% квоты ({used} / {quota})",
                         "en": "📊 <b>{srv}</b> — client <code>{user}</code> used {pct:.0f}% of quota ({used} / {quota})"},

    # ─── Джобы ─────────────────────────────────────────────────────────────
    "sch.job_failed":     {"ru": "Джоба [%s] упала с ошибкой: %s", "en": "Job [%s] failed: %s"},
    "sch.traffic_collected": {"ru": "Трафик собран: %s (%d users)", "en": "Traffic collected: %s (%d users)"},
    "sch.collect_api_err": {"ru": "API ошибка сбора трафика [%s]: %s", "en": "API error collecting traffic [%s]: %s"},
    "sch.collect_err":    {"ru": "Ошибка сбора трафика [%s]: %s", "en": "Traffic collection error [%s]: %s"},
    "sch.check_err":      {"ru": "Ошибка проверки [%s]: %s", "en": "Health check error [%s]: %s"},
    "sch.cleanup_done":   {"ru": "Очистка старых данных выполнена", "en": "Old data cleanup done"},
    "sch.scheduler_on":   {"ru": "Scheduler запущен (%d задач)", "en": "Scheduler started (%d jobs)"},
    "sch.scheduler_off":  {"ru": "Scheduler остановлен", "en": "Scheduler stopped"},
    "sch.lite_on":        {"ru": "Lite mode — scheduler и алерты отключены",
                           "en": "Lite mode — scheduler and alerts disabled"},
    "sch.alert_send_err": {"ru": "Не удалось отправить алерт user_id=%d: %s",
                           "en": "Failed to send alert to user_id=%d: %s"},
    "sch.session_close_err": {"ru": "Не удалось закрыть сессию [%s]: %s",
                              "en": "Failed to close session [%s]: %s"},
    "sch.cleanup_start":  {"ru": "Очистка старых данных…", "en": "Cleaning old data…"},
}
