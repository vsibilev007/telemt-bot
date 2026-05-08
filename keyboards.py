"""
Клавиатуры и inline-кнопки
"""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def _fmt_bytes_short(b: int) -> str:
    if not b:
        return "0B"
    for unit, threshold in [("G", 1 << 30), ("M", 1 << 20), ("K", 1 << 10)]:
        if b >= threshold:
            return f"{b / threshold:.1f}{unit}"
    return f"{b}B"


def main_menu_kb(
    servers: list,
    current: int = 0,
    online_count: int = 0,
    status: str = "unknown",
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if status == "ok":
        status_btn = "🟢 Состояние сервера"
    elif status == "unreachable":
        status_btn = "🔴 Состояние сервера"
    else:
        status_btn = "🟡 Состояние сервера"
    kb.button(text=status_btn, callback_data="menu:dashboard")
    kb.button(text="📊 Отчёт по трафику", callback_data="menu:traffic_report")
    kb.button(text="👥 Все клиенты", callback_data="menu:users")
    kb.button(text="➕ Новый клиент", callback_data="user:create")
    kb.button(text="⚡ Runtime", callback_data="menu:runtime")
    kb.button(text="⚠️ Истекающие", callback_data="users:expiring_menu")
    kb.button(text="🔒 Безопасность", callback_data="menu:security")
    kb.button(text="🔗 Upstreams", callback_data="menu:upstreams")
    kb.button(text="📡 DC / Writers", callback_data="menu:dcs")
    kb.button(text="📤 Бэкап", callback_data="users:export_toml")
    if len(servers) > 1:
        for i, srv in enumerate(servers):
            mark = "✅ " if i == current else ""
            kb.button(text=f"{mark}{srv.name}", callback_data=f"server:select:{i}")
        kb.adjust(2, 2, 2, 2, 2, len(servers))
    else:
        kb.adjust(2)
    return kb.as_markup()


def sysinfo_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data="sysinfo:refresh")
    kb.button(text="◀️ Меню", callback_data="menu:main")
    kb.adjust(2)
    return kb.as_markup()


def dashboard_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data="dashboard:refresh")
    kb.button(text="◀️ Меню", callback_data="menu:main")
    kb.adjust(2)
    return kb.as_markup()


