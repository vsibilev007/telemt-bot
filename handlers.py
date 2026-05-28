"""
Обработчики команд и callback-кнопок Telegram-бота
"""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
from datetime import datetime, timezone, timedelta
import tz as _tz

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InputMediaPhoto, Message, ReplyKeyboardRemove


from api_client import ApiError, TelemetClient, cluster_write, cluster_read, cluster_users_with_nodes, NodeResult
from config import Config
import database as db
from export_utils import users_to_csv, users_to_xlsx
from formatters import (
    format_connections, format_dashboard, format_dcs, format_limits,
    format_me_quality, format_me_writers, format_runtime_events,
    format_runtime_gates, format_runtime_init, format_security_posture,
    format_security_whitelist, format_upstream_quality, format_upstreams,
    format_user_detail, format_user_list, format_user_links, format_users_quota,
    fmt_bytes,
)
from keyboards import (
    alerts_kb, dashboard_kb, dcs_kb, dcs_sub_kb, export_menu_kb,
    main_menu_kb, runtime_kb, runtime_sub_kb, security_kb, security_sub_kb,
    sysinfo_kb, traffic_period_kb, traffic_report_kb, upstreams_kb,
    proxy_check_kb,
    user_delete_confirm_kb, user_detail_kb, user_edit_kb,
    user_links_kb, user_links_kb_no_links, users_delete_expired_confirm_kb,
    users_extra_kb, users_list_kb,
)
from qr_utils import make_qr_bytes, link_short_label
from session import get_client, get_server_index, set_server_index
from sysinfo import get_system_info, format_system_status
import charts
import proxy_checker as pc
from states import CreateUserFSM, EditFieldFSM, QuickAddFSM, SearchUserFSM, ProxyCheckFSM
from export_toml import router as export_toml_router
from database import set_alert, get_alert

# Валидация имени клиента — единая точка для FSM и /adduser
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")

logger = logging.getLogger(__name__)


def _is_command(message: Message) -> bool:
    """True если сообщение — команда бота.
    /skip и /gen разрешены внутри FSM — они не считаются командами бота."""
    if not message.text or not message.text.startswith("/"):
        return False
    FSM_INTERNALS = {"/skip", "/gen"}
    cmd = message.text.split()[0].lower()
    return cmd not in FSM_INTERNALS


def _format_cluster_result(results: list[NodeResult]) -> str:
    """Форматирует результат write-операции на кластере."""
    lines = []
    for r in results:
        icon = "✅" if r.ok else "❌"
        lines.append(f"{icon} <b>{r.server_name}</b>" + (f": {r.error}" if not r.ok else ""))
    return "\n".join(lines)


def _all_ok(results: list[NodeResult]) -> bool:
    return all(r.ok for r in results)

async def _cluster_section(
    cq: CallbackQuery,
    config: Config,
    api_method: str,
    formatter,
    kb,
    *args,
):
    """
    Универсальный хелпер для разделов Runtime/Security/DC/Upstreams.
    Для кластера — опрашивает все узлы параллельно и показывает данные каждого.
    Для одиночного — стандартное поведение.
    """
    client, srv = await get_client(_uid(cq), config)
    members = config.get_group_members(srv)

    if config.is_cluster(srv):
        await cq.answer()

        async def _get_node(node_srv):
            node_client = TelemetClient(node_srv.url, node_srv.auth_header)
            try:
                method = getattr(node_client, api_method)
                data = await method(*args)
                return node_srv.name, True, formatter(data)
            except Exception as e:
                return node_srv.name, False, f"🔴 Ошибка: {str(e)[:80]}"

        results = await asyncio.gather(*[_get_node(m) for m in members])
        sep = "─" * 28
        lines = []
        for name, ok, text in results:
            lines += [f"<b>⚙️ {name}</b>", sep, text, ""]
        await _safe_edit(cq, "\n".join(lines).rstrip(), reply_markup=kb)
    else:
        method = getattr(client, api_method)
        data = await _api_call(cq, method, *args)
        if data:
            await _safe_edit(cq, formatter(data), reply_markup=kb)


router = Router()
router.include_router(export_toml_router)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _uid(event) -> int:
    return event.from_user.id


async def _safe_edit(cq: CallbackQuery, text: str, reply_markup=None):
    try:
        await cq.message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        pass
    await cq.answer()


async def _api_call(target, func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except ApiError as e:
        if isinstance(target, CallbackQuery):
            await target.answer(f"❌ {e.code}: {e.message}"[:200], show_alert=True)
        else:
            await target.answer(f"❌ <b>{e.code}</b>: {e.message}")
        return None
    except Exception as e:
        if isinstance(target, CallbackQuery):
            await target.answer(str(e)[:200], show_alert=True)
        else:
            await target.answer(f"❌ {type(e).__name__}: {e}")
        return None


def _get_all_links(user: dict) -> list[str]:
    ld = user.get("links", {})
    return ld.get("classic", []) + ld.get("secure", []) + ld.get("tls", [])


def _gen_secret() -> str:
    return secrets.token_hex(16)


async def _get_menu_state(uid: int, config: Config) -> tuple[str, int]:
    """Возвращает (status, online_count) для главного меню"""
    client, srv = await get_client(uid, config)
    try:
        health, summary = await asyncio.gather(
            client.get_health(),
            client.get_stats_summary(),
        )
        status = health.get("status", "unknown")
        conns = summary.get("connections_total", 0)
        return status, conns
    except Exception:
        return "unreachable", 0


# ─── Start / Menu ─────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, config: Config):
    """Приветствие + главное меню."""
    uid = _uid(message)
    idx = await get_server_index(uid, config)
    srv = config.servers[idx]
    status, conns = await _get_menu_state(uid, config)
    name = message.from_user.first_name or "друг"
    await message.answer(
        f"👋 <b>Привет, {name}!</b>\n\n"
        f"Это бот управления <b>Telemt MTProxy</b>.\n\n"
        f"<b>Основные команды:</b>\n"
        f"  /menu — главное меню\n"
        f"  /adduser имя [дней] — быстро создать клиента\n"
        f"  /find запрос — поиск клиента по имени\n"
        f"  /alerts — управление алертами\n"
        f"  /alert_log — история последних алертов\n\n"
        f"<i>Выберите действие в меню ниже 👇</i>",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        f"<b>Telemt Manager</b> — <code>{srv.group if config.is_cluster(srv) else srv.name}</code>",
        reply_markup=main_menu_kb(config.servers, idx, conns, status, config),
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, config: Config):
    """Главное меню без приветствия."""
    uid = _uid(message)
    idx = await get_server_index(uid, config)
    srv = config.servers[idx]
    status, conns = await _get_menu_state(uid, config)
    await message.answer(
        f"<b>Telemt Manager</b> — <code>{srv.group if config.is_cluster(srv) else srv.name}</code>",
        reply_markup=main_menu_kb(config.servers, idx, conns, status, config),
    )


@router.callback_query(F.data == "menu:main")
async def cb_menu_main(cq: CallbackQuery, config: Config):
    """Возврат в главное меню — работает под любым типом сообщения."""
    uid = _uid(cq)
    idx = await get_server_index(uid, config)
    srv = config.servers[idx]
    status, conns = await _get_menu_state(uid, config)
    text = f"<b>Telemt Manager</b> — <code>{srv.group if srv.group else srv.name}</code>"
    kb = main_menu_kb(config.servers, idx, conns, status, config)

    # Под фото/документом/стикером edit_text невозможен — удаляем и шлём заново
    if cq.message.text:
        await _safe_edit(cq, text, reply_markup=kb)
    else:
        await cq.answer()
        try:
            await cq.message.delete()
        except Exception:
            pass
        await cq.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "menu:refresh")
async def cb_menu_refresh(cq: CallbackQuery, config: Config):
    await cb_menu_main(cq, config)


@router.callback_query(F.data == "noop")
async def cb_noop(cq: CallbackQuery):
    await cq.answer()

# ─── Server selection ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("server:select:"))
async def cb_server_select(cq: CallbackQuery, config: Config):
    idx = int(cq.data.split(":")[-1])
    await set_server_index(_uid(cq), idx)
    srv = config.servers[idx]
    await cq.answer(f"✅ {srv.name}", show_alert=False)
    status, conns = await _get_menu_state(_uid(cq), config)
    await _safe_edit(
        cq,
        f"<b>Telemt Manager</b> — <code>{srv.group if config.is_cluster(srv) else srv.name}</code>",
        reply_markup=main_menu_kb(config.servers, idx, conns, status, config),
    )


