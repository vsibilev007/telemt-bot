"""Строки handlers.py — заполнено при переводе модуля (prefix: h.*).

Ключи строго соответствуют вызовам t() в handlers.py; аргументы — {name}-
плейсхолдеры из call-site. Литеральные фигурные скобки внутри значений (маркер
шаблона {n} в bulk) удвоены: vpn{{n}}.
"""

HANDLERS: dict[str, dict[str, str]] = {
    # ─── Общие каталоги (переиспользуются) ─────────────────────────────────
    "h.common.default_name": {"ru": "друг", "en": "friend"},
    "h.common.gathering": {"ru": "⏳ Собираю данные...", "en": "⏳ Gathering data..."},
    "h.common.counting": {"ru": "⏳ Считаю...", "en": "⏳ Counting..."},
    "h.common.more": {"ru": " …ещё {n}", "en": " …{n} more"},
    "h.common.more_nl": {"ru": "\n…ещё {n}", "en": "\n…{n} more"},
    "h.common.fetch_failed": {"ru": "❌ Не удалось получить список", "en": "❌ Failed to fetch users"},
    "h.common.to_list": {"ru": "👥 К списку", "en": "👥 To users"},
    "h.common.menu": {"ru": "◀️ Меню", "en": "◀️ Menu"},
    "h.common.lite": {"ru": "⛔ Недоступно в lite-режиме", "en": "⛔ Unavailable in lite mode"},
    "h.common.partial_result": {"ru": "⚠️ Частичный результат:", "en": "⚠️ Partial result:"},
    "h.common.err": {"ru": "❌ Ошибка: {err}", "en": "❌ Error: {err}"},
    "h.common.nodes_err": {"ru": "⚠️ Ошибка на узлах:\n{errors}", "en": "⚠️ Node errors:\n{errors}"},

    # ─── Кластер / lite ─────────────────────────────────────────────────────
    "h.cluster.node_err": {"ru": "🔴 Ошибка: {err}", "en": "🔴 Error: {err}"},
    "h.cluster.unreachable": {"ru": "🔴 <b>{srv}</b> — недоступен: {err}", "en": "🔴 <b>{srv}</b> — unreachable: {err}"},
    "h.cluster.title": {"ru": "⚙️ <b>Кластер: {group}</b>\n", "en": "⚙️ <b>Cluster: {group}</b>\n"},
    "h.lite_blocked": {"ru": "⛔ Команда недоступна в lite-режиме (LITE_MODE=true)", "en": "⛔ Command unavailable in lite mode (LITE_MODE=true)"},

    # ─── Старт ─────────────────────────────────────────────────────────────
    "h.start.hello": {
        "ru": "👋 <b>Привет, {name}!</b>\n\n"
              "Это бот управления <b>Telemt MTProxy</b>.\n\n"
              "<b>Основные команды:</b>\n"
              "  /menu — главное меню\n"
              "  /adduser имя [дней] — быстро создать клиента\n"
              "  /find запрос — поиск клиента по имени\n"
              "  /alerts — управление алертами\n"
              "  /alert_log — история последних алертов\n\n"
              "<i>Выберите действие в меню ниже 👇</i>",
        "en": "👋 <b>Hi, {name}!</b>\n\n"
              "This is the Telemt MTProxy admin bot.\n\n"
              "<b>Basic commands:</b>\n"
              "  /menu — main menu\n"
              "  /adduser name [days] — quick client create\n"
              "  /find query — search client by name\n"
              "  /alerts — alert settings\n"
              "  /alert_log — recent alerts\n\n"
              "<i>Choose an action in the menu below 👇</i>",
    },

    # ─── Сервер / sysinfo / dashboard ──────────────────────────────────────
    "h.server.bad_index": {"ru": "❌ Неверный индекс", "en": "❌ Invalid index"},
    "h.server.not_found": {"ru": "❌ Сервер не найден", "en": "❌ Server not found"},
    "h.sysinfo.title": {"ru": "🖥 <b>Состояние сервера — {srv}</b>\n\n", "en": "🖥 <b>Server status — {srv}</b>\n\n"},

    # ─── Отчёт по трафику (period selector) ────────────────────────────────
    "h.tr.menu": {"ru": "📊 <b>Отчёт по трафику</b>\n\nВыберите период:", "en": "📊 <b>Traffic report</b>\n\nPick a period:"},
    "h.tr.title": {"ru": "📊 <b>Отчёт по трафику — {srv}</b>", "en": "📊 <b>Traffic report — {srv}</b>"},
    "h.tr.sub": {"ru": "<i>Период: {days} дн  |  {users} клиентов  |  {active} онлайн</i>", "en": "<i>Period: {days} d  |  {users} clients  |  {active} online</i>"},
    "h.tr.total": {"ru": "<b>Всего за период: {total}</b>", "en": "<b>Total for period: {total}</b>"},
    "h.tr.expired_tag": {"ru": " 🔴истёк", "en": " 🔴expired"},
    "h.tr.soon_tag": {"ru": " ⚠️скоро", "en": " ⚠️soon"},
    "h.tr.row": {"ru": "   За период: <b>{period}</b>  |  Всего: {total}  |  {conns}🔌", "en": "   For period: <b>{period}</b>  |  Total: {total}  |  {conns}🔌"},
    "h.tr.more": {"ru": "\n<i>...и ещё {n} клиентов</i>", "en": "\n<i>...and {n} more clients</i>"},

    # ─── Список юзеров ─────────────────────────────────────────────────────
    "h.users.header": {"ru": "<b>👥 Клиенты{hint}</b>  {active} онлайн / {total} всего", "en": "<b>👥 Clients{hint}</b>  {active} online / {total} total"},
    "h.users.bad_page": {"ru": "❌ Неверная страница", "en": "❌ Invalid page"},
    "h.users.sel_header": {"ru": "<b>☑️ Выбрано {n}</b> из {total}\nОтмечено: {names}", "en": "<b>☑️ Selected {n}</b> of {total}\nMarked: {names}"},

    # ─── Массовые операции ─────────────────────────────────────────────────
    "h.bulk.nobody": {"ru": "❌ Никто не выбран", "en": "❌ Nobody selected"},
    "h.bulk.start_enable": {"ru": "⏳ Включаю {n} юзеров…", "en": "⏳ Enabling {n} users..."},
    "h.bulk.start_disable": {"ru": "⏳ Отключаю {n} юзеров…", "en": "⏳ Disabling {n} users..."},
    "h.bulk.enabled_many": {"ru": "Включены", "en": "Enabled"},
    "h.bulk.disabled_many": {"ru": "Отключены", "en": "Disabled"},
    "h.bulk.result_header": {"ru": "{icon} <b>{verb}: {ok} из {total}</b>", "en": "{icon} <b>{verb}: {ok} of {total}</b>"},
    "h.bulk.del_confirm": {"ru": "⚠️ <b>Удалить {n} юзеров?</b>", "en": "⚠️ <b>Delete {n} users?</b>"},
    "h.bulk.irreversible": {"ru": "Действие необратимо. WEB-профили будут сняты автоматически.", "en": "This action is irreversible. WEB profiles will be stripped automatically."},
    "h.bulk.deleting": {"ru": "⏳ Удаляю {n}…", "en": "⏳ Deleting {n}..."},
    "h.bulk.deleted_header": {"ru": "🗑 <b>Удалены: {ok} из {total}</b>", "en": "🗑 <b>Deleted: {ok} of {total}</b>"},
    "h.bulk.not_deleted": {"ru": "\n\n⚠️ Не удалены: {n} (последний юзер или висящий профиль)", "en": "\n\n⚠️ Not deleted: {n} (last user or stray WEB profile)"},
    "h.bulk.need_args": {"ru": "Нужно 3–4 параметра: шаблон количество дней [квота_GB]", "en": "Need 3-4 params: template count days [quota_GB]"},
    "h.bulk.need_ints": {"ru": "Количество, дни и квота должны быть целыми числами", "en": "Count, days and quota must be integers"},
    "h.bulk.count_range": {"ru": "Количество: 1–{n}", "en": "Count: 1-{n}"},
    "h.bulk.days_range": {"ru": "Дни: 0 (без срока) … 3650", "en": "Days: 0 (no expiry) … 3650"},
    "h.bulk.quota_range": {"ru": "Квота в ГБ: 0 (без квоты) … 1024", "en": "Quota GB: 0 (no quota) … 1024"},
    "h.bulk.bad_name": {"ru": "Имя <code>{name}</code> не подходит: латиница/цифры/._- , 1–64 символа", "en": "Name <code>{name}</code> is invalid: letters/digits/._- , 1-64 chars"},
    "h.bulk.name_too_long": {"ru": "Имя <code>{name}</code> длиннее {n} символов — укоротите шаблон", "en": "Name <code>{name}</code> exceeds {n} chars — shorten the template"},
    "h.bulk.menu_title": {"ru": "<b>➕➕ Массовое создание клиентов</b>", "en": "<b>➕➕ Bulk client creation</b>"},
    "h.bulk.wiz.t1": {
        "ru": "➕➕ <b>Массовое создание клиентов</b>\n\nОтправь <b>шаблон имени</b> — <code>guest</code> или <code>vpn{n}</code> ({n} — номер 1,2,…) — или сразу готовую строку ниже.",
        "en": "➕➕ <b>Bulk client creation</b>\n\nSend the <b>name template</b> — <code>guest</code> or <code>vpn{n}</code> ({n} = number 1,2,...) — or the ready-made line below.",
    },
    "h.bulk.wiz.t1_bad": {
        "ru": "❌ Шаблон не подходит: латиница/цифры/._- , 1–64 символа, длина имени ≤ 40.",
        "en": "❌ Invalid template: letters/digits/._- , 1-64 chars, name length ≤ 40.",
    },
    "h.bulk.wiz.t2": {"ru": "2️⃣ <b>Сколько юзеров создать?</b>", "en": "2️⃣ <b>How many users to create?</b>"},
    "h.bulk.wiz.t3": {"ru": "3️⃣ <b>Срок действия</b>", "en": "3️⃣ <b>Expiration</b>"},
    "h.bulk.wiz.t4": {"ru": "4️⃣ <b>Квота трафика</b>", "en": "4️⃣ <b>Traffic quota</b>"},
    "h.bulk.wiz.count_prompt": {"ru": "🔢 Количество юзеров (1–50):", "en": "🔢 Number of users (1-50):"},
    "h.bulk.wiz.days_prompt": {"ru": "📅 Число дней или дата YYYY-MM-DD:", "en": "📅 Days count or date YYYY-MM-DD:"},
    "h.bulk.wiz.quota_prompt": {"ru": "💾 Квота в ГБ (0 — без квоты, до 1024):", "en": "💾 Quota in GB (0 = none, up to 1024):"},
    "h.bulk.wiz.pv_title": {"ru": "📋 <b>Проверка перед созданием</b>", "en": "📋 <b>Review before creating</b>"},
    "h.bulk.wiz.pv_names": {"ru": "👥 Имена: {names}", "en": "👥 Names: {names}"},
    "h.bulk.wiz.pv_exp_days": {"ru": "📅 Срок: +{days} дн (до {d})", "en": "📅 Expiry: +{days} d (until {d})"},
    "h.bulk.wiz.pv_exp_date": {"ru": "📅 Срок: до {d}", "en": "📅 Expiry: until {d}"},
    "h.bulk.wiz.pv_exp_none": {"ru": "♾ Срок: без срока", "en": "♾ Expiry: none"},
    "h.bulk.wiz.pv_quota": {"ru": "💾 Квота: {n} ГБ на юзера", "en": "💾 Quota: {n} GB per user"},
    "h.bulk.wiz.pv_quota_none": {"ru": "💾 Квота: нет", "en": "💾 Quota: none"},
    "h.bulk.wiz.pv_web_on": {"ru": "🌐 WEB-профили: ✅ Да", "en": "🌐 WEB profiles: ✅ On"},
    "h.bulk.wiz.pv_web_off": {"ru": "🌐 WEB-профили: ❌ Нет", "en": "🌐 WEB profiles: ❌ Off"},
    "h.bulk.wiz.btn_create": {"ru": "✅ Создать {n}", "en": "✅ Create {n}"},
    "h.bulk.wiz.btn_days": {"ru": "+{n} дн", "en": "+{n} d"},
    "h.bulk.wiz.btn_custom": {"ru": "🔢 Другое…", "en": "🔢 Custom…"},
    "h.bulk.wiz.btn_noexp": {"ru": "♾ Без срока", "en": "♾ No expiry"},
    "h.bulk.wiz.btn_noquota": {"ru": "🚫 Без квоты", "en": "🚫 No quota"},
    "h.bulk.wiz.btn_date": {"ru": "📅 Дата…", "en": "📅 Date…"},
    "h.bulk.wiz.btn_back": {"ru": "✏️ Изменить", "en": "✏️ Edit"},
    "h.bulk.wiz.btn_again": {"ru": "♻️ Повторить", "en": "♻️ Repeat"},
    "h.bulk.wiz.lost": {
        "ru": "❌ Данные шагов потеряны — начни «➕➕ Массово» заново.",
        "en": "❌ Wizard data lost — start Bulk again.",
    },

    # ─── Справка /help ─────────────────────────────────────────────────────
    "h.help.title": {"ru": "📖 <b>Telemt Manager Bot — справка</b>", "en": "📖 <b>Telemt Manager Bot — help</b>"},
    "h.help.commands": {
        "ru": "<b>Команды</b>\n"
              "/menu — главное меню\n"
              "/adduser <code>имя [дней]</code> — быстро создать клиента\n"
              "       <i>пример: /adduser vasya 30</i>\n"
              "/find <code>запрос</code> — поиск клиента по имени\n"
              "       <i>пример: /find vas  →  найдёт vasya, vasiliy…</i>\n"
              "/check <code>tg://proxy?...</code> — диагностика узла\n"
              "       <i>проверка: DNS, TCP, SSH, Ping, MTProto</i>\n"
              "/alerts — включить / выключить алерты\n"
              "/alert_log — история последних 20 алертов\n"
              "/reload <code>[instant|drain]</code> — runtime reload (3.4.25+)\n"
              "       <i>instant — мгновенное, drain — плавное завершение сессий</i>\n"
              "/reload_status <code>&lt;id&gt;</code> — статус reload операции\n"
              "       <i>accepted/preparing/activating/succeeded/failed</i>\n"
              "/id — ваш Telegram ID",
        "en": "<b>Commands</b>\n"
              "/menu — main menu\n"
              "/adduser <code>name [days]</code> — quickly create a client\n"
              "       <i>example: /adduser vasya 30</i>\n"
              "/find <code>query</code> — search for a client by name\n"
              "       <i>example: /find vas  →  finds vasya, vasiliy…</i>\n"
              "/check <code>tg://proxy?...</code> — node diagnostics\n"
              "       <i>checks: DNS, TCP, SSH, Ping, MTProto</i>\n"
              "/alerts — enable / disable alerts\n"
              "/alert_log — last 20 alerts\n"
              "/reload <code>[instant|drain]</code> — runtime reload (3.4.25+)\n"
              "       <i>instant — instant, drain — graceful session finish</i>\n"
              "/reload_status <code>&lt;id&gt;</code> — reload operation status\n"
              "       <i>accepted/preparing/activating/succeeded/failed</i>\n"
              "/id — your Telegram ID",
    },
    "h.help.menu": {
        "ru": "<b>Главное меню</b>\n"
              "🟢 <b>Состояние сервера</b> — dashboard: статус, uptime, версия, соединения, bad-классы, handshake-ошибки\n"
              "📊 <b>Отчёт по трафику</b> — все клиенты за 1/7/30 дней, сортировка по потреблению, 📈 график топ-15\n"
              "👥 <b>Все клиенты</b> — список с пагинацией и 🔍 поиском\n"
              "➕ <b>Новый клиент</b> — пошаговый мастер (6 шагов)\n"
              "➕➕ <b>Массово</b> — несколько юзеров за раз: шаблон имени, кнопки количества и срока, квота — перед созданием показывает превью\n"
              "⚡ <b>Runtime</b> — Gates, Init, ME Quality, Upstream Quality, Events, Connections, TLS Fingerprints\n"
              "⚠️ <b>Истекающие</b> — клиенты с истекающим сроком, массовое удаление истёкших\n"
              "🔒 <b>Безопасность</b> — Posture, IP Whitelist, Effective Limits\n"
              "🔗 <b>Upstreams</b> — RTT и статус апстримов\n"
              "📡 <b>DC / Writers</b> — статус датацентров и ME Writers\n"
              "📤 <b>Бэкап</b> — выгрузка <code>telemt.toml</code> файлом в чат\n"
              "🌐 <b>WEB Proxy</b> — статус, сессии, lifecycle (pause/drain/resume), debug\n"
              "🔍 <b>Проверить прокси</b> — диагностика узла: DNS, TCP, SSH, Ping, MTProto\n"
              "⚙️ <b>Конфиг</b> — редактирование настроек сервера (General, Timeouts, Censorship…)",
        "en": "<b>Main menu</b>\n"
              "🟢 <b>Server state</b> — dashboard: status, uptime, version, connections, bad classes, handshake errors\n"
              "📊 <b>Traffic report</b> — all clients for 1/7/30 days, sorted by consumption, 📈 top-15 chart\n"
              "👥 <b>All clients</b> — list with pagination and 🔍 search\n"
              "➕ <b>New client</b> — step-by-step wizard (6 steps)\n"
              "➕➕ <b>Bulk</b> — several users at once: name template, count and expiry buttons, quota — with a preview before creating\n"
              "⚡ <b>Runtime</b> — Gates, Init, ME Quality, Upstream Quality, Events, Connections, TLS fingerprints\n"
              "⚠️ <b>Expiring</b> — clients with an expiring term, mass delete of expired ones\n"
              "🔒 <b>Security</b> — Posture, IP Whitelist, Effective Limits\n"
              "🔗 <b>Upstreams</b> — RTT and status of upstreams\n"
              "📡 <b>DC / Writers</b> — datacenter and ME Writers status\n"
              "📤 <b>Backup</b> — unload <code>telemt.toml</code> as a file to the chat\n"
              "🌐 <b>WEB Proxy</b> — status, sessions, lifecycle (pause/drain/resume), debug\n"
              "🔍 <b>Check proxy</b> — node diagnostics: DNS, TCP, SSH, Ping, MTProto\n"
              "⚙️ <b>Config</b> — editing server settings (General, Timeouts, Censorship…)",
    },
    "h.help.reload": {
        "ru": "<b>Runtime Reload (3.4.25+)</b>\n"
              "/reload instant — мгновенное переключение поколения\n"
              "/reload drain — плавное завершение старых сессий\n"
              "/reload_status — проверка статуса reload\n"
              "Нужен при изменении: censorship, timeouts, upstreams, general.modes\n"
              "НЕ нужен при: server, network, пути логов",
        "en": "<b>Runtime Reload (3.4.25+)</b>\n"
              "/reload instant — instant generation switch\n"
              "/reload drain — graceful finish of old sessions\n"
              "/reload_status — check reload status\n"
              "Needed after changing: censorship, timeouts, upstreams, general.modes\n"
              "NOT needed after: server, network, log paths",
    },
    "h.help.card": {
        "ru": "<b>Карточка клиента</b>\n"
              "Редактирование полей • смена секрета • 🔄 сброс квоты • 📊 история трафика с 📈 графиком (24ч / 7 / 14 / 30 дней)",
        "en": "<b>Client card</b>\n"
              "Field editing • secret rotation • 🔄 quota reset • 📊 traffic history with 📈 chart (24h / 7 / 14 / 30 days)",
    },
    "h.help.links": {
        "ru": "<b>Ссылки</b>\n"
              "Над каждой TLS-ссылкой показывается домен маскировки (SNI)\n"
              "«Подключить» открывает окно добавления прокси в Telegram",
        "en": "<b>Links</b>\n"
              "Every TLS link shows its mask domain (SNI) on top\n"
              "«Connect» opens the Telegram add-proxy window",
    },
    "h.help.alerts": {
        "ru": "<b>Алерты</b> — 10 типов:\n"
              "падение / восстановление сервера • всплеск соединений • Writers coverage • обновление версии • неизвестный SNI • всплеск HS timeout • плохих TLS клиентов • сброс при handshake • превышение квоты\n"
              "Cooldown и пороги настраиваются через <code>.env</code>",
        "en": "<b>Alerts</b> — 10 types:\n"
              "server down / recovery • connection spike • Writers coverage • new version • unknown SNI • HS timeout spike • bad TLS clients • reset at handshake • quota exceeded\n"
              "Cooldown and thresholds are configured via <code>.env</code>",
    },
    "h.help.multi": {
        "ru": "<b>Мультисервер</b> — переключение серверов прямо из главного меню. Выбор сохраняется между перезапусками бота.",
        "en": "<b>Multi-server</b> — switch servers right in the main menu. The choice is saved between bot restarts.",
    },
    "h.bulk.spec_help": {
        "ru": "Отправь параметры одной строкой:\n"
              "<code>шаблон количество дней [квота_GB]</code>\n\n"
              "Примеры:\n"
              "• <code>guest 5 30</code> → guest1…guest5 на 30 дней\n"
              "• <code>vpn{{n}} 3 7 50</code> → vpn1…vpn3 на 7 дней, квота 50 ГБ\n"
              "• <code>guest 10 0</code> → 10 юзеров без срока\n\n"
              "Количество: 1–{max_count}, длина имени ≤ {name_max}.",
        "en": "Send the parameters in one line:\n"
              "<code>template count days [quota_GB]</code>\n\n"
              "Examples:\n"
              "• <code>guest 5 30</code> → guest1...guest5 for 30 days\n"
              "• <code>vpn{{n}} 3 7 50</code> → vpn1...vpn3 for 7 days, 50 GB quota\n"
              "• <code>guest 10 0</code> → 10 users without expiry\n\n"
              "Count: 1-{max_count}, name length ≤ {name_max}.",
    },
    "h.bulk.cancel_btn": {"ru": "◀ Отмена", "en": "◀ Cancel"},
    "h.bulk.cancelled": {"ru": "❌ Отменено", "en": "❌ Cancelled"},
    "h.bulk.creating": {"ru": "⏳ Создаю {n} юзеров…", "en": "⏳ Creating {n} users..."},
    "h.bulk.web_failed": {"ru": "\n⚠️ WEB-профили не добавлены: {err}", "en": "\n⚠️ WEB profiles were not added: {err}"},
    "h.bulk.done_title": {"ru": "<b>➕➕ Массовое создание: готово</b>", "en": "<b>➕➕ Bulk creation: done</b>"},
    "h.bulk.created_n": {"ru": "✅ Создано: {n}", "en": "✅ Created: {n}"},
    "h.bulk.skipped": {"ru": "⏭ Уже существуют: {names}", "en": "⏭ Already exist: {names}"},
    "h.bulk.more_errors": {"ru": "…ещё ошибок: {n}", "en": "...{n} more errors"},
    "h.bulk.days_n": {"ru": "📅 Срок: {n} дней", "en": "📅 Expiry: {n} days"},
    "h.bulk.quota_n": {"ru": "💾 Квота: {n} ГБ на юзера", "en": "💾 Quota: {n} GB per user"},
    "h.bulk.links_hint": {"ru": "\n<i>Ссылки остальных — через 🔍 Поиск.</i>", "en": "\n<i>Other links — via 🔍 Search.</i>"},
    "h.bulk.to_users": {"ru": "👥 К списку", "en": "👥 To users"},

    # ─── Поиск / доп. действия над списком / экспорт ───────────────────────
    "h.search.prompt": {"ru": "🔍 Введите имя или часть имени клиента:", "en": "🔍 Enter the client name or its part:"},
    "h.quota.old_api": {"ru": "⚠️ Требуется Telemt 3.4.12+", "en": "⚠️ Requires Telemt 3.4.12+"},
    "h.extra.more": {"ru": "◀️ Ещё", "en": "◀️ More"},
    "h.extra.refresh": {"ru": "🔄 Обновить", "en": "🔄 Refresh"},
    "h.extra.title": {"ru": "⚙️ <b>Действия со списком</b>", "en": "⚙️ <b>List actions</b>"},
    "h.export.title": {"ru": "📤 <b>Экспорт пользователей</b>", "en": "📤 <b>Export users</b>"},
    "h.export.generating": {"ru": "⏳ Генерирую файл...", "en": "⏳ Generating file..."},
    "h.export.csv": {"ru": "📤 CSV — {srv} ({n} клиентов)", "en": "📤 CSV — {srv} ({n} clients)"},
    "h.export.xlsx": {"ru": "📊 Excel — {srv} ({n} клиентов)\n<i>🟢 активные  🔴 истёкшие  Трафик за 7д из истории</i>", "en": "📊 Excel — {srv} ({n} clients)\n<i>🟢 active  🔴 expired  Traffic for 7d from history</i>"},

    # ─── Истёкшие клиенты ──────────────────────────────────────────────────
    "h.expiring.title": {"ru": "<b>⏰ Сроки действия — {srv}</b>", "en": "<b>⏰ Expirations — {srv}</b>"},
    "h.expiring.expired": {"ru": "🔴 <b>Истёкших: {n}</b>", "en": "🔴 <b>Expired: {n}</b>"},
    "h.expiring.soon": {"ru": "\n🟡 <b>Истекают в течение 7 дней: {n}</b>", "en": "\n🟡 <b>Expire within 7 days: {n}</b>"},
    "h.expiring.menu_btn": {"ru": "🧹 Удалить истёкших", "en": "🧹 Delete expired"},
    "h.expiring.none": {"ru": "Истёкших нет", "en": "No expired users"},
    "h.expiring.all_fine": {"ru": "✅ Нет истёкших пользователей", "en": "✅ No expired users"},
    "h.expiring.confirm": {"ru": "⚠️ Удалить <b>{n}</b> истёкших?\n\n<code>{names}</code>", "en": "⚠️ Delete <b>{n}</b> expired?\n\n<code>{names}</code>"},
    "h.expiring.deleted_n": {"ru": "✅ Удалено: {ok}, ошибок: {err}", "en": "✅ Deleted: {ok}, errors: {err}"},

    # ─── WEB-профили при удалении ──────────────────────────────────────────
    "h.strip_profiles_failed": {"ru": "❌ Не удалось убрать WEB-профили: {err}", "en": "❌ Failed to strip WEB profiles: {err}"},
    "h.strip_profile_failed": {"ru": "❌ Не удалось убрать WEB-профиль: {err}", "en": "❌ Failed to strip WEB profile: {err}"},

    # ─── Карточка юзера: rotate / toggle / delete ──────────────────────────
    "h.user.not_found": {"ru": "❌ Пользователь не найден", "en": "❌ User not found"},
    "h.rotate.failed": {"ru": "❌ Не удалось обновить секрет", "en": "❌ Failed to rotate secret"},
    "h.rotate.ok": {"ru": "✅ Секрет обновлён", "en": "✅ Secret rotated"},
    "h.rotate.title": {"ru": "🔑 <b>Новый секрет — {user}</b>{status}", "en": "🔑 <b>New secret — {user}</b>{status}"},
    "h.rotate.save_hint": {"ru": "<i>Сохраните — больше не будет показан</i>", "en": "<i>Save it now — it won't be shown again</i>"},
    "h.toggle.bad_format": {"ru": "❌ Неверный формат", "en": "❌ Invalid format"},
    "h.toggle.bad_action": {"ru": "❌ Неизвестное действие", "en": "❌ Unknown action"},
    "h.toggle.failed": {"ru": "❌ Не удалось изменить статус", "en": "❌ Failed to change status"},
    "h.toggle.on": {"ru": "🟢 Включён", "en": "🟢 Enabled"},
    "h.toggle.off": {"ru": "🔴 Отключён", "en": "🔴 Disabled"},
    "h.user.delete_confirm": {"ru": "⚠️ Удалить <b>{user}</b>?\n\nДействие необратимо.", "en": "⚠️ Delete <b>{user}</b>?\n\nThis action is irreversible."},
    "h.user.deleted": {"ru": "✅ {user} удалён", "en": "✅ {user} deleted"},
    "h.user.partial_delete": {"ru": "⚠️ Частичное удаление:", "en": "⚠️ Partial deletion:"},

    # ─── Квота / трафик юзера ──────────────────────────────────────────────
    "h.quota.reset_ok": {"ru": "✅ Квота сброшена", "en": "✅ Quota reset"},
    "h.quota.reset_title": {"ru": "✅ Квота <b>{user}</b> сброшена", "en": "✅ Quota of <b>{user}</b> reset"},
    "h.traffic.menu": {"ru": "📊 <b>История трафика — {user}</b>\n\nВыберите период:", "en": "📊 <b>Traffic history — {user}</b>\n\nPick a period:"},
    "h.traffic.few_title": {"ru": "📊 <b>История — {user}</b> ({days}д)", "en": "📊 <b>History — {user}</b> ({days}d)"},
    "h.traffic.few_points": {"ru": "⚠️ Данных пока мало (точек: {n})", "en": "⚠️ Not enough data yet (points: {n})"},
    "h.traffic.collect_hint": {"ru": "<i>Сбор каждые 15 минут</i>", "en": "<i>Collected every 15 min</i>"},
    "h.traffic.title": {"ru": "<b>📊 Трафик — {user} ({days}д)</b>", "en": "<b>📊 Traffic — {user} ({days}d)</b>"},
    "h.traffic.period_row": {"ru": "  За период: <b>{total}</b>  |  Точек: {points}", "en": "  For period: <b>{total}</b>  |  Points: {points}"},
    "h.traffic.chart_caption": {"ru": "📈 <b>{user}</b> — трафик за {days} дн. • {srv}", "en": "📈 <b>{user}</b> — traffic for {days} d • {srv}"},
    "h.traffic.top_caption": {"ru": "📈 Топ клиентов — {days} дн. • {srv}", "en": "📈 Top clients — {days} d • {srv}"},

    # ─── Графики ───────────────────────────────────────────────────────────
    "h.chart.recent_snapshots": {"ru": "<b>Последние снимки:</b>", "en": "<b>Recent snapshots:</b>"},
    "h.chart.building": {"ru": "⏳ Строю график...", "en": "⏳ Building chart..."},
    "h.chart.not_enough": {"ru": "⚠️ Мало данных (нужно минимум 2 точки)", "en": "⚠️ Not enough data (need at least 2 points)"},
    "h.chart.no_mpl": {"ru": "⚠️ matplotlib не установлен на сервере", "en": "⚠️ matplotlib is not installed on the server"},
    "h.chart.no_data": {"ru": "⚠️ Нет данных за период", "en": "⚠️ No data for the period"},

    # ─── Ссылки юзера ──────────────────────────────────────────────────────
    "h.links.title": {"ru": "<b>🔗 Ссылки — {user}</b>", "en": "<b>🔗 Links — {user}</b>"},

    # ─── FSM-создание юзера ────────────────────────────────────────────────
    "h.adduser.bad_name": {"ru": "❌ Неверное имя", "en": "❌ Invalid name"},
    "h.find.empty": {"ru": "❌ Пустой запрос", "en": "❌ Empty query"},
    "h.create.step1_err": {"ru": "❌ Только A-Z a-z 0-9 _ . - (1–64 символа)", "en": "❌ Only A-Z a-z 0-9 _ . - (1-64 chars)"},
    "h.create.step2_err": {"ru": "❌ 32 hex-символа, /skip или /gen", "en": "❌ 32 hex chars, /skip or /gen"},
    "h.create.step3_err": {"ru": "❌ Число или /skip", "en": "❌ A number or /skip"},
    "h.create.step4_err": {"ru": "❌ Число дней, дата или /skip", "en": "❌ Days as number, a date or /skip"},
    "h.create.step5_err": {"ru": "❌ Число байт или /skip", "en": "❌ Bytes as number or /skip"},
    "h.create.confirmed_cancel": {"ru": "❌ Отменено. /menu", "en": "❌ Cancelled. /menu"},

    # ─── FSM-редактирование юзера ──────────────────────────────────────────
    "h.edit.no_change": {"ru": "⏭ Без изменений. /menu", "en": "⏭ No changes. /menu"},
    "h.edit.not_int": {"ru": "❌ Нужно целое число", "en": "❌ An integer is required"},
    "h.edit.bad_rate": {"ru": "❌ Укажите скорость в байт/с (например <code>1048576</code> для 1 MB/s)\n", "en": "❌ Specify rate in bytes/s (e.g. <code>1048576</code> for 1 MB/s)\n"},
    "h.edit.rate_zero_hint": {"ru": "или <code>0</code> чтобы снять лимит", "en": "or <code>0</code> to remove the limit"},
    "h.edit.bad_secret": {"ru": "❌ Ровно 32 hex-символа", "en": "❌ Exactly 32 hex chars"},

    # ─── Runtime / SecurityCS ──────────────────────────────────────────────
    "h.runtime.title": {"ru": "<b>⚡ Runtime</b>\n\nВыберите раздел:", "en": "<b>⚡ Runtime</b>\n\nPick a section:"},
    "h.security.title": {"ru": "<b>🔒 Безопасность</b>", "en": "<b>🔒 Security</b>"},

    # ─── Проверка прокси (/check) ──────────────────────────────────────────
    "h.check.menu_title": {"ru": "🔍 <b>Проверка узла</b>", "en": "🔍 <b>Node check</b>"},
    "h.check.prompt": {"ru": "Отправь ссылку на прокси:", "en": "Send a proxy link:"},
    "h.check.methods": {"ru": "Проверка: DNS, TCP, SSH, Ping, MTProto", "en": "Checks: DNS, TCP, SSH, Ping, MTProto"},
    "h.check.prompt2": {"ru": "🔍 Отправь ссылку на прокси:", "en": "🔍 Send a proxy link:"},
    "h.check.unrecognized": {"ru": "❌ Не удалось распознать ссылку.\n\nОжидается формат:", "en": "❌ Could not parse the link.\n\nExpected format:"},
    "h.check.expected_format": {"ru": "<code>tg://proxy?server=HOST&port=443&secret=SECRET</code>", "en": "<code>tg://proxy?server=HOST&port=443&secret=SECRET</code>"},
    "h.check.bad_link2": {"ru": "❌ Не удалось разобрать ссылку — проверь формат.", "en": "❌ Could not parse the link — check the format."},
    "h.check.checking": {"ru": "⏳ Проверяю узел, подожди 2-8 секунд...", "en": "⏳ Checking node, wait 2-8 seconds..."},
    "h.node.title": {"ru": "🔍 <b>Диагностика узла</b>", "en": "🔍 <b>Node diagnostics</b>"},

    # ─── Редактор конфига / reload ─────────────────────────────────────────
    "h.cfg.no_data": {"ru": "❌ Нет данных для применения", "en": "❌ No data to apply"},
    "h.cfg.need_reload": {"ru": "\n⚠️ Изменения требуют runtime reload — выберите режим ниже\n", "en": "\n⚠️ Changes require runtime reload — pick a mode below\n"},
    "h.cfg.need_restart": {"ru": "⛔ Нужен перезапуск процесса Telemt\n", "en": "⛔ Telemt process restart required\n"},
    "h.cfg.hot_reload": {"ru": "✅ Hot-reload — перезапуск не требуется\n", "en": "✅ Hot-reload — restart not required\n"},
    "h.cfg.lite_block": {"ru": "⛔ Отключено в lite-режиме", "en": "⛔ Disabled in lite mode"},
    "h.cfg.bad_mode": {"ru": "❌ Неверный режим", "en": "❌ Invalid mode"},
    "h.reload.bad_mode": {"ru": "❌ Неверный режим. Допустимые: <code>instant</code>, <code>drain</code>\n\n", "en": "❌ Invalid mode. Allowed: <code>instant</code>, <code>drain</code>\n\n"},
    "h.reload.instant_hint": {"ru": "<b>instant</b> — мгновенное переключение, старые сессии отменяются\n", "en": "<b>instant</b> — instant switch, old sessions are cancelled\n"},
    "h.reload.drain_hint": {"ru": "<b>drain</b> — плавное завершение старых сессий", "en": "<b>drain</b> — graceful finish of old sessions"},
    "h.reload.usage": {"ru": "Использование: <code>/reload_status &lt;id&gt;</code>", "en": "Usage: <code>/reload_status &lt;id&gt;</code>"},

    # ─── WEB runtime ───────────────────────────────────────────────────────
    "h.web.runtime_down": {"ru": "❌ WEB runtime недоступен", "en": "❌ WEB runtime unavailable"},
    "h.web.closed_ok": {"ru": "✅ Сессия закрыта", "en": "✅ Session closed"},
    "h.web.op_failed_reason": {"ru": "ошибка операции", "en": "operation error"},
    "h.web.op_cancelled": {"ru": "⚠️ Операция отменена", "en": "⚠️ Operation cancelled"},
    "h.web.paused": {"ru": "⏸ Пауза — admission закрыт", "en": "⏸ Paused — admission closed"},
    "h.web.drain_started": {"ru": "🔄 Drain запущен (30с)", "en": "🔄 Drain started (30s)"},
    "h.web.resumed": {"ru": "▶️ Resume — admission открыт", "en": "▶️ Resume — admission open"},

    # ─── Статус / алерты ───────────────────────────────────────────────────
    "h.status.title": {"ru": "<b>⚡ Статус серверов</b>", "en": "<b>⚡ Server status</b>"},
    "h.alerts.on": {"ru": "включён", "en": "enabled"},
    "h.alerts.off": {"ru": "выключен", "en": "disabled"},
}

# fmt.common.no_links и другие чужие префиксы (fmt.* / kb.* / common.*) берутся
# из своих таблиц — их здесь нет и не должно быть.