def users_list_kb(
    users: list, page: int = 0, page_size: int = 10
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    start = page * page_size
    end = start + page_size
    page_users = users[start:end]
    for u in page_users:
        conns = u.get("current_connections", 0)
        icon = "🟢" if conns > 0 else "⚪"
        name = u["username"]
        traffic = _fmt_bytes_short(u.get("total_octets", 0))
        kb.button(
            text=f"{icon} {name}  |  {traffic}  |  {conns}🔌",
            callback_data=f"user:view:{name}",
        )
    total_pages = max(1, -(-len(users) // page_size))
    nav_count = 0
    if total_pages > 1:
        if page > 0:
            kb.button(text="◀", callback_data=f"users:page:{page - 1}")
            nav_count += 1
        kb.button(text=f"{page + 1}/{total_pages}", callback_data="noop")
        nav_count += 1
        if end < len(users):
            kb.button(text="▶", callback_data=f"users:page:{page + 1}")
            nav_count += 1
    kb.button(text="➕ Новый", callback_data="user:create")
    kb.button(text="🔄", callback_data="users:refresh")
    kb.button(text="⚙ Ещё", callback_data="users:extra")
    kb.button(text="◀ Назад в меню", callback_data="menu:main")
    schema = [1] * len(page_users)
    if nav_count:
        schema.append(nav_count)
    schema += [3, 1]
    kb.adjust(*schema)
    return kb.as_markup()


def user_detail_kb(username: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Редактировать", callback_data=f"user:edit:{username}")
    kb.button(text="🗑️ Удалить", callback_data=f"user:delete_confirm:{username}")
    kb.button(text="🔗 Ссылки", callback_data=f"user:links:{username}")
    kb.button(text="🔄 Сменить секрет", callback_data=f"user:rotate_secret:{username}")
    kb.button(text="📊 История трафика", callback_data=f"user:traffic:{username}")
    kb.button(text="🔄 Обновить", callback_data=f"user:view:{username}")
    kb.button(text="◀️ К списку", callback_data="menu:users")
    kb.adjust(2, 1, 2, 1, 1)
    return kb.as_markup()


def user_delete_confirm_kb(username: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=f"user:delete:{username}")
    kb.button(text="❌ Отмена", callback_data=f"user:view:{username}")
    kb.adjust(2)
    return kb.as_markup()


def user_edit_kb(username: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔑 Секрет", callback_data=f"user:editfield:{username}:secret")
    kb.button(
        text="🔗 Max TCP", callback_data=f"user:editfield:{username}:max_tcp_conns"
    )
    kb.button(
        text="📅 Срок действия",
        callback_data=f"user:editfield:{username}:expiration_rfc3339",
    )
    kb.button(
        text="💾 Квота", callback_data=f"user:editfield:{username}:data_quota_bytes"
    )
    kb.button(
        text="🌐 Max IP", callback_data=f"user:editfield:{username}:max_unique_ips"
    )
    kb.button(text="◀️ Назад", callback_data=f"user:view:{username}")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def user_links_kb(username: str, links: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in range(len(links)):
        kb.button(text="📷 QR", callback_data=f"user:qr:{username}:{i}")
    kb.button(text="◀️ Назад", callback_data=f"user:view:{username}")
    kb.adjust(2)
    return kb.as_markup()


def user_links_kb_no_links(username: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data=f"user:view:{username}")
    return kb.as_markup()


def users_extra_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⏰ Истекающие", callback_data="users:expiring")
    kb.button(text="🧹 Удалить истёкших", callback_data="users:delete_expired_confirm")
    kb.button(text="◀️ К списку", callback_data="menu:users")
    kb.adjust(2, 1)
    return kb.as_markup()


def users_delete_expired_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data="users:delete_expired")
    kb.button(text="❌ Отмена", callback_data="users:extra")
    kb.adjust(2)
    return kb.as_markup()


def export_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 CSV", callback_data="users:export:csv")
    kb.button(text="📊 Excel", callback_data="users:export:xlsx")
    kb.button(text="◀️ Меню", callback_data="menu:main")
    kb.adjust(2, 1)
    return kb.as_markup()


def traffic_period_kb(username: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for days, label in [(1, "24ч"), (7, "7 дней"), (14, "14 дней"), (30, "30 дней")]:
        kb.button(text=label, callback_data=f"user:traffic_period:{username}:{days}")
    kb.button(text="◀️ Назад", callback_data=f"user:view:{username}")
    kb.adjust(4, 1)
    return kb.as_markup()


def traffic_report_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for days, label in [(1, "24ч"), (7, "7 дней"), (30, "30 дней")]:
        kb.button(text=label, callback_data=f"traffic_report:{days}")
    kb.button(text="🔄 Обновить", callback_data="traffic_report:7")
    kb.button(text="◀️ Меню", callback_data="menu:main")
    kb.adjust(3, 1, 1)
    return kb.as_markup()


def alerts_kb(states: dict[str, bool] | None = None) -> InlineKeyboardMarkup:
    states = states or {}
    labels = {
        "status_down": "Падение сервера",
        "status_up": "Восстановление",
        "conn_spike": "Всплеск соединений",
        "writers_low": "Writers coverage",
        "version_change": "Обновление версии",
        "bad_unknown_sni": "Неизвестный SNI",
        "hs_timeout_spike": "Всплеск HS timeout",
        "bad_client_spike": "Всплеск плохих TLS",
        "hs_conn_reset": "Сброс при handshake",
    }
    kb = InlineKeyboardBuilder()
    for atype, alabel in labels.items():
        mark = "✅" if states.get(atype, False) else "☑️"
        kb.button(text=f"{mark} {alabel}", callback_data=f"alert:toggle:{atype}")
    kb.button(text="◀ Меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def runtime_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 Gates", callback_data="runtime:gates")
    kb.button(text="🚀 Init", callback_data="runtime:init")
    kb.button(text="📈 ME Quality", callback_data="runtime:me_quality")
    kb.button(text="🔗 Upstream Quality", callback_data="runtime:upstream_quality")
    kb.button(text="📋 Events", callback_data="runtime:events")
    kb.button(text="👥 Connections", callback_data="runtime:connections")
    kb.button(text="◀️ Меню", callback_data="menu:main")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def runtime_sub_kb(section: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data=f"runtime:{section}")
    kb.button(text="◀️ Runtime", callback_data="menu:runtime")
    kb.adjust(2)
    return kb.as_markup()


def security_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛡️ Posture", callback_data="security:posture")
    kb.button(text="📋 Whitelist", callback_data="security:whitelist")
    kb.button(text="⚙️ Лимиты", callback_data="security:limits")
    kb.button(text="◀️ Меню", callback_data="menu:main")
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def security_sub_kb(section: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data=f"security:{section}")
    kb.button(text="◀️ Безопасность", callback_data="menu:security")
    kb.adjust(2)
    return kb.as_markup()


def upstreams_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data="upstreams:refresh")
    kb.button(text="◀️ Меню", callback_data="menu:main")
    kb.adjust(2)
    return kb.as_markup()


def dcs_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📡 DC Status", callback_data="dcs:status")
    kb.button(text="✍️ ME Writers", callback_data="dcs:writers")
    kb.button(text="◀️ Меню", callback_data="menu:main")
    kb.adjust(2, 1)
    return kb.as_markup()


def dcs_sub_kb(section: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data=f"dcs:{section}")
    kb.button(text="◀️ DC / Writers", callback_data="menu:dcs")
    kb.adjust(2)
    return kb.as_markup()


def export_toml_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="◀ Меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()