# ─── System info ──────────────────────────────────────────────────────────────

async def _show_sysinfo(cq: CallbackQuery, config: Config):
    await cq.answer("⏳ Собираю данные...")
    client, srv = await get_client(_uid(cq), config)

    # Параллельно: системная инфа + состояние telemt
    sys_task = get_system_info()
    telemt_task = asyncio.gather(
        client.get_health(),
        client.get_stats_summary(),
        return_exceptions=True,
    )

    info, telemt_results = await asyncio.gather(sys_task, telemt_task)

    health, summary = telemt_results
    if isinstance(health, Exception):
        telemt_status = "unreachable"
        telemt_conns = 0
    else:
        telemt_status = health.get("status", "unknown")
        telemt_conns = summary.get("connections_total", 0) if not isinstance(summary, Exception) else 0

    text = (
        f"🖥 <b>Состояние сервера — {srv.name}</b>\n\n"
        + format_system_status(info, telemt_status, telemt_conns)
    )
    await _safe_edit(cq, text, reply_markup=sysinfo_kb())


@router.callback_query(F.data.in_({"menu:sysinfo", "sysinfo:refresh"}))
async def cb_sysinfo(cq: CallbackQuery, config: Config):
    await _show_sysinfo(cq, config)


# ─── Dashboard (Telemt detail) ─────────────────────────────────────────────────

async def _show_dashboard(cq: CallbackQuery, config: Config):
    client, srv = await get_client(_uid(cq), config)
    members = config.get_group_members(srv)

    if config.is_cluster(srv):
        # Кластер — показываем состояние всех узлов
        await cq.answer()

        async def _get_node_data(node_srv):
            node_client = TelemetClient(node_srv.url, node_srv.auth_header)
            try:
                health, summary, sysinfo, gates, users = await asyncio.gather(
                    node_client.get_health(),
                    node_client.get_stats_summary(),
                    node_client.get_system_info(),
                    node_client.get_runtime_gates(),
                    node_client.get_users(),
                )
                online = sum(1 for u in users if u.get("current_connections", 0) > 0)
                return node_srv.name, True, format_dashboard(
                    health, summary, sysinfo, gates, node_srv.name, online
                )
            except Exception as e:
                return node_srv.name, False, f"🔴 <b>{node_srv.name}</b> — недоступен: {e}"

        results = await asyncio.gather(*[_get_node_data(m) for m in members])

        # Собираем общий дашборд кластера
        lines = [f"⚙️ <b>Кластер: {srv.group}</b>\n"]
        for name, ok, text in results:
            lines.append(f"{'─' * 30}")
            lines.append(text)

        text = "\n".join(lines)
        await _safe_edit(cq, text, reply_markup=dashboard_kb())
    else:
        # Одиночный сервер — стандартный дашборд
        try:
            health, summary, sysinfo, gates, users = await asyncio.gather(
                client.get_health(),
                client.get_stats_summary(),
                client.get_system_info(),
                client.get_runtime_gates(),
                client.get_users(),
            )
        except Exception as e:
            await cq.answer(str(e)[:200], show_alert=True)
            return
        online_users = sum(1 for u in users if u.get("current_connections", 0) > 0)
        await _safe_edit(
            cq,
            format_dashboard(health, summary, sysinfo, gates, srv.name, online_users),
            reply_markup=dashboard_kb(),
        )


@router.callback_query(F.data.in_({"menu:dashboard", "dashboard:refresh"}))
async def cb_dashboard(cq: CallbackQuery, config: Config):
    await _show_dashboard(cq, config)




# ─── Traffic report ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:traffic_report")
async def cb_traffic_report_menu(cq: CallbackQuery):
    await _safe_edit(
        cq,
        "📊 <b>Отчёт по трафику</b>\n\nВыберите период:",
        reply_markup=traffic_report_kb(),
    )


@router.callback_query(F.data.startswith("traffic_report:"))
async def cb_traffic_report(cq: CallbackQuery, config: Config):
    days = int(cq.data.split(":")[-1])
    _, srv = await get_client(_uid(cq), config)
    await cq.answer("⏳ Считаю...")

    client, _ = await get_client(_uid(cq), config)
    users_task = client.get_users()
    deltas_task = db.get_all_users_traffic_delta(srv.name, days=days)
    try:
        users, deltas = await asyncio.gather(users_task, deltas_task)
    except Exception as e:
        await cq.answer(str(e)[:200], show_alert=True)
        return

    delta_map = {r["username"]: r["delta_bytes"] for r in deltas}
    sorted_users = sorted(users, key=lambda u: delta_map.get(u["username"], 0), reverse=True)

    total_delta = sum(delta_map.values())
    active = sum(1 for u in users if u.get("current_connections", 0) > 0)

    lines = [
        f"📊 <b>Отчёт по трафику — {srv.group if srv.group else srv.name}</b>",
        f"<i>Период: {days} дн  |  {len(users)} клиентов  |  {active} онлайн</i>",
        f"<b>Всего за период: {fmt_bytes(total_delta)}</b>",
        "",
    ]

    for u in sorted_users[:20]:
        name = u["username"]
        delta = delta_map.get(name, 0)
        conns = u.get("current_connections", 0)
        icon = "🟢" if conns > 0 else "⚪"
        total = fmt_bytes(u.get("total_octets", 0))
        d_str = fmt_bytes(delta) if delta else "—"
        exp = u.get("expiration_rfc3339", "")
        exp_str = ""
        if exp:
            try:
                exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                if exp_dt < datetime.now(timezone.utc):
                    exp_str = " 🔴истёк"
                elif exp_dt < datetime.now(timezone.utc) + timedelta(days=7):
                    exp_str = " ⚠️скоро"
            except Exception:
                pass
        lines.append(f"{icon} <code>{name}</code>{exp_str}")
        lines.append(f"   За период: <b>{d_str}</b>  |  Всего: {total}  |  {conns}🔌")

    if len(sorted_users) > 20:
        lines.append(f"\n<i>...и ещё {len(sorted_users) - 20} клиентов</i>")

    text = "\n".join(lines)
    kb = traffic_report_kb(chart_mode=False)

    # Если под фото — удаляем фото и шлём новое текстовое сообщение
    if cq.message.photo:
        await cq.message.delete()
        await cq.message.answer(text, reply_markup=kb)
    else:
        await _safe_edit(cq, text, reply_markup=kb)


# ─── Users list ───────────────────────────────────────────────────────────────

async def _show_users(cq: CallbackQuery, config: Config, page: int = 0):
    client, srv = await get_client(_uid(cq), config)
    members = config.get_group_members(srv)

    if config.is_cluster(srv):
        users = await cluster_users_with_nodes(members)
    else:
        users = await _api_call(cq, client.get_users)
        if users is None:
            return

    active = sum(1 for u in users if u.get("current_connections", 0) > 0)
    cluster_hint = f" ⚙️ {srv.group}" if config.is_cluster(srv) else ""
    header = f"<b>👥 Клиенты{cluster_hint}</b>  {active} онлайн / {len(users)} всего"
    await _safe_edit(cq, header, reply_markup=users_list_kb(users, page, config=config, cluster=config.is_cluster(srv)))


@router.callback_query(F.data == "menu:users")
async def cb_users(cq: CallbackQuery, config: Config):
    await _show_users(cq, config, 0)


@router.callback_query(F.data.startswith("users:page:"))
async def cb_users_page(cq: CallbackQuery, config: Config):
    page = int(cq.data.split(":")[-1])
    await _show_users(cq, config, page)


@router.callback_query(F.data == "users:refresh")
async def cb_users_refresh(cq: CallbackQuery, config: Config):
    await _show_users(cq, config, 0)


# ─── Users extra ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "users:search")
async def cb_users_search(cq: CallbackQuery, state: FSMContext):
    await state.set_state(SearchUserFSM.waiting_query)
    await cq.answer()
    await cq.message.answer("🔍 Введите имя или часть имени клиента:")


@router.callback_query(F.data == "users:quota")
async def cb_users_quota(cq: CallbackQuery, config: Config):
    """Показывает сводку использования квот (GET /v1/users/quota, 3.4.12+)"""
    client, srv = await get_client(_uid(cq), config)
    members = config.get_group_members(srv)

    if config.is_cluster(srv):
        await cq.answer()
        async def _get_quota(node_srv):
            nc = TelemetClient(node_srv.url, node_srv.auth_header)
            try:
                data = await nc.get_users_quota()
                return node_srv.name, True, format_users_quota(data)
            except ApiError as e:
                if e.status == 404:
                    return node_srv.name, False, "⚠️ Требуется Telemt 3.4.12+"
                return node_srv.name, False, f"❌ {e.message}"

        results = await asyncio.gather(*[_get_quota(m) for m in members])
        sep = "─" * 28
        lines = []
        for name, ok, text in results:
            lines += [f"<b>⚙️ {name}</b>", sep, text, ""]
        from aiogram.utils.keyboard import InlineKeyboardBuilder as _IKB
        kb = _IKB()
        kb.button(text="◀️ Ещё", callback_data="users:extra")
        await _safe_edit(cq, "\n".join(lines).rstrip(), reply_markup=kb.as_markup())
    else:
        data = await _api_call(cq, client.get_users_quota)
        if data is None:
            return
        from aiogram.utils.keyboard import InlineKeyboardBuilder as _IKB
        kb = _IKB()
        kb.button(text="🔄 Обновить", callback_data="users:quota")
        kb.button(text="◀️ Ещё",      callback_data="users:extra")
        kb.adjust(2)
        await _safe_edit(cq, format_users_quota(data), reply_markup=kb.as_markup())


@router.callback_query(F.data == "users:extra")
async def cb_users_extra(cq: CallbackQuery):
    await _safe_edit(cq, "⚙️ <b>Действия со списком</b>", reply_markup=users_extra_kb())


@router.callback_query(F.data == "users:export_menu")
async def cb_export_menu(cq: CallbackQuery):
    await _safe_edit(cq, "📤 <b>Экспорт пользователей</b>", reply_markup=export_menu_kb())


@router.callback_query(F.data.startswith("users:export:"))
async def cb_users_export(cq: CallbackQuery, config: Config):
    fmt = cq.data.split(":")[-1]
    client, srv = await get_client(_uid(cq), config)
    users = await _api_call(cq, client.get_users)
    if not users:
        return
    await cq.answer("⏳ Генерирую файл...")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    if fmt == "csv":
        data = users_to_csv(users, srv.name)
        fname = f"telemt_{srv.name}_{ts}.csv"
        await cq.message.answer_document(
            BufferedInputFile(data, filename=fname),
            caption=f"📤 CSV — {srv.name} ({len(users)} клиентов)",
        )
    else:
        deltas = await db.get_all_users_traffic_delta(srv.name, days=7)
        data = users_to_xlsx(users, srv.name, deltas)
        fname = f"telemt_{srv.name}_{ts}.xlsx"
        await cq.message.answer_document(
            BufferedInputFile(data, filename=fname),
            caption=f"📊 Excel — {srv.name} ({len(users)} клиентов)\n"
                    f"<i>🟢 активные  🔴 истёкшие  Трафик за 7д из истории</i>",
        )


@router.callback_query(F.data.in_({"users:expiring", "users:expiring_menu"}))
async def cb_users_expiring(cq: CallbackQuery, config: Config):
    client, srv = await get_client(_uid(cq), config)
    members = config.get_group_members(srv)
    if config.is_cluster(srv):
        users = await cluster_users_with_nodes(members)
    else:
        users = await _api_call(cq, client.get_users)
        if users is None:
            return

    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=7)
    expired, expiring = [], []

    for u in users:
        exp = u.get("expiration_rfc3339")
        if not exp:
            continue
        try:
            exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
            if exp_dt < now:
                expired.append((u["username"], exp_dt))
            elif exp_dt < soon:
                expiring.append((u["username"], exp_dt))
        except Exception:
            pass

    lines = [f"<b>⏰ Сроки действия — {srv.group if srv.group else srv.name}</b>", ""]
    lines.append(f"🔴 <b>Истёкших: {len(expired)}</b>")
    for name, dt in expired:
        lines.append(f"  <code>{name}</code> — {dt.strftime('%Y-%m-%d')}")
    lines.append(f"\n🟡 <b>Истекают в течение 7 дней: {len(expiring)}</b>")
    for name, dt in expiring:
        lines.append(f"  <code>{name}</code> — {dt.strftime('%Y-%m-%d')}")

    from keyboards import users_delete_expired_confirm_kb as _exp_confirm_kb
    from aiogram.utils.keyboard import InlineKeyboardBuilder as _IKB
    exp_kb = _IKB()
    exp_kb.button(text="🧹 Удалить истёкших", callback_data="users:delete_expired_confirm")
    exp_kb.button(text="◀️ К списку", callback_data="menu:users")
    exp_kb.adjust(1)
    await _safe_edit(cq, "\n".join(lines), reply_markup=exp_kb.as_markup())


@router.callback_query(F.data == "users:delete_expired_confirm")
async def cb_delete_expired_confirm(cq: CallbackQuery, config: Config):
    client, _ = await get_client(_uid(cq), config)
    users = await _api_call(cq, client.get_users)
    if users is None:
        return
    now = datetime.now(timezone.utc)
    expired = [u["username"] for u in users if u.get("expiration_rfc3339") and
               _parse_exp(u["expiration_rfc3339"]) and _parse_exp(u["expiration_rfc3339"]) < now]
    if not expired:
        await cq.answer("Истёкших нет", show_alert=True)
        return
    names = ", ".join(expired[:8]) + ("..." if len(expired) > 8 else "")
    await _safe_edit(
        cq,
        f"⚠️ Удалить <b>{len(expired)}</b> истёкших?\n\n<code>{names}</code>",
        reply_markup=users_delete_expired_confirm_kb(),
    )


def _parse_exp(exp: str):
    try:
        return datetime.fromisoformat(exp.replace("Z", "+00:00"))
    except Exception:
        return None


@router.callback_query(F.data == "users:delete_expired")
async def cb_delete_expired(cq: CallbackQuery, config: Config):
    client, srv = await get_client(_uid(cq), config)
    members = config.get_group_members(srv)

    # Читаем список с любого узла
    users = await _api_call(cq, client.get_users)
    if users is None:
        return

    now = datetime.now(timezone.utc)
    expired = [
        u["username"] for u in users
        if (exp := _parse_exp(u.get("expiration_rfc3339", ""))) and exp < now
    ]

    deleted = errors = 0
    for username in expired:
        results = await cluster_write(members, "delete_user", username)
        if _all_ok(results):
            deleted += 1
        else:
            errors += 1

    await cq.answer(f"✅ Удалено: {deleted}, ошибок: {errors}")
    await _show_users(cq, config, 0)


# ─── User detail ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user:view:"))
async def cb_user_view(cq: CallbackQuery, config: Config):
    username = cq.data.split(":", 2)[2]
    client, srv = await get_client(_uid(cq), config)
    members = config.get_group_members(srv)

    if config.is_cluster(srv):
        # Читаем данные по каждому узлу параллельно
        async def _get_from_node(node_srv):
            nc = TelemetClient(node_srv.url, node_srv.auth_header)
            try:
                return node_srv.name, await nc.get_user(username)
            except Exception:
                return node_srv.name, None

        results = await asyncio.gather(*[_get_from_node(m) for m in members])
        user = None
        nodes = {}
        all_ips: set = set()
        max_recent_ips = 0

        for node_name, node_user in results:
            if node_user:
                if user is None:
                    user = dict(node_user)
                nodes[node_name] = node_user.get("current_connections", 0)
                # Собираем IP со всех узлов
                all_ips.update(node_user.get("active_unique_ips_list", []))
                max_recent_ips = max(max_recent_ips, node_user.get("recent_unique_ips", 0))

        if user is None:
            await cq.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Агрегируем данные
        user["current_connections"] = sum(nodes.values())
        user["_nodes"] = nodes
        user["active_unique_ips_list"] = list(all_ips)
        user["active_unique_ips"] = len(all_ips)
        user["recent_unique_ips"] = max_recent_ips
    else:
        user = await _api_call(cq, client.get_user, username)
        if user is None:
            return

    text = format_user_detail(user)
    kb = user_detail_kb(username)
    if cq.message.photo:
        await cq.answer()
        try:
            await cq.message.delete()
        except Exception:
            pass
        await cq.bot.send_message(cq.message.chat.id, text, reply_markup=kb)
    else:
        await _safe_edit(cq, text, reply_markup=kb)


# ─── Rotate secret ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user:rotate_secret:"))
async def cb_rotate_secret(cq: CallbackQuery, config: Config):
    username = cq.data.split(":", 2)[2]
    new_secret = _gen_secret()
    client, srv = await get_client(_uid(cq), config)
    members = config.get_group_members(srv)
    results = await cluster_write(members, "patch_user", username, {"secret": new_secret})
    ok_results = [r for r in results if r.ok]
    if not ok_results:
        await cq.answer("❌ Не удалось обновить секрет", show_alert=True)
        return
    user = ok_results[0].data
    status = ""
    if not _all_ok(results):
        status = "\n⚠️ " + _format_cluster_result([r for r in results if not r.ok])
    await cq.answer("✅ Секрет обновлён")
    await cq.message.answer(
        f"🔑 <b>Новый секрет — {username}</b>{status}\n\n"
        f"<code>{new_secret}</code>\n\n"
        f"<i>Сохраните — больше не будет показан</i>",
    )
    await _safe_edit(cq, format_user_detail(user), reply_markup=user_detail_kb(username))


# ─── Traffic history ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user:traffic:"))
async def cb_user_traffic(cq: CallbackQuery):
    username = cq.data.split(":", 2)[2]
    await _safe_edit(
        cq,
        f"📊 <b>История трафика — {username}</b>\n\nВыберите период:",
        reply_markup=traffic_period_kb(username),
    )


@router.callback_query(F.data.startswith("user:traffic_period:"))
async def cb_user_traffic_period(cq: CallbackQuery, config: Config):
    parts = cq.data.split(":")
    username, days = parts[2], int(parts[3])
    _, srv = await get_client(_uid(cq), config)
    await cq.answer()

    rows = await db.get_traffic_history(srv.name, username, days)
    delta_info = await db.get_traffic_delta(srv.name, username, days)

    if len(rows) < 2:
        text = (
            f"📊 <b>История — {username}</b> ({days}д)\n\n"
            f"⚠️ Данных пока мало (точек: {len(rows)})\n"
            f"<i>Сбор каждые 15 минут</i>"
        )
    else:
        lines = [
            f"<b>📊 Трафик — {username} ({days}д)</b>",
            f"  За период: <b>{fmt_bytes(delta_info['delta_bytes'])}</b>  |  Точек: {delta_info['points']}",
            "",
            "<b>Последние снимки:</b>",
        ]
        prev = None
        for r in rows[-12:]:
            dt = _tz.fmt_dt(r["sampled_at"], "%m-%d %H:%M")
            delta_str = f" +{fmt_bytes(max(0, r['octets'] - prev))}" if prev is not None else ""
            lines.append(f"  <code>{dt}</code>  {fmt_bytes(r['octets'])}{delta_str}  {r['connections']}🔌")
            prev = r["octets"]
        text = "\n".join(lines)

    kb = traffic_period_kb(username, days)

    if cq.message.photo:
        # Под фото: удаляем и шлём текст через bot напрямую
        try:
            await cq.message.delete()
        except Exception:
            pass
        await cq.bot.send_message(cq.message.chat.id, text, reply_markup=kb)
    else:
        try:
            await cq.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.startswith("user:traffic_chart:"))
async def cb_user_traffic_chart(cq: CallbackQuery, config: Config):
    """PNG-график трафика клиента. Если уже фото — заменяем его."""
    parts = cq.data.split(":")
    username, days = parts[2], int(parts[3])
    _, srv = await get_client(_uid(cq), config)
    await cq.answer("⏳ Строю график...")

    rows = await db.get_traffic_history(srv.name, username, days)
    if len(rows) < 2:
        await cq.answer("⚠️ Мало данных (нужно минимум 2 точки)", show_alert=True)
        return

    buf = await asyncio.get_event_loop().run_in_executor(
        None, charts.render_user_traffic, rows, username, days, srv.name
    )
    if buf is None:
        await cq.answer("⚠️ matplotlib не установлен на сервере", show_alert=True)
        return

    caption = f"📈 <b>{username}</b> — трафик за {days} дн. • {srv.name}"
    kb = traffic_period_kb(username, days, chart_mode=True)
    img_bytes = buf.read()

    if cq.message.photo:
        # Уже фото — заменяем через edit_media
        media = InputMediaPhoto(
            media=BufferedInputFile(img_bytes, filename=f"traffic_{username}_{days}d.png"),
            caption=caption,
        )
        try:
            await cq.message.edit_media(media=media, reply_markup=kb)
        except TelegramBadRequest:
            pass
    else:
        # Под текстом — удаляем текст, шлём фото через bot напрямую
        try:
            await cq.message.delete()
        except Exception:
            pass
        await cq.bot.send_photo(
            cq.message.chat.id,
            photo=BufferedInputFile(img_bytes, filename=f"traffic_{username}_{days}d.png"),
            caption=caption,
            reply_markup=kb,
        )


@router.callback_query(F.data.startswith("traffic_report_chart:"))
async def cb_traffic_report_chart(cq: CallbackQuery, config: Config):
    """PNG-график топ клиентов по трафику."""
    days = int(cq.data.split(":")[-1])
    _, srv = await get_client(_uid(cq), config)
    await cq.answer("⏳ Строю график...")

    deltas = await db.get_all_users_traffic_delta(srv.name, days=days)
    if not deltas:
        await cq.answer("⚠️ Нет данных за период", show_alert=True)
        return

    buf = await asyncio.get_event_loop().run_in_executor(
        None, charts.render_traffic_report, deltas, days, srv.name
    )
    if buf is None:
        await cq.answer("⚠️ matplotlib не установлен на сервере", show_alert=True)
        return

    from aiogram.types import BufferedInputFile, InputMediaPhoto
    media = InputMediaPhoto(
        media=BufferedInputFile(buf.read(), filename=f"report_{srv.name}_{days}d.png"),
        caption=f"📈 Топ клиентов — {days} дн. • {srv.name}",
    )
    # Если сообщение уже фото — редактируем его (не плодим новые)
    if cq.message.photo:
        try:
            await cq.message.edit_media(media=media, reply_markup=traffic_report_kb(chart_mode=True))
        except TelegramBadRequest:
            await cq.answer()  # контент не изменился — просто убираем часики
    else:
        await cq.message.delete()
        await cq.message.answer_photo(
            BufferedInputFile(buf.getvalue(), filename=f"report_{srv.name}_{days}d.png"),
            caption=f"📈 Топ клиентов — {days} дн. • {srv.name}",
            reply_markup=traffic_report_kb(chart_mode=True),
        )


# ─── Links + QR ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user:links:"))
async def cb_user_links(cq: CallbackQuery, config: Config):
    username = cq.data.split(":", 2)[2]
    client, _ = await get_client(_uid(cq), config)
    user = await _api_call(cq, client.get_user, username)
    if user is None:
        return
    all_links = _get_all_links(user)
    if not all_links:
        await _safe_edit(cq, f"<b>🔗 Ссылки — {username}</b>\n\n— нет ссылок —",
                         reply_markup=user_links_kb_no_links(username))
        return
    text, _ = format_user_links(user)
    await _safe_edit(cq, text, reply_markup=user_links_kb(username, all_links))


@router.callback_query(F.data.startswith("user:qr:"))
async def cb_user_qr(cq: CallbackQuery, config: Config):
    parts = cq.data.split(":")
    index, username = int(parts[-1]), ":".join(parts[2:-1])
    client, _ = await get_client(_uid(cq), config)
    user = await _api_call(cq, client.get_user, username)
    if user is None:
        return
    all_links = _get_all_links(user)
    if index >= len(all_links):
        await cq.answer("Ссылка не найдена", show_alert=True)
        return
    await cq.answer("Генерирую QR...")
    link = all_links[index]
    label = link_short_label(link, index)
    try:
        png = make_qr_bytes(link)
        photo = BufferedInputFile(png, filename=f"qr_{username}_{index}.png")
        caption = f"📷 {username}\n\n<code>{link}</code>"
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb = InlineKeyboardBuilder()
        kb.button(text="◀️ К ссылкам", callback_data=f"qr:back_links:{username}")
        kb.button(text="◀️ К клиенту", callback_data=f"qr:back_user:{username}")
        kb.adjust(1)
        # Удаляем текстовое сообщение, отправляем фото
        try:
            await cq.message.delete()
        except Exception:
            pass
        await cq.bot.send_photo(
            chat_id=cq.message.chat.id,
            photo=photo,
            caption=caption,
            reply_markup=kb.as_markup(),
        )
    except Exception as e:
        await cq.answer(f"❌ QR: {e}", show_alert=True)


@router.callback_query(F.data.startswith("qr:back_links:"))
async def cb_qr_back_links(cq: CallbackQuery, config: Config):
    """Возврат к ссылкам из QR-фото — удаляем фото, показываем ссылки"""
    username = cq.data.split(":", 2)[2]
    try:
        await cq.message.delete()
    except Exception:
        pass
    client, _ = await get_client(_uid(cq), config)
    user = await _api_call(cq, client.get_user, username)
    if user is None:
        return
    all_links = _get_all_links(user)
    text, _ = format_user_links(user)
    await cq.bot.send_message(
        chat_id=cq.message.chat.id,
        text=text,
        reply_markup=user_links_kb(username, all_links),
    )
    await cq.answer()


@router.callback_query(F.data.startswith("qr:back_user:"))
async def cb_qr_back_user(cq: CallbackQuery, config: Config):
    """Возврат к клиенту из QR-фото — удаляем фото, показываем карточку"""
    username = cq.data.split(":", 2)[2]
    try:
        await cq.message.delete()
    except Exception:
        pass
    client, _ = await get_client(_uid(cq), config)
    user = await _api_call(cq, client.get_user, username)
    if user is None:
        return
    await cq.bot.send_message(
        chat_id=cq.message.chat.id,
        text=format_user_detail(user),
        reply_markup=user_detail_kb(username),
    )
    await cq.answer()


@router.callback_query(F.data.startswith("user:qr_all:"))
async def cb_user_qr_all(cq: CallbackQuery, config: Config):
    username = cq.data.split(":", 2)[2]
    client, _ = await get_client(_uid(cq), config)
    user = await _api_call(cq, client.get_user, username)
    if user is None:
        return
    all_links = _get_all_links(user)
    if not all_links:
        await cq.answer("Ссылок нет", show_alert=True)
        return
    await cq.answer(f"Генерирую {len(all_links)} QR...")

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    # Удаляем исходное сообщение со ссылками
    try:
        await cq.message.delete()
    except Exception:
        pass

    for i, link in enumerate(all_links):
        label = link_short_label(link, i)
        is_last = (i == len(all_links) - 1)
        kb = InlineKeyboardBuilder()
        if is_last:
            kb.button(text="◀️ К клиенту", callback_data=f"qr:back_user:{username}")
            kb.adjust(1)
        try:
            png = make_qr_bytes(link)
            await cq.bot.send_photo(
                chat_id=cq.message.chat.id,
                photo=BufferedInputFile(png, filename=f"qr_{username}_{i}.png"),
                caption=f"📷 <b>{label}</b> — {username}\n\n<code>{link}</code>",
                reply_markup=kb.as_markup() if is_last else None,
            )
        except Exception as e:
            await cq.bot.send_message(cq.message.chat.id, f"❌ QR #{i}: {e}")


# ─── Delete ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user:delete_confirm:"))
async def cb_user_delete_confirm(cq: CallbackQuery):
    username = cq.data.split(":", 2)[2]
    await _safe_edit(cq, f"⚠️ Удалить <b>{username}</b>?\n\nДействие необратимо.",
                     reply_markup=user_delete_confirm_kb(username))


@router.callback_query(F.data.startswith("user:delete:"))
async def cb_user_delete(cq: CallbackQuery, config: Config):
    username = cq.data.split(":", 2)[2]
    _, srv = await get_client(_uid(cq), config)
    members = config.get_group_members(srv)

    results = await cluster_write(members, "delete_user", username)

    if _all_ok(results):
        await cq.answer(f"✅ {username} удалён")
    else:
        status = _format_cluster_result(results)
        await cq.answer(f"⚠️ Частичное удаление:\n{status}"[:200], show_alert=True)
    await _show_users(cq, config, 0)


# ─── /adduser ─────────────────────────────────────────────────────────────────

@router.message(Command("adduser"))
async def cmd_adduser(message: Message, config: Config):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "Использование: <code>/adduser имя [дней]</code>\n"
            "Пример: <code>/adduser vasya 30</code>"
        )
        return
    username = parts[1].strip()
    days = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None
    if not USERNAME_RE.match(username):
        await message.answer("❌ Неверное имя")
        return

    secret = _gen_secret()
    payload: dict = {"username": username, "secret": secret}
    if days:
        exp = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload["expiration_rfc3339"] = exp

    client, srv = await get_client(_uid(message), config)
    members = config.get_group_members(srv)
    results = await cluster_write(members, "create_user", payload)
    ok_results = [r for r in results if r.ok]

    if not ok_results:
        errors = _format_cluster_result(results)
        await message.answer(f"❌ Не удалось создать пользователя:\n{errors}")
        return

    result = ok_results[0].data
    user = result.get("user", result)
    all_links = _get_all_links(user)
    status = ""
    if len(members) > 1:
        status = "\n" + _format_cluster_result(results)
    elif not _all_ok(results):
        status = "\n⚠️ " + _format_cluster_result([r for r in results if not r.ok])
    msg = (f"✅ <b>{username}</b> создан{status}\n\n"
           f"🔑 Секрет: <code>{secret}</code>\n")
    if days:
        msg += f"📅 Срок: {days} дней\n"
    msg += "\n" + format_user_detail(user)
    await message.answer(msg, reply_markup=user_detail_kb(username))

    if all_links:
        try:
            png = make_qr_bytes(all_links[0])
            await message.answer_photo(
                BufferedInputFile(png, filename=f"qr_{username}.png"),
                caption=f"📷 {link_short_label(all_links[0], 0)}\n\n<code>{all_links[0]}</code>",
            )
        except Exception:
            pass


# ─── /find — поиск клиента ────────────────────────────────────────────────────

@router.message(Command("find"))
async def cmd_find(message: Message, state: FSMContext, config: Config):
    """Поиск клиента: /find vasya  или  /find (запрашивает имя)."""
    parts = message.text.split(maxsplit=1)
    if len(parts) >= 2:
        await _do_search(message, parts[1].strip(), config)
    else:
        await state.set_state(SearchUserFSM.waiting_query)
        await message.answer("🔍 Введите имя или часть имени клиента:")


@router.message(SearchUserFSM.waiting_query, F.text.regexp(r"^[^/]"))
async def fsm_search_query(message: Message, state: FSMContext, config: Config):
    # Если пользователь ввёл команду — сбрасываем FSM и не ищем
    if message.text and message.text.startswith("/"):
        await state.clear()
        return
    await state.clear()
    await _do_search(message, message.text.strip(), config)


async def _do_search(message: Message, query: str, config: Config):
    if not query:
        await message.answer("❌ Пустой запрос")
        return
    client, srv = await get_client(_uid(message), config)
    members = config.get_group_members(srv)

    if config.is_cluster(srv):
        users = await cluster_users_with_nodes(members)
    else:
        users = await _api_call(message, client.get_users)
        if users is None:
            return

    q = query.lower()
    found = [u for u in users if q in u["username"].lower()]
    if not found:
        await message.answer(f"🔍 По запросу <b>{query}</b> ничего не найдено")
        return
    if len(found) == 1:
        u = found[0]
        await message.answer(
            format_user_detail(u),
            reply_markup=user_detail_kb(u["username"]),
        )
    else:
        # Показываем список совпадений
        lines = [f"🔍 <b>Найдено: {len(found)}</b> по запросу «{query}»\n"]
        for u in found[:20]:
            conns = u.get("current_connections", 0)
            icon = "🟢" if conns > 0 else "⚪"
            octets = fmt_bytes(u.get("total_octets", 0))
            lines.append(f"{icon} <code>{u['username']}</code> — {octets}")
        if len(found) > 20:
            lines.append(f"\n<i>...и ещё {len(found) - 20}. Уточните запрос.</i>")
        await message.answer("\n".join(lines))


# ─── /alert_log — история алертов ─────────────────────────────────────────────

@router.message(Command("alert_log"))
async def cmd_alert_log(message: Message, config: Config):
    _, srv = await get_client(_uid(message), config)
    members = config.get_group_members(srv)

    if config.is_cluster(srv):
        # Собираем алерты со всех узлов кластера
        all_rows = []
        for member in members:
            rows = await db.get_recent_alerts(member.name, limit=20)
            for r in rows:
                r["_node"] = member.name
            all_rows.extend(rows)

        # Сортируем по времени (новые сначала) и берём 20
        all_rows.sort(key=lambda r: r["fired_at"], reverse=True)
        all_rows = all_rows[:20]

        title = f"cluster {srv.group}" if srv.group else srv.name
        if not all_rows:
            await message.answer(f"📋 <b>История алертов — {title}</b>\n\nПусто")
            return
        lines = [f"📋 <b>История алертов — {title}</b>\n"]
        for r in all_rows:
            dt = _tz.fmt_dt(r["fired_at"], "%m-%d %H:%M")
            node = r.get("_node", "")
            lines.append(f"<i>{dt}</i> [{node}] — {r['message']}")
    else:
        rows = await db.get_recent_alerts(srv.name, limit=20)
        if not rows:
            await message.answer(f"📋 <b>История алертов — {srv.name}</b>\n\nПусто")
            return
        lines = [f"📋 <b>История алертов — {srv.name}</b>\n"]
        for r in rows:
            dt = _tz.fmt_dt(r["fired_at"], "%m-%d %H:%M")
            lines.append(f"<i>{dt}</i> — {r['message']}")

    await message.answer("\n".join(lines))


# ─── Create User FSM ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "user:create")
async def cb_user_create_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(CreateUserFSM.username)
    await state.update_data(payload={})
    await _safe_edit(cq,
        "➕ <b>Новый клиент</b>\n\n"
        "Шаг 1/6: Имя\n<i>Буквы, цифры, _ . - (1–64 символа)</i>\n\n"
        "<i>Быстро: /adduser имя [дней]</i>")


@router.message(CreateUserFSM.username, F.text.regexp(r"^[^/]"))
async def fsm_create_username(message: Message, state: FSMContext):
    u = message.text.strip()
    if not USERNAME_RE.match(u):
        await message.answer("❌ Только A-Z a-z 0-9 _ . - (1–64 символа)")
        return
    await state.update_data(username=u)
    await state.set_state(CreateUserFSM.secret)
    await message.answer("Шаг 2/6: Секрет\n<i>32 hex-символа, /skip или /gen</i>")


@router.message(CreateUserFSM.secret)
async def fsm_create_secret(message: Message, state: FSMContext):
    if _is_command(message):
        await state.clear()
        return
    txt = message.text.strip()
    if txt == "/gen":
        txt = _gen_secret()
        await message.answer(f"🎲 <code>{txt}</code>")
    if txt != "/skip" and not re.match(r"^[0-9a-fA-F]{32}$", txt):
        await message.answer("❌ 32 hex-символа, /skip или /gen")
        return
    data = await state.get_data()
    pl = data.get("payload", {})
    if txt != "/skip":
        pl["secret"] = txt
    await state.update_data(payload=pl)
    await state.set_state(CreateUserFSM.max_tcp)
    await message.answer("Шаг 3/6: Max TCP\n<i>Число или /skip</i>")


@router.message(CreateUserFSM.max_tcp)
async def fsm_create_max_tcp(message: Message, state: FSMContext):
    if _is_command(message):
        await state.clear()
        return
    txt = message.text.strip()
    if txt != "/skip" and not txt.isdigit():
        await message.answer("❌ Число или /skip")
        return
    data = await state.get_data()
    pl = data.get("payload", {})
    if txt != "/skip":
        pl["max_tcp_conns"] = int(txt)
    await state.update_data(payload=pl)
    await state.set_state(CreateUserFSM.expiration)
    await message.answer("Шаг 4/6: Срок действия\n<i>Число дней (30/90/365), дата 2026-12-31T23:59:59Z, или /skip</i>")


@router.message(CreateUserFSM.expiration)
async def fsm_create_expiration(message: Message, state: FSMContext):
    if _is_command(message):
        await state.clear()
        return
    txt = message.text.strip()
    if txt != "/skip":
        if txt.isdigit():
            txt = (datetime.now(timezone.utc) + timedelta(days=int(txt))).strftime("%Y-%m-%dT%H:%M:%SZ")
            await message.answer(f"📅 <code>{txt}</code>")
        elif not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", txt):
            await message.answer("❌ Число дней, дата или /skip")
            return
    data = await state.get_data()
    pl = data.get("payload", {})
    if txt != "/skip":
        pl["expiration_rfc3339"] = txt
    await state.update_data(payload=pl)
    await state.set_state(CreateUserFSM.quota)
    await message.answer("Шаг 5/6: Квота трафика\n<i>Байты (10737418240 = 10GB) или /skip</i>")


@router.message(CreateUserFSM.quota)
async def fsm_create_quota(message: Message, state: FSMContext):
    if _is_command(message):
        await state.clear()
        return
    txt = message.text.strip()
    if txt != "/skip" and not txt.isdigit():
        await message.answer("❌ Число байт или /skip")
        return
    data = await state.get_data()
    pl = data.get("payload", {})
    if txt != "/skip":
        pl["data_quota_bytes"] = int(txt)
    await state.update_data(payload=pl)
    await state.set_state(CreateUserFSM.max_ips)
    await message.answer("Шаг 6/6: Max уникальных IP\n<i>Число или /skip</i>")


@router.message(CreateUserFSM.max_ips)
async def fsm_create_max_ips(message: Message, state: FSMContext):
    if _is_command(message):
        await state.clear()
        return
    txt = message.text.strip()
    if txt != "/skip" and not txt.isdigit():
        await message.answer("❌ Число или /skip")
        return
    data = await state.get_data()
    pl = data.get("payload", {})
    if txt != "/skip":
        pl["max_unique_ips"] = int(txt)
    await state.update_data(payload=pl)
    await state.set_state(CreateUserFSM.confirm)
    labels = {"secret": "Секрет", "max_tcp_conns": "Max TCP",
              "expiration_rfc3339": "Истекает", "data_quota_bytes": "Квота", "max_unique_ips": "Max IP"}
    lines = ["<b>📋 Подтверждение</b>", "", f"Имя: <b>{data['username']}</b>"]
    for k, v in pl.items():
        lines.append(f"{labels.get(k, k)}: {v}")
    lines.append("\n<b>да</b> — создать, <b>нет</b> — отмена:")
    await message.answer("\n".join(lines))


@router.message(CreateUserFSM.confirm)
async def fsm_create_confirm(message: Message, state: FSMContext, config: Config):
    if _is_command(message):
        await state.clear()
        return
    if message.text.strip().lower() not in ("да", "yes", "y", "д"):
        await state.clear()
        await message.answer("❌ Отменено. /menu")
        return
    data = await state.get_data()
    pl = {k: v for k, v in data.get("payload", {}).items() if v is not None}
    pl["username"] = data["username"]
    if "secret" not in pl:
        pl["secret"] = _gen_secret()
    await state.clear()
    client, srv = await get_client(_uid(message), config)
    members = config.get_group_members(srv)

    results = await cluster_write(members, "create_user", pl)
    ok_results = [r for r in results if r.ok]
    fail_results = [r for r in results if not r.ok]

    if not ok_results:
        errors = _format_cluster_result(results)
        await message.answer(f"❌ Не удалось создать пользователя:\n{errors}")
        return

    # Берём данные из первого успешного узла
    result = ok_results[0].data
    user = result.get("user", result)
    secret = result.get("secret", pl.get("secret", "—"))

    status_text = "\n\n<b>Статус по узлам:</b>\n" + _format_cluster_result(results) if len(members) > 1 else ""
    if fail_results:
        status_text += "\n\n⚠️ <b>Не синхронизировано:</b>\n" + _format_cluster_result(fail_results)

    await message.answer(
        f"✅ <b>{pl['username']}</b> создан!{status_text}\n\n"
        f"🔑 Секрет: <code>{secret}</code>\n\n"
        + format_user_detail(user),
        reply_markup=user_detail_kb(pl["username"]),
    )


# ─── Edit User Field FSM ──────────────────────────────────────────────────────

FIELD_LABELS = {
    "secret": ("🔑 Секрет", "32 hex-символа"),
    "max_tcp_conns": ("🔗 Max TCP", "целое число"),
    "expiration_rfc3339": ("📅 Срок", "число дней или 2026-12-31T23:59:59Z"),
    "data_quota_bytes": ("💾 Квота", "байты, например 10737418240 для 10GB"),
    "max_unique_ips": ("🌐 Max IP", "целое число"),
    "rate_limit_up_bps": ("⬆️ Лимит upload", "байт/с, например 1048576 для 1MB/s, 0 — снять"),
    "rate_limit_down_bps": ("⬇️ Лимит download", "байт/с, например 2097152 для 2MB/s, 0 — снять"),
}


@router.callback_query(F.data.startswith("user:edit:"))
async def cb_user_edit(cq: CallbackQuery):
    username = cq.data.split(":", 2)[2]
    await _safe_edit(cq, f"✏️ <b>Редактирование — {username}</b>\n\nВыберите поле:",
                     reply_markup=user_edit_kb(username))


@router.callback_query(F.data.startswith("user:editfield:"))
async def cb_user_editfield_start(cq: CallbackQuery, state: FSMContext):
    parts = cq.data.split(":")
    username, field = parts[2], parts[3]
    label, hint = FIELD_LABELS.get(field, (field, ""))
    await state.set_state(EditFieldFSM.waiting_value)
    await state.update_data(username=username, field=field)
    await _safe_edit(cq, f"✏️ <b>{label}</b> — {username}\n\n<i>({hint})</i>\nили /skip:")


@router.message(EditFieldFSM.waiting_value, F.text.regexp(r"^[^/]"))
async def fsm_edit_value(message: Message, state: FSMContext, config: Config):
    data = await state.get_data()
    username, field = data["username"], data["field"]
    txt = message.text.strip()
    await state.clear()
    if txt == "/skip":
        await message.answer("⏭ Без изменений. /menu")
        return
    value = txt
    if field in ("max_tcp_conns", "data_quota_bytes", "max_unique_ips"):
        if not txt.isdigit():
            await message.answer("❌ Нужно целое число")
            return
        value = int(txt)
    elif field in ("rate_limit_up_bps", "rate_limit_down_bps"):
        # Принимаем: 0 (снять), целое число байт/с, или null
        if txt.lower() in ("0", "нет", "null", "none", "—"):
            value = None  # удаляем лимит
        elif txt.isdigit():
            value = int(txt)
        else:
            await message.answer(
                "❌ Укажите скорость в байт/с (например <code>1048576</code> для 1 MB/s)\n"
                "или <code>0</code> чтобы снять лимит"
            )
            return
    elif field == "secret":
        if not re.match(r"^[0-9a-fA-F]{32}$", txt):
            await message.answer("❌ Ровно 32 hex-символа")
            return
    elif field == "expiration_rfc3339" and txt.isdigit():
        value = (datetime.now(timezone.utc) + timedelta(days=int(txt))).strftime("%Y-%m-%dT%H:%M:%SZ")

    client, srv = await get_client(_uid(message), config)
    members = config.get_group_members(srv)
    results = await cluster_write(members, "patch_user", username, {field: value})

    ok_results = [r for r in results if r.ok]
    if not ok_results:
        errors = _format_cluster_result(results)
        await message.answer(f"❌ Не удалось обновить:\n{errors}")
        return

    user = ok_results[0].data
    label = FIELD_LABELS.get(field, (field,))[0]
    status = ""
    if not _all_ok(results):
        status = "\n⚠️ " + _format_cluster_result([r for r in results if not r.ok])
    await message.answer(
        f"✅ {label} обновлён{status}\n\n" + format_user_detail(user),
        reply_markup=user_detail_kb(username),
    )


# ─── Runtime ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:runtime")
async def cb_runtime_menu(cq: CallbackQuery):
    await _safe_edit(cq, "<b>⚡ Runtime</b>\n\nВыберите раздел:", reply_markup=runtime_kb())


@router.callback_query(F.data == "runtime:gates")
async def cb_runtime_gates(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_runtime_gates", format_runtime_gates, runtime_sub_kb("gates"))


@router.callback_query(F.data == "runtime:init")
async def cb_runtime_init(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_runtime_initialization", format_runtime_init, runtime_sub_kb("init"))


@router.callback_query(F.data == "runtime:me_quality")
async def cb_runtime_me_quality(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_runtime_me_quality", format_me_quality, runtime_sub_kb("me_quality"))


@router.callback_query(F.data == "runtime:upstream_quality")
async def cb_runtime_upstream_quality(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_runtime_upstream_quality", format_upstream_quality, runtime_sub_kb("upstream_quality"))


@router.callback_query(F.data == "runtime:events")
async def cb_runtime_events(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_runtime_events", format_runtime_events, runtime_sub_kb("events"), 20)


@router.callback_query(F.data == "runtime:connections")
async def cb_runtime_connections(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_runtime_connections", format_connections, runtime_sub_kb("connections"))


# ─── Security ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:security")
async def cb_security_menu(cq: CallbackQuery):
    await _safe_edit(cq, "<b>🔒 Безопасность</b>", reply_markup=security_kb())


@router.callback_query(F.data == "security:posture")
async def cb_security_posture(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_security_posture", format_security_posture, security_sub_kb("posture"))


@router.callback_query(F.data == "security:whitelist")
async def cb_security_whitelist(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_security_whitelist", format_security_whitelist, security_sub_kb("whitelist"))


@router.callback_query(F.data == "security:limits")
async def cb_security_limits(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_limits_effective", format_limits, security_sub_kb("limits"))


# ─── Upstreams ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.in_({"menu:upstreams", "upstreams:refresh"}))
async def cb_upstreams(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_stats_upstreams", format_upstreams, upstreams_kb())


# ─── DCs ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.in_({"menu:dcs", "dcs:refresh"}))
async def cb_dcs_menu(cq: CallbackQuery):
    await _safe_edit(cq, "<b>📡 DC / Writers</b>", reply_markup=dcs_kb())


@router.callback_query(F.data == "dcs:status")
async def cb_dcs_status(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_stats_dcs", format_dcs, dcs_sub_kb("status"))


@router.callback_query(F.data == "dcs:writers")
async def cb_dcs_writers(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_stats_me_writers", format_me_writers, dcs_sub_kb("writers"))


# ─── Proxy checker ────────────────────────────────────────────────────────────

def _proxy_prompt_kb() -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой Меню — пока ждём ссылку."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder as _IKB
    kb = _IKB()
    kb.button(text="◀️ Меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "menu:proxy_check")
async def cb_proxy_check_menu(cq: CallbackQuery, state: FSMContext):
    await state.set_state(ProxyCheckFSM.waiting_url)
    await cq.answer()
    await cq.message.answer(
        "🔍 <b>Проверка MTProto прокси</b>\n\n"
        "Отправь ссылку на прокси в формате:\n"
        "<code>tg://proxy?server=HOST&port=443&secret=SECRET</code>\n\n"
        "или нажми кнопку «Подключиться» в любом канале — "
        "скопируй ссылку и отправь сюда.",
        reply_markup=_proxy_prompt_kb(),
    )


@router.callback_query(F.data == "proxy:check_again")
async def cb_proxy_check_again(cq: CallbackQuery, state: FSMContext):
    await state.set_state(ProxyCheckFSM.waiting_url)
    await cq.answer()
    await cq.message.answer(
        "🔍 Отправь ссылку на прокси:",
        reply_markup=_proxy_prompt_kb(),
    )


@router.message(ProxyCheckFSM.waiting_url, F.text.regexp(r"^[^/]"))
async def fsm_proxy_check_url(message: Message, state: FSMContext, config: Config):
    await state.clear()
    url = message.text.strip()

    if not (url.startswith("tg://") or "t.me/proxy" in url):
        await state.set_state(ProxyCheckFSM.waiting_url)
        await message.answer(
            "❌ Не удалось распознать ссылку.\n\n"
            "Ожидается формат:\n"
            "<code>tg://proxy?server=HOST&port=443&secret=SECRET</code>",
            reply_markup=_proxy_prompt_kb(),
        )
        return

    info = pc.parse_proxy_url(url)
    if info is None:
        await state.set_state(ProxyCheckFSM.waiting_url)
        await message.answer(
            "❌ Не удалось разобрать ссылку — проверь формат.",
            reply_markup=_proxy_prompt_kb(),
        )
        return

    wait_msg = await message.answer("⏳ Проверяю прокси...")
    info = await pc.check_proxy(
        info,
        timeout=5.0,
        agents=config.agents if config.agents else None,
    )

    try:
        await wait_msg.delete()
    except Exception:
        pass

    # Только после результата показываем кнопки «Проверить ещё» и «Меню»
    await message.answer(
        pc.format_proxy_result(info),
        reply_markup=proxy_check_kb(has_result=True),
    )


# ─── Alerts / Help ────────────────────────────────────────────────────────────

#@router.message(Command("alerts"))
#async def cmd_alerts(message: Message):
#    await message.answer(
#        "<b>🔔 Алерты</b>\n\n"
#        "Автоматические уведомления:\n"
#        "  🔴 Падение сервера\n"
#        "  🟢 Восстановление\n"
#        "  ⚠ Всплеск соединений &gt;50%\n"
#        "  ⚠ ME Writers coverage &lt;80%\n\n"
#        "Проверка: каждые 2 мин\n"
#        "Трафик: каждые 15 мин\n"
#        "Хранение: 30 дней",
#        reply_markup=alerts_kb(),
#    )
ALERT_LABELS = {
    "status_down":      "Падение сервера",
    "status_up":        "Восстановление",
    "conn_spike":       "Всплеск соединений",
    "writers_low":      "Writers coverage",
    "version_change":   "Обновление версии",
    "bad_unknown_sni":  "Неизвестный SNI",
    "hs_timeout_spike": "Всплеск HS timeout",
    "bad_client_spike": "Всплеск плохих TLS",
    "hs_conn_reset":    "Сброс при handshake",
}


@router.message(Command("alerts"))
async def cmd_alerts(message: Message, config: Config):
    uid = _uid(message)
    idx = await get_server_index(uid, config)
    srv = config.servers[idx]

    states = {}
    for atype in ALERT_LABELS:
        states[atype] = await get_alert(uid, srv.name, atype)

    await message.answer(
        "<b>🔔 Алерты</b>\n\n"
        "Автоматические уведомления:\n"
        "  🔴 Падение сервера\n"
        "  🟢 Восстановление\n"
        "  ⚠ Всплеск соединений &gt;50%\n"
        "  ⚠ ME Writers coverage &lt;80%\n"
        "  🏷 Обновление версии\n"
        "  ⚠ Неизвестный SNI\n"
        "  ⚠ Всплеск HS timeout\n"
        "  ⚠ Всплеск плохих TLS клиентов\n"
        "  ⚠ Сброс соединений при handshake\n\n"
        "Проверка: каждые 2 мин\n"
        "Трафик: каждые 15 мин\n"
        "Хранение: 30 дней",
        reply_markup=alerts_kb(states),
    )


@router.callback_query(F.data.startswith("alert:toggle:"))
async def cb_alert_toggle(cq: CallbackQuery, config: Config):
    uid = _uid(cq)
    alert_type = cq.data.split(":")[-1]
    idx = await get_server_index(uid, config)
    srv = config.servers[idx]

    current = await get_alert(uid, srv.name, alert_type)
    new_state = not current
    await set_alert(uid, srv.name, alert_type, threshold=None, enabled=new_state)

    label = ALERT_LABELS.get(alert_type, alert_type)
    await cq.answer(f"{'✅' if new_state else '☑️'} {label}: {'включён' if new_state else 'выключен'}")

    states = {}
    for atype in ALERT_LABELS:
        states[atype] = await get_alert(uid, srv.name, atype)

    await cq.message.edit_reply_markup(reply_markup=alerts_kb(states))


@router.message(Command("status"))
async def cmd_status(message: Message, config: Config):
    """/status — быстрый статус всех серверов"""
    lines = ["<b>⚡ Статус серверов</b>", ""]
    for srv in config.servers:
        from api_client import TelemetClient
        client = TelemetClient(srv.url, srv.auth_header)
        try:
            health = await client.get_health()
            summary = await client.get_stats_summary()
            status = health.get("status", "?")
            icon = "🟢" if status == "ok" else "🔴"
            conns = summary.get("connections_total", 0)
            users = summary.get("configured_users", 0)
            uptime_s = summary.get("uptime_seconds", 0)
            d, r = divmod(int(uptime_s), 86400)
            h, r = divmod(r, 3600)
            m = r // 60
            uptime = f"{d}д {h}ч {m}м" if d else f"{h}ч {m}м"
            lines.append(f"{icon} <b>{srv.name}</b>")
            lines.append(f"  Статус: {status}  |  {conns} соед.  |  {users} клиентов")
            lines.append(f"  Uptime: {uptime}")
        except Exception as e:
            lines.append(f"🔴 <b>{srv.name}</b> — недоступен")
            lines.append(f"  {type(e).__name__}: {e}")
        lines.append("")
    await message.answer("\n".join(lines))


@router.message(Command("id"))
async def cmd_id(message: Message):
    """/id — показать Telegram ID пользователя"""
    uid = message.from_user.id
    username = message.from_user.username or "—"
    name = message.from_user.full_name or "—"
    await message.answer(
        f"<b>ℹ️ Ваш Telegram ID</b>\n\n"
        f"ID: <code>{uid}</code>\n"
        f"Username: @{username}\n"
        f"Имя: {name}"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>📖 Telemt Manager Bot — справка</b>\n"
        "\n"
        "<b>Команды</b>\n"
        "/menu — главное меню\n"
        "/adduser <code>имя [дней]</code> — быстро создать клиента\n"
        "       <i>пример: /adduser vasya 30</i>\n"
        "/find <code>запрос</code> — поиск клиента по имени\n"
        "       <i>пример: /find vas  →  найдёт vasya, vasiliy…</i>\n"
        "/alerts — включить / выключить алерты\n"
        "/alert_log — история последних 20 алертов\n"
        "/id — ваш Telegram ID\n"
        "\n"
        "<b>Главное меню</b>\n"
        "🟢 <b>Состояние сервера</b> — dashboard: статус, uptime, версия, "
        "соединения, bad-классы, handshake-ошибки\n"
        "📊 <b>Отчёт по трафику</b> — все клиенты за 1/7/30 дней, "
        "сортировка по потреблению, 📈 график топ-15\n"
        "👥 <b>Все клиенты</b> — список с пагинацией и 🔍 поиском\n"
        "➕ <b>Новый клиент</b> — пошаговый мастер (6 шагов)\n"
        "⚡ <b>Runtime</b> — Gates, Init, ME Quality, Upstream Quality, "
        "Events, Connections\n"
        "⚠️ <b>Истекающие</b> — клиенты с истекающим сроком, "
        "массовое удаление истёкших\n"
        "🔒 <b>Безопасность</b> — Posture, IP Whitelist, Effective Limits\n"
        "🔗 <b>Upstreams</b> — RTT и статус апстримов\n"
        "📡 <b>DC / Writers</b> — статус датацентров и ME Writers\n"
        "📤 <b>Бэкап</b> — выгрузка <code>telemt.toml</code> файлом в чат\n"
        "\n"
        "<b>Карточка клиента</b>\n"
        "Редактирование полей • смена секрета • 📊 история трафика "
        "с 📈 графиком (24ч / 7 / 14 / 30 дней) • QR-коды ссылок\n"
        "\n"
        "<b>Алерты</b> — 9 типов:\n"
        "падение / восстановление сервера • всплеск соединений • "
        "Writers coverage • обновление версии • неизвестный SNI • "
        "всплеск HS timeout • плохих TLS клиентов • сброс при handshake\n"
        "Cooldown и пороги настраиваются через <code>.env</code>\n"
        "\n"
        "<b>Мультисервер</b> — переключение серверов прямо из главного меню. "
        "Выбор сохраняется между перезапусками бота."
    )
