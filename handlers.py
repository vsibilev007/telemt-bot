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
from aiogram.types import (
    BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, InputMediaPhoto,
    LinkPreviewOptions, Message, ReplyKeyboardRemove,
)

_NO_LINK_PREVIEW = LinkPreviewOptions(is_disabled=True)


from api_client import ApiError, TelemetClient, cluster_write, cluster_read, cluster_users_with_nodes, NodeResult
from config import Config
import database as db
from i18n import t
from export_utils import users_to_csv, users_to_xlsx
from formatters import (
    format_connections, format_dashboard, format_dcs,
    format_limits, format_me_quality, format_me_pool, format_me_selftest, format_me_writers,
    format_minimal_all, format_nat_stun, format_health_ready, format_runtime_events,
    format_runtime_gates, format_runtime_init, format_security_posture,
    format_active_ips, format_zero_all,
    format_security_whitelist, format_tls_fingerprints, format_upstream_quality,
    format_upstreams, format_user_detail, format_user_links,
    format_users_quota, fmt_bytes,
)
from keyboards import (
    ALERT_LABELS,
    alerts_kb, dashboard_kb, dcs_kb, dcs_sub_kb, export_menu_kb,
    main_menu_kb, runtime_kb, runtime_sub_kb, security_kb, security_sub_kb,
    sysinfo_kb, traffic_period_kb, traffic_report_kb, upstreams_kb,
    proxy_check_kb,
    config_edit_sections_kb, config_edit_fields_kb, config_edit_after_kb, user_delete_confirm_kb, user_detail_kb, user_edit_kb,
    users_sel_delete_confirm_kb,
    user_links_kb, users_active_ips_kb, users_delete_expired_confirm_kb,
    users_extra_kb, users_list_kb,
    web_menu_kb, web_sessions_kb, web_session_detail_kb,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from session import get_client, get_server_index, set_server_index
from sysinfo import get_system_info, format_system_status
import charts
import proxy_checker as pc
from proxy_checker import format_node_result
from states import CreateUserFSM, BulkCreateFSM, EditFieldFSM, SearchUserFSM, ProxyCheckFSM, NodeCheckFSM, ConfigEditFSM
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
                return node_srv.name, False, t("h.cluster.node_err", err=str(e)[:80])

        results = await asyncio.gather(*[_get_node(m) for m in members])
        sep = "─" * 28
        lines = []
        for name, ok, text in results:
            lines += [f"<b>⚙️ {name}</b>", sep, text, ""]
        await _safe_edit(cq, "\n".join(lines).rstrip(), reply_markup=kb)
    else:
        method = getattr(client, api_method)
        data = await _api_call(cq, method, *args)
        if data is not None:
            await _safe_edit(cq, formatter(data), reply_markup=kb)


router = Router()
router.include_router(export_toml_router)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _uid(event) -> int:
    return event.from_user.id


async def _lite_blocked(message: Message, config: Config) -> bool:
    """True, если команда отключена в lite-режиме (ответ уже отправлен)."""
    if config.lite_mode:
        await message.answer(t("h.lite_blocked"))
        return True
    return False


async def _safe_edit(cq: CallbackQuery, text: str, reply_markup=None, link_preview=None):
    try:
        await cq.message.edit_text(
            text,
            reply_markup=reply_markup,
            link_preview_options=link_preview,
        )
    except Exception as e:
        logger.debug("_safe_edit: %s", e)
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


# Кэш версии Telemt для серверов (сбрасывается при смене сервера)
_telemt_version_cache: dict[str, str] = {}


async def _get_telemt_version(client) -> str:
    """Получает версию Telemt с кэшированием."""
    cache_key = client.base_url
    if cache_key in _telemt_version_cache:
        return _telemt_version_cache[cache_key]
    try:
        info = await client.get_system_info()
        version = info.get("version", "")
        _telemt_version_cache[cache_key] = version
        return version
    except Exception:
        return ""


def _version_at_least(version: str, major: int, minor: int, patch: int = 0) -> bool:
    """True, если версия >= указанной. Пустая/неразборчивая версия → True (не ограничиваем)."""
    try:
        parts = tuple(int(p) for p in version.split(".")[:3])
        if len(parts) < 3:
            parts = parts + (0,) * (3 - len(parts))
        return parts >= (major, minor, patch)
    except (ValueError, AttributeError):
        return True


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
    name = message.from_user.first_name or t("h.common.default_name")
    await message.answer(
        t("h.start.hello", name=name),
        reply_markup=ReplyKeyboardRemove(),
    )
    client, _ = await get_client(uid, config)
    telemt_version = await _get_telemt_version(client)
    await message.answer(
        f"<b>Telemt Manager</b> — <code>{srv.group if config.is_cluster(srv) else srv.name}</code>",
        reply_markup=main_menu_kb(config.servers, idx, conns, status, config, telemt_version),
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, config: Config):
    """Главное меню без приветствия."""
    uid = _uid(message)
    idx = await get_server_index(uid, config)
    srv = config.servers[idx]
    status, conns = await _get_menu_state(uid, config)
    client, _ = await get_client(uid, config)
    telemt_version = await _get_telemt_version(client)
    await message.answer(
        f"<b>Telemt Manager</b> — <code>{srv.group if config.is_cluster(srv) else srv.name}</code>",
        reply_markup=main_menu_kb(config.servers, idx, conns, status, config, telemt_version),
    )


@router.callback_query(F.data == "menu:main")
async def cb_menu_main(cq: CallbackQuery, config: Config):
    """Возврат в главное меню — работает под любым типом сообщения."""
    uid = _uid(cq)
    idx = await get_server_index(uid, config)
    srv = config.servers[idx]
    status, conns = await _get_menu_state(uid, config)
    client, _ = await get_client(uid, config)
    telemt_version = await _get_telemt_version(client)
    text = f"<b>Telemt Manager</b> — <code>{srv.group if srv.group else srv.name}</code>"
    kb = main_menu_kb(config.servers, idx, conns, status, config, telemt_version)

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
    try:
        idx = int(cq.data.split(":")[-1])
    except (ValueError, IndexError):
        await cq.answer(t("h.server.bad_index"), show_alert=True)
        return
    if idx < 0 or idx >= len(config.servers):
        await cq.answer(t("h.server.not_found"), show_alert=True)
        return
    await set_server_index(_uid(cq), idx)
    srv = config.servers[idx]
    await cq.answer(f"✅ {srv.name}", show_alert=False)
    status, conns = await _get_menu_state(_uid(cq), config)
    client, _ = await get_client(_uid(cq), config)
    telemt_version = await _get_telemt_version(client)
    await _safe_edit(
        cq,
        f"<b>Telemt Manager</b> — <code>{srv.group if config.is_cluster(srv) else srv.name}</code>",
        reply_markup=main_menu_kb(config.servers, idx, conns, status, config, telemt_version),
    )


# ─── System info ──────────────────────────────────────────────────────────────

async def _show_sysinfo(cq: CallbackQuery, config: Config):
    await cq.answer(t("h.common.gathering"))
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
        t("h.sysinfo.title", srv=srv.name)
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
                return node_srv.name, False, t("h.cluster.unreachable", srv=node_srv.name, err=e)

        results = await asyncio.gather(*[_get_node_data(m) for m in members])

        # Собираем общий дашборд кластера
        lines = [t("h.cluster.title", group=srv.group)]
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
        t("h.tr.menu"),
        reply_markup=traffic_report_kb(),
    )


@router.callback_query(F.data.startswith("traffic_report:"))
async def cb_traffic_report(cq: CallbackQuery, config: Config):
    days = int(cq.data.split(":")[-1])
    client, srv = await get_client(_uid(cq), config)
    await cq.answer(t("h.common.counting"))
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
        t("h.tr.title", srv=(srv.group or srv.name)),
        t("h.tr.sub", days=days, users=len(users), active=active),
        t("h.tr.total", total=fmt_bytes(total_delta)),
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
                    exp_str = t("h.tr.expired_tag")
                elif exp_dt < datetime.now(timezone.utc) + timedelta(days=7):
                    exp_str = t("h.tr.soon_tag")
            except Exception:
                pass
        lines.append(f"{icon} <code>{name}</code>{exp_str}")
        lines.append(t("h.tr.row", period=d_str, total=total, conns=conns))

    if len(sorted_users) > 20:
        lines.append(t("h.tr.more", n=len(sorted_users) - 20))

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
    header = t("h.users.header", hint=cluster_hint, active=active, total=len(users))
    await _safe_edit(cq, header, reply_markup=users_list_kb(users, page, config=config, cluster=config.is_cluster(srv)))


@router.callback_query(F.data == "menu:users")
async def cb_users(cq: CallbackQuery, config: Config):
    await _show_users(cq, config, 0)


@router.callback_query(F.data.startswith("users:page:"))
async def cb_users_page(cq: CallbackQuery, config: Config):
    try:
        page = int(cq.data.split(":")[-1])
    except (ValueError, IndexError):
        await cq.answer(t("h.users.bad_page"), show_alert=True)
        return
    # В режиме выбора листаем сохранённый список, не запрашивая API заново
    if _uid(cq) in _users_selection:
        await _show_users_sel(cq, config, max(0, page))
        return
    await _show_users(cq, config, max(0, page))


@router.callback_query(F.data == "users:refresh")
async def cb_users_refresh(cq: CallbackQuery, config: Config):
    # «Обновить» сбрасывает режим выбора и перезагружает данные
    _users_selection.pop(_uid(cq), None)
    await _show_users(cq, config, 0)


# ─── Массовый выбор юзеров (чекбоксы) ─────────────────────────────────────────

# Хранилище режима выбора: uid → {"users", "selected", "page", "cluster"}
_users_selection: dict[int, dict] = {}


def _sel_names(selected: set) -> str:
    names = sorted(selected)
    shown = ", ".join(f"<code>{n}</code>" for n in names[:15])
    return shown + (t("h.common.more", n=len(names) - 15) if len(names) > 15 else "")


async def _show_users_sel(cq: CallbackQuery, config: Config, page: int = 0):
    """Перерисовывает список в режиме выбора (без повторного запроса к API)."""
    st = _users_selection.get(_uid(cq))
    if not st:
        await _show_users(cq, config, 0)
        return
    st["page"] = page
    header = (
        t("h.users.sel_header", n=len(st['selected']), total=len(st['users']),
          names=(_sel_names(st['selected']) or "—"))
    )
    await _safe_edit(
        cq, header,
        reply_markup=users_list_kb(
            st["users"], page, cluster=st["cluster"],
            sel_mode=True, selected=st["selected"],
        ),
    )


async def _fetch_users(uid: int, config: Config):
    """(users, srv, members) или (None, srv, members) при ошибке API."""
    client, srv = await get_client(uid, config)
    members = config.get_group_members(srv)
    try:
        if config.is_cluster(srv):
            users = await cluster_users_with_nodes(members)
        else:
            users = await client.get_users()
    except ApiError as e:
        await cq_safe_error(e)
        return None, srv, members
    return users, srv, members


async def cq_safe_error(e: ApiError):
    """Заглушка-логгер для ошибок API вне _api_call."""
    logger.warning("users fetch failed: %s", e)


@router.callback_query(F.data.startswith("users:sel_enter:"))
async def cb_users_sel_enter(cq: CallbackQuery, config: Config):
    """Вход в режим выбора: загружаем список и запоминаем выбор."""
    users, srv, members = await _fetch_users(_uid(cq), config)
    if users is None:
        await cq.answer(t("h.common.fetch_failed"), show_alert=True)
        return
    try:
        page = max(0, int(cq.data.split(":")[-1]))
    except ValueError:
        page = 0
    _users_selection[_uid(cq)] = {
        "users": users, "selected": set(), "page": page,
        "cluster": config.is_cluster(srv),
    }
    await _show_users_sel(cq, config, page)


@router.callback_query(F.data.startswith("users:sel_exit:"))
async def cb_users_sel_exit(cq: CallbackQuery, config: Config):
    _users_selection.pop(_uid(cq), None)
    await _show_users(cq, config, 0)


@router.callback_query(F.data.startswith("users:sel_back:"))
async def cb_users_sel_back(cq: CallbackQuery, config: Config):
    st = _users_selection.get(_uid(cq))
    await _show_users_sel(cq, config, st["page"] if st else 0)


@router.callback_query(F.data.startswith("user:sel:"))
async def cb_user_sel_toggle(cq: CallbackQuery, config: Config):
    """Отметить/снять юзера в режиме выбора."""
    name = cq.data.split(":", 2)[2]
    st = _users_selection.get(_uid(cq))
    if not st:
        await _show_users(cq, config, 0)
        return
    if name in st["selected"]:
        st["selected"].discard(name)
    else:
        st["selected"].add(name)
    await _show_users_sel(cq, config, st["page"])


async def _send_fresh_users_list(cq: CallbackQuery, config: Config):
    """После массовой операции: новый список отдельным сообщением."""
    users, _, _ = await _fetch_users(_uid(cq), config)
    if users is None:
        return
    active = sum(1 for u in users if u.get("current_connections", 0) > 0)
    await cq.message.answer(
        t("h.users.header", hint="", active=active, total=len(users)),
        reply_markup=users_list_kb(users, 0, config=config),
    )


@router.callback_query(F.data.startswith("users:sel_do:"))
async def cb_users_sel_do(cq: CallbackQuery, config: Config):
    """Массовое включение/отключение выбранных."""
    action = cq.data.split(":")[-1]
    st = _users_selection.get(_uid(cq))
    if not st or not st["selected"]:
        await cq.answer(t("h.bulk.nobody"), show_alert=True)
        return
    names = sorted(st["selected"])
    _, srv, members = await _fetch_users(_uid(cq), config)

    method = "enable_user" if action == "enable" else "disable_user"
    await cq.answer(t("h.bulk.start_enable" if action == "enable" else "h.bulk.start_disable", n=len(names)))

    # Последовательно: API сервера сериализует мутации одним локом
    report: list[str] = []
    failed = 0
    for name in names:
        results = await cluster_write(members, method, name)
        if _all_ok(results):
            report.append(f"✅ {name}")
        else:
            failed += 1
            report.append(f"❌ {name}: {_format_cluster_result([r for r in results if not r.ok])[:120]}")

    icon = "🟢" if action == "enable" else "🔴"
    verb = t("h.bulk.enabled_many") if action == "enable" else t("h.bulk.disabled_many")
    text = t("h.bulk.result_header", icon=icon, verb=verb, ok=len(names) - failed, total=len(names)) + "\n\n"
    text += "\n".join(report[:30]) + (t("h.common.more_nl", n=len(report) - 30) if len(report) > 30 else "")

    _users_selection.pop(_uid(cq), None)
    await _safe_edit(cq, text)
    await _send_fresh_users_list(cq, config)


@router.callback_query(F.data.startswith("users:sel_del:"))
async def cb_users_sel_del(cq: CallbackQuery, config: Config):
    """Удаление выбранных: 0 — подтверждение, 1 — исполнение."""
    stage = cq.data.split(":")[-1]
    st = _users_selection.get(_uid(cq))
    if not st or not st["selected"]:
        await cq.answer(t("h.bulk.nobody"), show_alert=True)
        return

    if stage != "1":
        await _safe_edit(
            cq,
            t("h.bulk.del_confirm", n=len(st['selected'])) + "\n\n"
            f"{_sel_names(st['selected'])}\n\n"
            + t("h.bulk.irreversible"),
            reply_markup=users_sel_delete_confirm_kb(len(st["selected"])),
        )
        return

    names = sorted(st["selected"])
    await cq.answer(t("h.bulk.deleting", n=len(names)))
    _, srv, members = await _fetch_users(_uid(cq), config)

    # Сначала снимаем WEB-профили на всех узлах (иначе API отклонит удаление)
    for node in members:
        try:
            await _strip_web_profiles(TelemetClient(node.url, node.auth_header), st["selected"])
        except Exception as e:
            logger.warning("WEB profile strip failed on %s: %s", node.name, e)

    report: list[str] = []
    failed = 0
    for name in names:
        results = await cluster_write(members, "delete_user", name)
        if _all_ok(results):
            report.append(f"🗑 {name}")
        else:
            failed += 1
            report.append(f"❌ {name}: {_format_cluster_result([r for r in results if not r.ok])[:120]}")

    text = t("h.bulk.deleted_header", ok=len(names) - failed, total=len(names)) + "\n\n"
    text += "\n".join(report[:30]) + (f"\n…ещё {len(report) - 30}" if len(report) > 30 else "")
    if failed:
        text += t("h.bulk.not_deleted", n=failed)

    _users_selection.pop(_uid(cq), None)
    await _safe_edit(cq, text)
    await _send_fresh_users_list(cq, config)


# ─── Users extra ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "users:search")
async def cb_users_search(cq: CallbackQuery, state: FSMContext):
    await state.set_state(SearchUserFSM.waiting_query)
    await cq.answer()
    await cq.message.answer(t("h.search.prompt"))


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
                    return node_srv.name, False, t("h.quota.old_api")
                return node_srv.name, False, f"❌ {e.message}"

        results = await asyncio.gather(*[_get_quota(m) for m in members])
        sep = "─" * 28
        lines = []
        for name, ok, text in results:
            lines += [f"<b>⚙️ {name}</b>", sep, text, ""]
        from aiogram.utils.keyboard import InlineKeyboardBuilder as _IKB
        kb = _IKB()
        kb.button(text=t("h.extra.more"), callback_data="users:extra")
        await _safe_edit(cq, "\n".join(lines).rstrip(), reply_markup=kb.as_markup())
    else:
        data = await _api_call(cq, client.get_users_quota)
        if data is None:
            return
        from aiogram.utils.keyboard import InlineKeyboardBuilder as _IKB
        kb = _IKB()
        kb.button(text=t("h.extra.refresh"), callback_data="users:quota")
        kb.button(text=t("h.extra.more"),      callback_data="users:extra")
        kb.adjust(2)
        await _safe_edit(cq, format_users_quota(data), reply_markup=kb.as_markup())


@router.callback_query(F.data == "users:active_ips")
async def cb_users_active_ips(cq: CallbackQuery, config: Config):
    await _cluster_section(
        cq, config,
        "get_stats_users_active_ips",
        format_active_ips,
        users_active_ips_kb(),
    )


@router.callback_query(F.data == "users:extra")
async def cb_users_extra(cq: CallbackQuery):
    await _safe_edit(cq, t("h.extra.title"), reply_markup=users_extra_kb())


@router.callback_query(F.data == "users:export_menu")
async def cb_export_menu(cq: CallbackQuery):
    await _safe_edit(cq, t("h.export.title"), reply_markup=export_menu_kb())


@router.callback_query(F.data.startswith("users:export:"))
async def cb_users_export(cq: CallbackQuery, config: Config):
    fmt = cq.data.split(":")[-1]
    client, srv = await get_client(_uid(cq), config)
    users = await _api_call(cq, client.get_users)
    if not users:
        return
    await cq.answer(t("h.export.generating"))
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    if fmt == "csv":
        data = users_to_csv(users, srv.name)
        fname = f"telemt_{srv.name}_{ts}.csv"
        await cq.message.answer_document(
            BufferedInputFile(data, filename=fname),
            caption=t("h.export.csv", srv=srv.name, n=len(users)),
        )
    else:
        deltas = await db.get_all_users_traffic_delta(srv.name, days=7)
        data = users_to_xlsx(users, srv.name, deltas)
        fname = f"telemt_{srv.name}_{ts}.xlsx"
        await cq.message.answer_document(
            BufferedInputFile(data, filename=fname),
            caption=t("h.export.xlsx", srv=srv.name, n=len(users)),
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

    lines = [t("h.expiring.title", srv=(srv.group or srv.name)), ""]
    lines.append(t("h.expiring.expired", n=len(expired)))
    for name, dt in expired:
        lines.append(f"  <code>{name}</code> — {dt.strftime('%Y-%m-%d')}")
    lines.append(t("h.expiring.soon", n=len(expiring)))
    for name, dt in expiring:
        lines.append(f"  <code>{name}</code> — {dt.strftime('%Y-%m-%d')}")

    from aiogram.utils.keyboard import InlineKeyboardBuilder as _IKB
    exp_kb = _IKB()
    exp_kb.button(text=t("h.expiring.menu_btn"), callback_data="users:delete_expired_confirm")
    exp_kb.button(text=t("h.common.to_list"), callback_data="menu:users")
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
        await cq.answer(t("h.expiring.none"), show_alert=True)
        return
    names = ", ".join(expired[:8]) + ("..." if len(expired) > 8 else "")
    await _safe_edit(
        cq,
        t("h.expiring.confirm", n=len(expired), names=names),
        reply_markup=users_delete_expired_confirm_kb(),
    )


# ─── Массовое создание юзеров ─────────────────────────────────────────────────

# Лимит имени для bulk: имя попадает в callback "user:links:{name}" (64 байта)
BULK_NAME_MAX = 40
BULK_MAX_COUNT = 50
def _bulk_spec_help() -> str:
    return t(
        "h.bulk.spec_help",
        max_count=BULK_MAX_COUNT, name_max=BULK_NAME_MAX,
    )


def _bulk_names(template: str, count: int) -> list[str]:
    """guest → guest1..guestN; vpn{n} → vpn1..vpnN."""
    if "{n}" in template:
        return [template.replace("{n}", str(i)) for i in range(1, count + 1)]
    return [f"{template}{i}" for i in range(1, count + 1)]


def _parse_bulk_spec(text: str) -> tuple[list[str], int, int]:
    """Разбирает 'шаблон N дней [квота_GB]'. Бросает ValueError с текстом ошибки."""
    parts = text.split()
    if len(parts) < 3 or len(parts) > 4:
        raise ValueError(t("h.bulk.need_args"))

    template, cnt_raw, days_raw = parts[0], parts[1], parts[2]
    quota_raw = parts[3] if len(parts) == 4 else "0"

    try:
        count = int(cnt_raw)
        days = int(days_raw)
        quota_gb = int(quota_raw)
    except ValueError:
        raise ValueError(t("h.bulk.need_ints"))

    if not 1 <= count <= BULK_MAX_COUNT:
        raise ValueError(t("h.bulk.count_range", n=BULK_MAX_COUNT))
    if not 0 <= days <= 3650:
        raise ValueError(t("h.bulk.days_range"))
    if not 0 <= quota_gb <= 1024:
        raise ValueError(t("h.bulk.quota_range"))

    names = _bulk_names(template, count)
    for name in names:
        if not USERNAME_RE.match(name):
            raise ValueError(t("h.bulk.bad_name", name=name))
        if len(name) > BULK_NAME_MAX:
            raise ValueError(t("h.bulk.name_too_long", name=name, n=BULK_NAME_MAX))
    return names, days, quota_gb


@router.callback_query(F.data == "user:bulk")
async def cb_user_bulk(cq: CallbackQuery, state: FSMContext):
    await state.set_data({})
    await state.set_state(BulkCreateFSM.waiting_template)
    await _safe_edit(
        cq,
        t("h.bulk.wiz.t1") + "\n\n" + _bulk_spec_help(),
        reply_markup=InlineKeyboardBuilder()
        .button(text=t("h.bulk.cancel_btn"), callback_data="bulk:cancel")
        .adjust(1).as_markup(),
    )


@router.message(BulkCreateFSM.waiting_template, F.text)
async def fsm_bulk_template(message: Message, state: FSMContext):
    if (message.text or "").startswith("/"):
        await state.clear()
        await message.answer(t("h.bulk.cancelled"))
        return
    txt = message.text.strip()
    # Быстрый путь: целая строка спеки «guest 5 30» → сразу превью
    if len(txt.split()) >= 2:
        try:
            names, days, quota_gb = _parse_bulk_spec(txt)
        except ValueError:
            names = None
        if names:
            await state.update_data(bulk={
                "tpl": txt.split()[0], "count": len(names),
                "days": days, "date": "", "quota_gb": quota_gb, "web": True,
            })
            await state.set_state(BulkCreateFSM.confirm)
            await message.answer(
                "\n".join(_bulk_summary_lines((await state.get_data())["bulk"])),
                reply_markup=_bulk_preview_kb((await state.get_data())["bulk"]),
            )
            return
    # одиночный токен — шаблон
    base = txt.replace("{n}", "")
    if not base or not USERNAME_RE.match(base) or len(_bulk_names(txt, 2)[0]) > BULK_NAME_MAX:
        await message.answer(t("h.bulk.wiz.t1_bad"))
        return
    await state.update_data(bulk={
        "tpl": txt, "count": 0, "days": 0, "date": "", "quota_gb": 0, "web": True,
    })
    await state.set_state(BulkCreateFSM.waiting_count)
    await message.answer(t("h.bulk.wiz.t2"), reply_markup=_bulk_count_kb())


def _bulk_count_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for n in (5, 10, 25, 50):
        kb.button(text=str(n), callback_data=f"bulk:count:{n}")
    kb.button(text=t("h.bulk.wiz.btn_custom"), callback_data="bulk:count:0")
    kb.button(text=t("h.bulk.cancel_btn"), callback_data="bulk:cancel")
    kb.adjust(4, 1, 1)
    return kb.as_markup()


def _bulk_days_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for n in (7, 30, 90):
        kb.button(text=t("h.bulk.wiz.btn_days", n=n), callback_data=f"bulk:days:{n}")
    kb.button(text=t("h.bulk.wiz.btn_noexp"), callback_data="bulk:days:0")
    kb.button(text=t("h.bulk.wiz.btn_date"), callback_data="bulk:days:date")
    kb.button(text=t("h.bulk.wiz.btn_back"), callback_data="bulk:tocount")
    kb.button(text=t("h.bulk.cancel_btn"), callback_data="bulk:cancel")
    kb.adjust(3, 2, 1, 1)
    return kb.as_markup()


def _bulk_quota_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for n in (10, 50, 100):
        kb.button(text=str(n), callback_data=f"bulk:quota:{n}")
    kb.button(text=t("h.bulk.wiz.btn_noquota"), callback_data="bulk:quota:0")
    kb.button(text=t("h.bulk.wiz.btn_custom"), callback_data="bulk:quota:custom")
    kb.button(text=t("h.bulk.wiz.btn_back"), callback_data="bulk:todays")
    kb.button(text=t("h.bulk.cancel_btn"), callback_data="bulk:cancel")
    kb.adjust(3, 2, 1, 1)
    return kb.as_markup()


def _bulk_summary_lines(data: dict) -> list[str]:
    tpl, count = data["tpl"], data["count"]
    names = _bulk_names(tpl, count)
    names_s = ", ".join(names[:8]) + (t("h.common.more", n=count - 8) if count > 8 else "")
    if data.get("date"):
        exp_line = t("h.bulk.wiz.pv_exp_date", d=data["date"])
    elif data.get("days"):
        d = (datetime.now(timezone.utc) + timedelta(days=data["days"])).strftime("%Y-%m-%d")
        exp_line = t("h.bulk.wiz.pv_exp_days", days=data["days"], d=d)
    else:
        exp_line = t("h.bulk.wiz.pv_exp_none")
    quota_line = (
        t("h.bulk.wiz.pv_quota", n=data["quota_gb"])
        if data.get("quota_gb") else t("h.bulk.wiz.pv_quota_none")
    )
    web_line = t("h.bulk.wiz.pv_web_on" if data.get("web", True) else "h.bulk.wiz.pv_web_off")
    return [
        t("h.bulk.wiz.pv_title"), "",
        t("h.bulk.wiz.pv_names", names=names_s),
        exp_line, quota_line, web_line,
    ]


def _bulk_preview_kb(data: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t("h.bulk.wiz.btn_create", n=data["count"]), callback_data="bulk:go")
    kb.button(
        text=t("h.bulk.wiz.pv_web_on" if data.get("web", True) else "h.bulk.wiz.pv_web_off"),
        callback_data="bulk:web",
    )
    kb.button(text=t("h.bulk.wiz.btn_back"), callback_data="bulk:tocount")
    kb.button(text=t("h.bulk.cancel_btn"), callback_data="bulk:cancel")
    kb.adjust(1)
    return kb.as_markup()


async def _bulk_show_preview(cq: CallbackQuery, state: FSMContext):
    data = (await state.get_data())["bulk"]
    await state.set_state(BulkCreateFSM.confirm)
    await _safe_edit(cq, "\n".join(_bulk_summary_lines(data)), reply_markup=_bulk_preview_kb(data))


@router.callback_query(F.data.startswith("bulk:"))
async def cb_bulk(cq: CallbackQuery, state: FSMContext, config: Config):
    parts = cq.data.split(":")
    action, arg = parts[1], parts[2] if len(parts) > 2 else ""
    data = (await state.get_data()).get("bulk")
    if action == "cancel":
        await cq.answer()
        await state.clear()
        await _safe_edit(cq, t("h.bulk.cancelled"))
        return
    if not data:
        await cq.answer(t("h.bulk.wiz.lost"), show_alert=True)
        return
    await cq.answer()
    if action == "count":
        if arg == "0":
            await state.set_state(BulkCreateFSM.waiting_count)
            await _safe_edit(cq, t("h.bulk.wiz.count_prompt"))
        else:
            data["count"] = int(arg)
            await state.update_data(bulk=data)
            await state.set_state(BulkCreateFSM.waiting_days)
            await _safe_edit(cq, t("h.bulk.wiz.t3"), reply_markup=_bulk_days_kb())
    elif action == "tocount":
        await state.set_state(BulkCreateFSM.waiting_count)
        await _safe_edit(cq, t("h.bulk.wiz.count_prompt"))
    elif action == "days":
        if arg == "date":
            await state.set_state(BulkCreateFSM.waiting_days)
            await _safe_edit(cq, t("h.bulk.wiz.days_prompt"))
        else:
            data["days"] = int(arg)
            data["date"] = ""
            await state.update_data(bulk=data)
            await state.set_state(BulkCreateFSM.waiting_quota)
            await _safe_edit(cq, t("h.bulk.wiz.t4"), reply_markup=_bulk_quota_kb())
    elif action == "todays":
        await state.set_state(BulkCreateFSM.waiting_days)
        await _safe_edit(cq, t("h.bulk.wiz.days_prompt"))
    elif action == "quota":
        if arg == "custom":
            await state.set_state(BulkCreateFSM.waiting_quota)
            await _safe_edit(cq, t("h.bulk.wiz.quota_prompt"))
        else:
            data["quota_gb"] = int(arg)
            await state.update_data(bulk=data)
            await _bulk_show_preview(cq, state)
    elif action == "web":
        data["web"] = not data.get("web", True)
        await state.update_data(bulk=data)
        await _bulk_show_preview(cq, state)
    elif action == "again":
        await _bulk_show_preview(cq, state)
    elif action == "go":
        await _bulk_run(cq, state, config)


@router.message(BulkCreateFSM.waiting_count, F.text)
async def fsm_bulk_count(message: Message, state: FSMContext):
    if (message.text or "").startswith("/"):
        await state.clear()
        await message.answer(t("h.bulk.cancelled"))
        return
    txt = (message.text or "").strip()
    if not txt.isdigit() or not 1 <= int(txt) <= BULK_MAX_COUNT:
        await message.answer(t("h.bulk.count_range", n=BULK_MAX_COUNT))
        return
    data = (await state.get_data())["bulk"]
    data["count"] = int(txt)
    await state.update_data(bulk=data)
    await state.set_state(BulkCreateFSM.waiting_days)
    await message.answer(t("h.bulk.wiz.t3"), reply_markup=_bulk_days_kb())


@router.message(BulkCreateFSM.waiting_days, F.text)
async def fsm_bulk_days(message: Message, state: FSMContext):
    if (message.text or "").startswith("/"):
        await state.clear()
        await message.answer(t("h.bulk.cancelled"))
        return
    txt = (message.text or "").strip()
    data = (await state.get_data())["bulk"]
    if txt.isdigit():
        data["days"], data["date"] = min(int(txt), 3650), ""
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", txt):
        data["days"], data["date"] = 0, txt + "T00:00:00Z"
    else:
        await message.answer(t("h.create.step4_err"))
        return
    await state.update_data(bulk=data)
    await state.set_state(BulkCreateFSM.waiting_quota)
    await message.answer(t("h.bulk.wiz.t4"), reply_markup=_bulk_quota_kb())


@router.message(BulkCreateFSM.waiting_quota, F.text)
async def fsm_bulk_quota(message: Message, state: FSMContext):
    if (message.text or "").startswith("/"):
        await state.clear()
        await message.answer(t("h.bulk.cancelled"))
        return
    txt = (message.text or "").strip()
    if not txt.isdigit() or int(txt) > 1024:
        await message.answer(t("h.bulk.quota_range"))
        return
    data = (await state.get_data())["bulk"]
    data["quota_gb"] = int(txt)
    await state.update_data(bulk=data)
    await state.set_state(BulkCreateFSM.confirm)
    await message.answer(
        "\n".join(_bulk_summary_lines(data)),
        reply_markup=_bulk_preview_kb(data),
    )


async def _bulk_run(cq: CallbackQuery, state: FSMContext, config: Config):
    data = (await state.get_data()).get("bulk")
    if not data:
        await _safe_edit(cq, t("h.bulk.wiz.lost"))
        return
    names = _bulk_names(data["tpl"], data["count"])
    days, date_str, quota_gb = data.get("days") or 0, data.get("date"), data.get("quota_gb") or 0

    client, srv = await get_client(_uid(cq), config)
    members = config.get_group_members(srv)

    # Предзагрузка существующих: лишние 409 не шлём
    try:
        existing = {u["username"] for u in await client.get_users()}
    except Exception:
        existing = set()

    await _safe_edit(cq, t("h.bulk.creating", n=len(names)))

    created: list[str] = []
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []
    created_users: dict[str, dict] = {}

    for name in names:
        if name in existing:
            skipped.append(name)
            continue
        payload: dict = {"username": name}
        if date_str:
            payload["expiration_rfc3339"] = date_str
        elif days:
            payload["expiration_rfc3339"] = (
                datetime.now(timezone.utc) + timedelta(days=days)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
        if quota_gb:
            payload["data_quota_bytes"] = quota_gb * (1 << 30)

        results = await cluster_write(members, "create_user", payload)
        ok_results = [r for r in results if r.ok]
        if ok_results:
            created.append(name)
            user = ok_results[0].data
            created_users[name] = user.get("user", user)
        else:
            err = next((r for r in results if not r.ok), None)
            failed.append((name, err.error if err else "unknown"))

    # WEB-профили: один PATCH на всю пачку (vhosts — массив, заменяется целиком)
    web_warn = ""
    if created and data.get("web", True):
        try:
            cfg = await client.get_config()
            vhosts = (cfg.get("web") or {}).get("vhosts") or []
            if vhosts:
                vhost = dict(vhosts[0])
                profiles = vhost.get("profiles") or []
                have = {p.get("user") for p in profiles}
                for name in created:
                    if name not in have:
                        profiles.append({
                            "user": name,
                            "secret_mode": "dd",
                            "max_sessions": 8,
                            "max_streams": 512,
                            "max_streams_per_session": 64,
                        })
                vhost["profiles"] = profiles
                await client.patch_config(
                    {"web": {"vhosts": [vhost]}},
                    if_match=cfg.get("revision", ""),
                    reload="instant",
                )
        except Exception as e:
            web_warn = t("h.bulk.web_failed", err=e)

    lines = [t("h.bulk.done_title")]
    if created:
        lines.append(t("h.bulk.created_n", n=len(created)))
    if skipped:
        lines.append(t("h.bulk.skipped", names=", ".join(skipped[:10]))
                     + (t("h.common.more", n=len(skipped) - 10) if len(skipped) > 10 else ""))
    for name, err in failed[:10]:
        lines.append(f"❌ {name}: {err}")
    if len(failed) > 10:
        lines.append(t("h.bulk.more_errors", n=len(failed) - 10))
    if date_str:
        lines.append(t("h.bulk.wiz.pv_exp_date", d=date_str[:10]))
    elif days:
        lines.append(t("h.bulk.days_n", n=days))
    if quota_gb:
        lines.append(t("h.bulk.quota_n", n=quota_gb))
    lines.append(web_warn)

    kb = InlineKeyboardBuilder()
    for name in created[:8]:
        kb.button(text=f"🔗 {name}", callback_data=f"user:links:{name}")
    if len(created) > 8:
        lines.append(t("h.bulk.links_hint"))
    kb.button(text=t("h.bulk.wiz.btn_again"), callback_data="bulk:again")
    kb.button(text=t("h.bulk.to_users"), callback_data="menu:users")
    kb.adjust(2)
    await state.set_state(None)

    await _safe_edit(cq, "\n".join(l for l in lines if l), reply_markup=kb.as_markup())


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

    if not expired:
        await cq.answer(t("h.expiring.all_fine"))
        return

    try:
        for node in members:
            await _strip_web_profiles(TelemetClient(node.url, node.auth_header), set(expired))
    except Exception as e:
        logger.warning("Failed to remove WEB profiles for expired users: %s", e)
        await cq.answer(t("h.strip_profiles_failed", err=e)[:200], show_alert=True)
        return

    deleted = errors = 0
    for username in expired:
        results = await cluster_write(members, "delete_user", username)
        if _all_ok(results):
            deleted += 1
        else:
            errors += 1

    await cq.answer(t("h.expiring.deleted_n", ok=deleted, err=errors))
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
            await cq.answer(t("h.user.not_found"), show_alert=True)
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
    is_enabled = user.get("enabled", None)
    kb = user_detail_kb(username, enabled=is_enabled)
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
    results = await cluster_write(members, "rotate_secret", username, new_secret)
    ok_results = [r for r in results if r.ok]
    if not ok_results:
        await cq.answer(t("h.rotate.failed"), show_alert=True)
        return
    payload = ok_results[0].data if isinstance(ok_results[0].data, dict) else {}
    user = payload.get("user", payload)
    new_secret = payload.get("secret", new_secret)
    status = ""
    if not _all_ok(results):
        status = "\n⚠️ " + _format_cluster_result([r for r in results if not r.ok])
    await cq.answer(t("h.rotate.ok"))
    await cq.message.answer(
        t("h.rotate.title", user=username, status=status)
        + "\n\n"
        + f"<code>{new_secret}</code>\n\n"
        + t("h.rotate.save_hint"),
    )
    await _safe_edit(cq, format_user_detail(user), reply_markup=user_detail_kb(username, enabled=user.get("enabled", None)))


# ─── Toggle user enabled/disabled (3.4.14+) ───────────────────────────────────

@router.callback_query(F.data.startswith("user:toggle:"))
async def cb_user_toggle(cq: CallbackQuery, config: Config):
    parts    = cq.data.split(":")
    if len(parts) < 4:
        await cq.answer(t("h.toggle.bad_format"), show_alert=True)
        return
    username = parts[2]
    action   = parts[3]   # "enable" или "disable"
    if action not in ("enable", "disable"):
        await cq.answer(t("h.toggle.bad_action"), show_alert=True)
        return

    client, srv = await get_client(_uid(cq), config)
    members     = config.get_group_members(srv)

    method_name = "enable_user" if action == "enable" else "disable_user"
    results     = await cluster_write(members, method_name, username)
    ok_results  = [r for r in results if r.ok]

    if not ok_results:
        await cq.answer(t("h.toggle.failed"), show_alert=True)
        return

    user        = ok_results[0].data
    status_text = t("h.toggle.on") if action == "enable" else t("h.toggle.off")
    await cq.answer(f"{status_text}: {username}")

    if not _all_ok(results):
        await cq.message.answer(
            t("h.common.partial_result") + "\n" + _format_cluster_result([r for r in results if not r.ok])
        )

    await _safe_edit(
        cq,
        format_user_detail(user),
        reply_markup=user_detail_kb(username, enabled=user.get("enabled", None)),
    )


# ─── Reset quota (3.4.11+) ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user:reset_quota:"))
async def cb_user_reset_quota(cq: CallbackQuery, config: Config):
    username = cq.data.split(":")[2]
    client, srv = await get_client(_uid(cq), config)
    members = config.get_group_members(srv)

    try:
        results = await cluster_write(members, "reset_user_quota", username)
    except Exception as e:
        await cq.answer(t("h.common.err", err=e), show_alert=True)
        return

    if _all_ok(results):
        await cq.answer(t("h.quota.reset_ok"))
    else:
        errors = _format_cluster_result([r for r in results if not r.ok])
        await cq.answer(t("h.common.nodes_err", errors=errors), show_alert=True)
        return

    try:
        user = await cluster_read(members, "get_user", username)
        await _safe_edit(
            cq,
            t("h.quota.reset_title", user=username) + "\n\n" + format_user_detail(user),
            reply_markup=user_detail_kb(username, enabled=user.get("enabled", None)),
        )
    except Exception:
        await _safe_edit(cq, t("h.quota.reset_title", user=username))


# ─── Traffic history ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user:traffic:"))
async def cb_user_traffic(cq: CallbackQuery):
    username = cq.data.split(":", 2)[2]
    await _safe_edit(
        cq,
        t("h.traffic.menu", user=username),
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
            t("h.traffic.few_title", user=username, days=days)
            + "\n\n"
            + t("h.traffic.few_points", n=len(rows))
            + "\n"
            + t("h.traffic.collect_hint")
        )
    else:
        lines = [
            t("h.traffic.title", user=username, days=days),
            t("h.traffic.period_row", total=fmt_bytes(delta_info['delta_bytes']), points=delta_info['points']),
            "",
            t("h.chart.recent_snapshots"),
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
    await cq.answer(t("h.chart.building"))

    rows = await db.get_traffic_history(srv.name, username, days)
    if len(rows) < 2:
        await cq.answer(t("h.chart.not_enough"), show_alert=True)
        return

    buf = await asyncio.get_running_loop().run_in_executor(
        None, charts.render_user_traffic, rows, username, days, srv.name
    )
    if buf is None:
        await cq.answer(t("h.chart.no_mpl"), show_alert=True)
        return

    caption = t("h.traffic.chart_caption", user=username, days=days, srv=srv.name)
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
    await cq.answer(t("h.chart.building"))

    deltas = await db.get_all_users_traffic_delta(srv.name, days=days)
    if not deltas:
        await cq.answer(t("h.chart.no_data"), show_alert=True)
        return

    buf = await asyncio.get_running_loop().run_in_executor(
        None, charts.render_traffic_report, deltas, days, srv.name
    )
    if buf is None:
        await cq.answer(t("h.chart.no_mpl"), show_alert=True)
        return

    media = InputMediaPhoto(
        media=BufferedInputFile(buf.read(), filename=f"report_{srv.name}_{days}d.png"),
        caption=t("h.traffic.top_caption", days=days, srv=srv.name),
    )
    # Если сообщение уже фото — редактируем его (не плодим новые)
    if cq.message.photo:
        try:
            await cq.message.edit_media(media=media, reply_markup=traffic_report_kb(chart_mode=True))
        except TelegramBadRequest:
            await cq.answer()  # контент не изменился — просто убираем часики
    else:
        try:
            await cq.message.delete()
        except Exception:
            pass
        await cq.message.answer_photo(
            BufferedInputFile(buf.getvalue(), filename=f"report_{srv.name}_{days}d.png"),
            caption=f"📈 Топ клиентов — {days} дн. • {srv.name}",
            reply_markup=traffic_report_kb(chart_mode=True),
        )


# ─── Links ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user:links:"))
async def cb_user_links(cq: CallbackQuery, config: Config):
    username = cq.data.split(":", 2)[2]
    client, _ = await get_client(_uid(cq), config)
    user = await _api_call(cq, client.get_user, username)
    if user is None:
        return
    all_links = _get_all_links(user)
    if not all_links:
        await _safe_edit(cq, t("h.links.title", user=username) + "\n\n" + t("fmt.common.no_links"),
                         reply_markup=user_links_kb(username))
        return
    # Получаем WEB-конфиг и версию Telemt
    web_config = None
    telemt_version = ""
    try:
        cfg = await client.get_config()
        web_config = cfg.get("web", {})
        info = await client.get_system_info()
        telemt_version = info.get("version", "")
    except Exception:
        pass
    text, _ = format_user_links(user, web_config, telemt_version)
    await _safe_edit(
        cq, text,
        reply_markup=user_links_kb(username),
        link_preview=_NO_LINK_PREVIEW,
    )


# ─── Delete ───────────────────────────────────────────────────────────────────

async def _strip_web_profiles(client: TelemetClient, usernames: set[str]) -> None:
    """Снимает WEB-профили до DELETE /users.

    Пока профиль ссылается на пользователя, telemt отклоняет удаление.
    reload=instant здесь не вызывается: такой reload держит слот ~15с и
    отвечает reload_in_progress, из-за чего профиль остаётся на месте.
    """
    last_error: Exception | None = None
    for _ in range(3):
        cfg = await client.get_config()
        vhosts = (cfg.get("web") or {}).get("vhosts") or []
        if not vhosts:
            return
        changed = False
        new_vhosts = []
        for vhost in vhosts:
            vhost = dict(vhost)
            profiles = vhost.get("profiles") or []
            kept = [p for p in profiles if p.get("user") not in usernames]
            if len(kept) != len(profiles):
                changed = True
                vhost["profiles"] = kept
            new_vhosts.append(vhost)
        if not changed:
            return
        try:
            await client.patch_config(
                {"web": {"vhosts": new_vhosts}},
                if_match=cfg.get("revision", ""),
            )
            return
        except ApiError as e:
            last_error = e
            if e.code in {"revision_conflict", "reload_in_progress"}:
                await asyncio.sleep(0.4)
                continue
            raise
    if last_error:
        raise last_error


@router.callback_query(F.data.startswith("user:delete_confirm:"))
async def cb_user_delete_confirm(cq: CallbackQuery):
    username = cq.data.split(":", 2)[2]
    await _safe_edit(cq, t("h.user.delete_confirm", user=username),
                     reply_markup=user_delete_confirm_kb(username))


@router.callback_query(F.data.startswith("user:delete:"))
async def cb_user_delete(cq: CallbackQuery, config: Config):
    username = cq.data.split(":", 2)[2]
    _, srv = await get_client(_uid(cq), config)
    members = config.get_group_members(srv)

    try:
        for node in members:
            await _strip_web_profiles(TelemetClient(node.url, node.auth_header), {username})
    except Exception as e:
        logger.warning("Failed to remove WEB profile for %s: %s", username, e)
        await cq.answer(t("h.strip_profile_failed", err=e)[:200], show_alert=True)
        return

    results = await cluster_write(members, "delete_user", username)

    if _all_ok(results):
        await cq.answer(t("h.user.deleted", user=username))
    else:
        status = _format_cluster_result(results)
        await cq.answer((t("h.user.partial_delete") + "\n" + status)[:200], show_alert=True)
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
        await message.answer(t("h.adduser.bad_name"))
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

    # Автоматически добавляем пользователя в WEB-профили
    try:
        cfg = await client.get_config()
        web = cfg.get("web", {})
        vhosts = web.get("vhosts", [])
        if vhosts:
            vhost = dict(vhosts[0])
            existing_profiles = vhost.get("profiles", [])
            has_profile = any(p.get("user") == username for p in existing_profiles)
            if not has_profile:
                new_profiles = existing_profiles + [{
                    "user": username,
                    "secret_mode": "dd",
                    "max_sessions": 8,
                    "max_streams": 512,
                    "max_streams_per_session": 64,
                }]
                vhost["profiles"] = new_profiles
                patch = {"web": {"vhosts": [vhost]}}
                revision = cfg.get("revision", "")
                await client.patch_config(patch, if_match=revision, reload="instant")
    except Exception as e:
        logger.warning("Failed to add WEB profile for %s: %s", username, e)

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
    await message.answer(msg, reply_markup=user_detail_kb(username, enabled=user.get("enabled", None)))


# ─── /find — поиск клиента ────────────────────────────────────────────────────

@router.message(Command("find"))
async def cmd_find(message: Message, state: FSMContext, config: Config):
    """Поиск клиента: /find vasya  или  /find (запрашивает имя)."""
    parts = message.text.split(maxsplit=1)
    if len(parts) >= 2:
        await _do_search(message, parts[1].strip(), config)
    else:
        await state.set_state(SearchUserFSM.waiting_query)
        await message.answer(t("h.search.prompt"))


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
        await message.answer(t("h.find.empty"))
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
            reply_markup=user_detail_kb(u["username"], enabled=u.get("enabled", None)),
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
    if await _lite_blocked(message, config):
        return
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
        await message.answer(t("h.create.step1_err"))
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
        await message.answer(t("h.create.step2_err"))
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
        await message.answer(t("h.create.step3_err"))
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
            await message.answer(t("h.create.step4_err"))
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
        await message.answer(t("h.create.step5_err"))
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
        await message.answer(t("h.create.step3_err"))
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
        await message.answer(t("h.create.confirmed_cancel"))
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

    # Автоматически добавляем пользователя в WEB-профили
    try:
        cfg = await client.get_config()
        web = cfg.get("web", {})
        vhosts = web.get("vhosts", [])
        if vhosts:
            # Проверяем, есть ли уже профиль для этого пользователя
            vhost = dict(vhosts[0])
            existing_profiles = vhost.get("profiles", [])
            has_profile = any(p.get("user") == pl["username"] for p in existing_profiles)
            if not has_profile:
                # Добавляем профиль
                new_profiles = existing_profiles + [{
                    "user": pl["username"],
                    "secret_mode": "dd",
                    "max_sessions": 8,
                    "max_streams": 512,
                    "max_streams_per_session": 64,
                }]
                vhost["profiles"] = new_profiles
                patch = {"web": {"vhosts": [vhost]}}
                revision = cfg.get("revision", "")
                await client.patch_config(patch, if_match=revision, reload="instant")
    except Exception as e:
        logger.warning("Failed to add WEB profile for %s: %s", pl["username"], e)

    status_text = "\n\n<b>Статус по узлам:</b>\n" + _format_cluster_result(results) if len(members) > 1 else ""
    if fail_results:
        status_text += "\n\n⚠️ <b>Не синхронизировано:</b>\n" + _format_cluster_result(fail_results)

    await message.answer(
        f"✅ <b>{pl['username']}</b> создан!{status_text}\n\n"
        f"🔑 Секрет: <code>{secret}</code>\n\n"
        + format_user_detail(user),
        reply_markup=user_detail_kb(pl["username"], enabled=user.get("enabled", None)),
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
        await message.answer(t("h.edit.no_change"))
        return
    value = txt
    if field in ("max_tcp_conns", "data_quota_bytes", "max_unique_ips"):
        if not txt.isdigit():
            await message.answer(t("h.edit.not_int"))
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
                t("h.edit.bad_rate")
                + t("h.edit.rate_zero_hint")
            )
            return
    elif field == "secret":
        if not re.match(r"^[0-9a-fA-F]{32}$", txt):
            await message.answer(t("h.edit.bad_secret"))
            return
    elif field == "expiration_rfc3339" and txt.isdigit():
        value = (datetime.now(timezone.utc) + timedelta(days=int(txt))).strftime("%Y-%m-%dT%H:%M:%SZ")

    client, srv = await get_client(_uid(message), config)
    members = config.get_group_members(srv)
    if field == "secret":
        results = await cluster_write(members, "rotate_secret", username, value)
    else:
        results = await cluster_write(members, "patch_user", username, {field: value})

    ok_results = [r for r in results if r.ok]
    if not ok_results:
        errors = _format_cluster_result(results)
        await message.answer(f"❌ Не удалось обновить:\n{errors}")
        return

    payload = ok_results[0].data if isinstance(ok_results[0].data, dict) else {}
    user = payload.get("user", payload) if field == "secret" else payload
    label = FIELD_LABELS.get(field, (field,))[0]
    status = ""
    if not _all_ok(results):
        status = "\n⚠️ " + _format_cluster_result([r for r in results if not r.ok])
    await message.answer(
        f"✅ {label} обновлён{status}\n\n" + format_user_detail(user),
        reply_markup=user_detail_kb(username, enabled=user.get("enabled", None)),
    )


# ─── Runtime ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:runtime")
async def cb_runtime_menu(cq: CallbackQuery):
    await _safe_edit(cq, t("h.runtime.title"), reply_markup=runtime_kb())


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


@router.callback_query(F.data == "runtime:ready")
async def cb_runtime_ready(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_health_ready", format_health_ready, runtime_sub_kb("ready"))


@router.callback_query(F.data == "runtime:me_pool")
async def cb_runtime_me_pool(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_runtime_me_pool_state", format_me_pool, runtime_sub_kb("me_pool"))


@router.callback_query(F.data == "runtime:me_selftest")
async def cb_runtime_me_selftest(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_runtime_me_selftest", format_me_selftest, runtime_sub_kb("me_selftest"))


@router.callback_query(F.data == "runtime:nat_stun")
async def cb_runtime_nat_stun(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_runtime_nat_stun", format_nat_stun, runtime_sub_kb("nat_stun"))


@router.callback_query(F.data == "runtime:zero")
async def cb_runtime_zero(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_stats_zero_all", format_zero_all, runtime_sub_kb("zero"))


@router.callback_query(F.data == "runtime:minimal")
async def cb_runtime_minimal(cq: CallbackQuery, config: Config):
    await _cluster_section(cq, config, "get_stats_minimal_all", format_minimal_all, runtime_sub_kb("minimal"))


@router.callback_query(F.data == "runtime:tls_fingerprints")
async def cb_runtime_tls_fingerprints(cq: CallbackQuery, config: Config):
    """TLS JA3/JA4 fingerprints (3.4.14+). Требует general.beobachten = true."""
    await _cluster_section(
        cq, config,
        "get_runtime_tls_fingerprints",
        format_tls_fingerprints,
        runtime_sub_kb("tls_fingerprints"),
    )




# ─── Security ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:security")
async def cb_security_menu(cq: CallbackQuery):
    await _safe_edit(cq, t("h.security.title"), reply_markup=security_kb())


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
    kb.button(text=t("h.common.menu"), callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "menu:proxy_check")
async def cb_proxy_check_menu(cq: CallbackQuery, state: FSMContext, config: Config):
    if config.lite_mode:
        await cq.answer(t("h.common.lite"), show_alert=True)
        return
    await state.set_state(ProxyCheckFSM.waiting_url)
    await cq.answer()
    await cq.message.answer(
        t("h.check.menu_title")
        + "\n"
        + t("h.check.prompt")
        + "\n<code>tg://proxy?server=HOST&port=443&secret=SECRET</code>\n\n"
        + t("h.check.methods"),
        reply_markup=_proxy_prompt_kb(),
    )


@router.callback_query(F.data == "proxy:check_again")
async def cb_proxy_check_again(cq: CallbackQuery, state: FSMContext, config: Config):
    if config.lite_mode:
        await cq.answer(t("h.common.lite"), show_alert=True)
        return
    await state.set_state(ProxyCheckFSM.waiting_url)
    await cq.answer()
    await cq.message.answer(
        t("h.check.prompt2"),
        reply_markup=_proxy_prompt_kb(),
    )


@router.message(ProxyCheckFSM.waiting_url, F.text.regexp(r"^[^/]"))
async def fsm_proxy_check_url(message: Message, state: FSMContext, config: Config):
    await state.clear()
    if await _lite_blocked(message, config):
        return
    url = message.text.strip()

    if not (url.startswith("tg://") or "t.me/proxy" in url):
        await state.set_state(ProxyCheckFSM.waiting_url)
        await message.answer(
            t("h.check.unrecognized")
            + "\n"
            + t("h.check.expected_format")
            + "\n<code>tg://proxy?server=HOST&port=443&secret=SECRET</code>",
            reply_markup=_proxy_prompt_kb(),
        )
        return

    info = pc.parse_proxy_url(url)
    if info is None:
        await state.set_state(ProxyCheckFSM.waiting_url)
        await message.answer(
            t("h.check.bad_link2"),
            reply_markup=_proxy_prompt_kb(),
        )
        return

    wait_msg = await message.answer(t("h.check.checking"))
    info = await pc.check_node_full(
        info, timeout=5.0,
        agents=config.agents if config.agents else None,
    )

    try:
        await wait_msg.delete()
    except Exception:
        pass

    await message.answer(
        pc.format_node_result(info),
        reply_markup=proxy_check_kb(),
    )


# ─── /check — расширенная диагностика узла ────────────────────────────────────

@router.message(Command("check"))
async def cmd_check(message: Message, state: FSMContext, config: Config):
    """/check tg://proxy?... — полная диагностика узла"""
    if await _lite_blocked(message, config):
        return
    text = message.text.replace("/check", "", 1).strip()
    if text:
        await _do_node_check(message, state, text)
    else:
        await state.set_state(NodeCheckFSM.waiting_url)
        await message.answer(
            t("h.node.title")
            + "\n"
            + t("h.check.prompt")
            + "\n<code>/check tg://proxy?server=HOST&port=443&secret=SECRET</code>",
            reply_markup=_proxy_prompt_kb(),
        )


@router.message(NodeCheckFSM.waiting_url, F.text.regexp(r"^[^/]"))
async def fsm_node_check_url(message: Message, state: FSMContext, config: Config):
    await state.clear()
    if await _lite_blocked(message, config):
        return
    url = message.text.strip()
    if url.startswith("/check"):
        url = url.replace("/check", "", 1).strip()
    await _do_node_check(message, state, url)


async def _do_node_check(message: Message, state: FSMContext, url: str):
    info = pc.parse_proxy_url(url)
    if info is None:
        await state.set_state(NodeCheckFSM.waiting_url)
        await message.answer(
            "❌ Не удалось распознать ссылку.\n\n"
            "Ожидается формат:\n"
            "<code>/check tg://proxy?server=HOST&port=443&secret=SECRET</code>",
            reply_markup=_proxy_prompt_kb(),
        )
        return

    wait_msg = await message.answer(t("h.check.checking"))

    # Получаем агенты из конфига (нужен uid → config)
    config = None
    try:
        # Пытаемся получить конфиг через state или диспетчер
        # Импортируем конфиг напрямую
        from config import load_config
        config = load_config()
    except Exception:
        pass

    agents = config.agents if config else None
    info = await pc.check_node_full(info, timeout=5.0, agents=agents)

    try:
        await wait_msg.delete()
    except Exception:
        pass

    await message.answer(
        format_node_result(info),
        reply_markup=proxy_check_kb(),
    )


# ─── Config edit (PATCH /v1/config) ───────────────────────────────────────────

# Поля доступные для редактирования в каждой секции
CONFIG_FIELDS = {
    "general": [
        "log_level", "beobachten", "use_middle_proxy", "me2dc_fallback", "me2dc_fast",
        "me_keepalive_enabled", "me_keepalive_interval_secs", "me_floor_mode",
        "me_writer_pick_mode", "update_every", "me_reinit_every_secs",
    ],
    "timeouts": [
        "client_handshake", "client_first_byte_idle_secs", "client_keepalive",
        "client_ack", "tg_connect", "me_one_retry", "me_one_timeout_ms",
    ],
    "censorship": [
        "tls_domain", "tls_domains", "mask", "mask_host", "mask_port",
        "tls_emulation", "tls_front_dir", "tls_full_cert_ttl_secs",
        "alpn_enforce", "unknown_sni_action",
    ],
    "upstreams": [],  # Массив — редактируется как целое
    "show_link": [],  # Массив
    "dc_overrides": {},  # Dict
    "web": {},  # Dict — редактируется как целое (vhosts, profiles, timeouts, limits)
}

# Кэш текущего конфига для пользователя
_config_edit_cache: dict[int, dict] = {}


@router.callback_query(F.data == "menu:config_edit")
async def cb_config_edit_menu(cq: CallbackQuery, config: Config):
    """Показать список секций для редактирования."""
    client, srv = await get_client(_uid(cq), config)
    try:
        data = await client.get_config()
    except ApiError as e:
        await _safe_edit(cq, f"❌ Ошибка: {e}")
        return
    except Exception as e:
        logger.exception("cb_config_edit_menu error")
        await _safe_edit(cq, f"❌ Ошибка: {type(e).__name__}: {e}")
        return

    _config_edit_cache[_uid(cq)] = data
    revision = data.get("revision", "")
    header = "<b>⚙️ Редактирование конфига</b>\n"
    if revision:
        header += f"<i>revision: {revision[:12]}…</i>"
    header += "\n\nВыберите секцию:"
    client, _ = await get_client(_uid(cq), config)
    telemt_version = await _get_telemt_version(client)
    await _safe_edit(cq, header, reply_markup=config_edit_sections_kb(telemt_version))


@router.callback_query(F.data == "configedit:menu")
async def cb_config_edit_back(cq: CallbackQuery, config: Config):
    """Вернуться к списку секций."""
    uid = _uid(cq)
    data = _config_edit_cache.get(uid, {})
    revision = data.get("revision", "")
    header = "<b>⚙️ Редактирование конфига</b>\n"
    if revision:
        header += f"<i>revision: {revision[:12]}…</i>"
    header += "\n\nВыберите секцию:"
    client, _ = await get_client(uid, config)
    telemt_version = await _get_telemt_version(client)
    await _safe_edit(cq, header, reply_markup=config_edit_sections_kb(telemt_version))


@router.callback_query(F.data.startswith("configedit:section:"))
async def cb_config_edit_section(cq: CallbackQuery, state: FSMContext, config: Config):
    """Показать поля секции."""
    section = cq.data.split(":")[2]
    uid = _uid(cq)
    data = _config_edit_cache.get(uid, {})
    section_data = data.get(section, {})

    # Для вложенных секций
    if section_data is None and "." in section:
        parent, child = section.rsplit(".", 1)
        parent_data = data.get(parent, {})
        if isinstance(parent_data, dict):
            section_data = parent_data.get(child, {})

    fields = CONFIG_FIELDS.get(section)

    # Для секций-массивов/словарей — показать как целое
    if fields == [] or fields == {}:
        text = f"<b>⚙️ [{section}]</b>\n\n"
        if isinstance(section_data, list):
            text += f"Текущее значение:\n<code>{section_data}</code>\n\n"
            text += "Отправь новое значение (JSON-массив):"
        elif isinstance(section_data, dict):
            text += f"Текущее значение:\n<code>{section_data}</code>\n\n"
            text += "Отправь новое значение (JSON-объект):"
        else:
            text += f"Текущее значение: <code>{section_data}</code>\n\n"
            text += "Отправь новое значение:"
        await state.set_state(ConfigEditFSM.waiting_value)
        await state.update_data(section=section, field="__raw__")
        await _safe_edit(cq, text)
        return

    if not fields:
        await _safe_edit(cq, f"⚙️ [{section}]\n\n❌ Нет полей для редактирования")
        return

    # Показать текущие значения полей
    # Кнопки "+reload" появились в PATCH /v1/config?reload= (Telemt 3.4.25+)
    client, srv = await get_client(uid, config)
    version = await _get_telemt_version(client)
    supports_reload = _version_at_least(version, 3, 4, 25)
    await _safe_edit(
        cq,
        f"<b>⚙️ [{section}]</b>\n\nВыберите поле:",
        reply_markup=config_edit_fields_kb(
            section,
            fields,
            section_data if isinstance(section_data, dict) else {},
            supports_reload=supports_reload,
        ),
    )


@router.callback_query(F.data.startswith("configedit:field:"))
async def cb_config_edit_field(cq: CallbackQuery, state: FSMContext):
    """Запрос нового значения для поля."""
    parts = cq.data.split(":")
    section, field = parts[2], parts[3]

    uid = _uid(cq)
    data = _config_edit_cache.get(uid, {})
    section_data = data.get(section, {})
    if isinstance(section_data, dict):
        current = section_data.get(field, "—")
    else:
        current = "—"

    hints = {
        "log_level": "debug / normal / silent",
        "beobachten": "true / false",
        "use_middle_proxy": "true / false",
        "me2dc_fallback": "true / false",
        "me2dc_fast": "true / false",
        "me_keepalive_enabled": "true / false",
        "tls_domain": "домен или пустая строка",
        "tls_domains": '["domain1.com", "domain2.com"] или []',
        "mask": "true / false",
        "mask_host": "хост или пустая строка",
        "mask_port": "число (например 443)",
        "tls_emulation": "true / false",
        "alpn_enforce": "true / false",
        "unknown_sni_action": "drop / pass",
        "client_handshake": "секунды (например 60)",
        "client_keepalive": "секунды (например 15)",
        "client_ack": "секунды (например 90)",
        "tg_connect": "секунды (например 10)",
    }
    hint = hints.get(field, "значение")

    await state.set_state(ConfigEditFSM.waiting_value)
    await state.update_data(section=section, field=field)
    await _safe_edit(cq, f"✏️ <b>{field}</b>\n\nТекущее: <code>{current}</code>\n<i>{hint}</i>\n\nОтправь новое значение или /skip:")


@router.message(ConfigEditFSM.waiting_value, Command("skip"))
async def fsm_config_edit_skip(message: Message, state: FSMContext, config: Config):
    """/skip — отмена и возврат в меню конфигурации."""
    await state.clear()
    uid = message.from_user.id
    data = _config_edit_cache.get(uid, {})
    revision = data.get("revision", "")
    header = "<b>⚙️ Редактирование конфига</b>\n"
    if revision:
        header += f"<i>revision: {revision[:12]}…</i>"
    header += "\n\nВыберите секцию:"
    client, _ = await get_client(uid, config)
    telemt_version = await _get_telemt_version(client)
    await message.answer(header, reply_markup=config_edit_sections_kb(telemt_version))


@router.message(ConfigEditFSM.waiting_value, F.text.regexp(r"^[^/]"))
async def fsm_config_edit_value(message: Message, state: FSMContext, config: Config):
    """Применить новое значение поля."""
    data = await state.get_data()
    section = data["section"]
    field = data.get("field", "")
    value_str = message.text.strip()
    await state.clear()

    # Парсим значение
    value = _parse_config_value(value_str)

    # Применяем через API
    uid = message.from_user.id
    cache = _config_edit_cache.get(uid, {})
    revision = cache.get("revision", "")

    if field == "__raw__":
        patch = {section: value}
    else:
        patch = {section: {field: value}}

    client, srv = await get_client(uid, config)
    try:
        result = await client.patch_config(patch, if_match=revision)
    except ApiError as e:
        # Повторный ввод при ошибке API
        await state.set_state(ConfigEditFSM.waiting_value)
        await state.update_data(section=section, field=field)
        await message.answer(
            f"❌ <b>Ошибка:</b> {e}\n\n"
            f"Попробуй ещё раз или /skip для отмены:"
        )
        return
    except Exception as e:
        await state.set_state(ConfigEditFSM.waiting_value)
        await state.update_data(section=section, field=field)
        await message.answer(
            f"❌ <b>Ошибка:</b> {type(e).__name__}: {e}\n\n"
            f"Попробуй ещё раз или /skip для отмены:"
        )
        return

    new_rev = result.get("revision", "")
    restart = result.get("restart_required", False)
    changed = result.get("changed", [])

    text = "✅ Конфиг обновлён\n"
    if new_rev:
        text += f"revision: <code>{new_rev[:12]}…</code>\n"
    if changed:
        text += f"Изменено: {', '.join(changed)}\n"
    if restart:
        text += "\n⚠️ Требуется перезапуск Telemt!"
    else:
        text += "\n✅ Hot-reload применён"

    await message.answer(text)


def _parse_config_value(s: str):
    """Парсит строку в типизированное значение для JSON."""
    import json
    s = s.strip()

    # Булевы
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False

    # null
    if s.lower() in ("null", "none", "нет"):
        return None

    # JSON (массивы, объекты, строки в кавычках)
    if s.startswith(("[", "{", '"')):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass

    # Число
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        pass

    # Строка
    return s


@router.callback_query(F.data.startswith("configedit:apply:"))
async def cb_config_edit_apply(cq: CallbackQuery, config: Config):
    """Применить все изменения секции, опционально с runtime reload."""
    parts = cq.data.split(":")
    # configedit:apply:{section} или configedit:apply:{mode}:{section}
    if len(parts) == 4:
        reload_mode, section = parts[2], parts[3]
    else:
        reload_mode, section = "", parts[2]

    uid = _uid(cq)
    cache = _config_edit_cache.get(uid, {})
    revision = cache.get("revision", "")
    section_data = cache.get(section, {})

    if not section_data:
        await cq.answer(t("h.cfg.no_data"), show_alert=True)
        return

    # Применяем секцию целиком; reload делаем тем же запросом (единый If-Match)
    client, srv = await get_client(uid, config)
    try:
        result = await client.patch_config(
            {section: section_data}, if_match=revision, reload=reload_mode
        )
    except ApiError as e:
        await cq.answer(f"❌ {e}", show_alert=True)
        return
    except Exception as e:
        await cq.answer(f"❌ {type(e).__name__}: {e}", show_alert=True)
        return

    new_rev = result.get("revision", "")
    runtime_reload = result.get("runtime_reload_required", False)
    # Старый API (3.4.16-3.4.24) отдаёт только легаси-поле restart_required
    process_restart = result.get(
        "process_restart_required", result.get("restart_required", False)
    )
    deferred = result.get("deferred_process_fields") or []
    reload_info = result.get("reload") or {}

    text = f"✅ Секция <b>[{section}]</b> применена\n"
    if new_rev:
        text += f"revision: <code>{new_rev[:12]}…</code>\n"
    if reload_info:
        rid = reload_info.get("reload_id", "?")
        state = reload_info.get("state", "?")
        text += f"\n🔄 Reload <code>{reload_info.get('mode', reload_mode)}</code> принят (ID: <code>{rid}</code>, {state})\n"
        text += f"Проверить: <code>/reload_status {rid}</code>\n"
    elif runtime_reload:
        text += t("h.cfg.need_reload")
    if process_restart:
        text += t("h.cfg.need_restart")
    if deferred:
        text += f"Отложено до перезапуска: <code>{', '.join(deferred)}</code>\n"
    if not runtime_reload and not process_restart and not reload_info:
        text += t("h.cfg.hot_reload")

    needs_reload = bool(runtime_reload) and not reload_info and not config.lite_mode
    await _safe_edit(cq, text, reply_markup=config_edit_after_kb(section, needs_reload))


@router.callback_query(F.data.startswith("configedit:reload:"))
async def cb_config_edit_reload(cq: CallbackQuery, config: Config):
    """Runtime reload после применения секции."""
    if config.lite_mode:
        await cq.answer(t("h.cfg.lite_block"), show_alert=True)
        return

    _, _, mode, section = cq.data.split(":")
    if mode not in ("instant", "drain"):
        await cq.answer(t("h.cfg.bad_mode"), show_alert=True)
        return

    client, srv = await get_client(_uid(cq), config)
    try:
        result = await client.system_reload(mode=mode)
    except ApiError as e:
        await cq.answer(f"❌ {e.message}", show_alert=True)
        return
    except Exception as e:
        await cq.answer(f"❌ {type(e).__name__}: {e}", show_alert=True)
        return

    reload_id = result.get("reload_id", "?")
    state = result.get("state", "?")
    icon = "✅" if state == "accepted" else "⚠️"
    await cq.answer(
        f"{icon} Reload {mode} принят (ID: {reload_id}, {state})",
        show_alert=True,
    )
    text = (
        f"{icon} <b>Runtime reload принят</b>\n\n"
        f"ID: <code>{reload_id}</code>\n"
        f"Режим: <code>{mode}</code>\n"
        f"Статус: <code>{state}</code>\n\n"
        f"Проверить: <code>/reload_status {reload_id}</code>"
    )
    await _safe_edit(cq, text, reply_markup=config_edit_after_kb(section, False))


@router.callback_query(F.data.startswith("configedit:confirm:"))
async def cb_config_edit_confirm(cq: CallbackQuery, state: FSMContext):
    """После применения — вернуться к секции."""
    await cb_config_edit_section(cq, state)


# ─── /reload — runtime reload (3.4.25+) ──────────────────────────────────────

@router.message(Command("reload"))
async def cmd_reload(message: Message, config: Config):
    """/reload [instant|drain] — runtime reload без перезапуска процесса"""
    if await _lite_blocked(message, config):
        return
    args = message.text.replace("/reload", "", 1).strip().split()
    mode = args[0] if args else "instant"

    if mode not in ("instant", "drain"):
        await message.answer(
            t("h.reload.bad_mode")
            + t("h.reload.instant_hint")
            + t("h.reload.drain_hint")
        )
        return

    uid = message.from_user.id
    client, srv = await get_client(uid, config)

    try:
        result = await client.system_reload(mode=mode)
    except ApiError as e:
        await message.answer(f"❌ Ошибка: {e}")
        return
    except Exception as e:
        await message.answer(f"❌ Ошибка: {type(e).__name__}: {e}")
        return

    reload_id = result.get("reload_id", "?")
    state_name = result.get("state", "?")
    target_gen = result.get("target_generation", "?")

    icon = "✅" if state_name == "accepted" else "⚠️"
    await message.answer(
        f"{icon} <b>Runtime reload принят</b>\n\n"
        f"ID: <code>{reload_id}</code>\n"
        f"Режим: <code>{mode}</code>\n"
        f"Целевое поколение: <code>{target_gen}</code>\n"
        f"Статус: <code>{state_name}</code>\n\n"
        f"Проверить статус: <code>/reload_status {reload_id}</code>"
    )


@router.message(Command("reload_status"))
async def cmd_reload_status(message: Message, config: Config):
    """/reload_status <id> — проверить статус reload операции"""
    if await _lite_blocked(message, config):
        return
    args = message.text.replace("/reload_status", "", 1).strip().split()
    if not args or not args[0].isdigit():
        await message.answer(t("h.reload.usage"))
        return

    reload_id = int(args[0])
    uid = message.from_user.id
    client, srv = await get_client(uid, config)

    try:
        result = await client.get_reload_status(reload_id)
    except ApiError as e:
        await message.answer(f"❌ Ошибка: {e}")
        return
    except Exception as e:
        await message.answer(f"❌ Ошибка: {type(e).__name__}: {e}")
        return

    state_name = result.get("state", "?")
    mode = result.get("mode", "?")
    target_gen = result.get("target_generation", "?")

    icons = {
        "accepted": "⏳", "preparing": "🔄", "activating": "🔄",
        "draining": "🔄", "succeeded": "✅", "rolled_back": "↩️", "failed": "❌"
    }
    icon = icons.get(state_name, "❓")

    lines = [
        f"{icon} <b>Reload #{reload_id}</b>",
        f"Режим: <code>{mode}</code>",
        f"Поколение: <code>{target_gen}</code>",
        f"Статус: <code>{state_name}</code>",
    ]

    if result.get("error"):
        lines.append(f"Ошибка: {result['error']}")
    if result.get("warnings"):
        lines.append(f"Предупреждения: {', '.join(result['warnings'])}")
    if result.get("deferred_process_fields"):
        lines.append(f"Отложенные: {', '.join(result['deferred_process_fields'])}")
    if result.get("finished_at_epoch_secs"):
        from tz import fmt_datetime
        lines.append(f"Завершено: {fmt_datetime(result['finished_at_epoch_secs'])}")

    await message.answer("\n".join(lines))


# ─── WEB Proxy ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:web")
async def cb_web_menu(cq: CallbackQuery, config: Config):
    """Показать WEB Proxy статус."""
    client, srv = await get_client(_uid(cq), config)
    try:
        data = await client.get_web_status()
    except ApiError as e:
        await _safe_edit(cq, f"❌ Ошибка: {e}")
        return
    except Exception as e:
        logger.exception("cb_web_menu error")
        await _safe_edit(cq, f"❌ Ошибка: {type(e).__name__}: {e}")
        return

    from formatters import format_web_status
    op_lifecycle = data.get("operator_lifecycle", {})
    op_state = op_lifecycle.get("state", "running")
    await _safe_edit(cq, format_web_status(data), reply_markup=web_menu_kb(op_state))


@router.callback_query(F.data == "web:status")
async def cb_web_status(cq: CallbackQuery, config: Config):
    """Обновить WEB статус."""
    await cb_web_menu(cq, config)


@router.callback_query(F.data == "web:sessions")
async def cb_web_sessions(cq: CallbackQuery, config: Config):
    """Показать список WEB-сессий."""
    client, srv = await get_client(_uid(cq), config)
    try:
        data = await client.get_web_sessions(limit=50)
    except ApiError as e:
        await _safe_edit(cq, f"❌ Ошибка: {e}")
        return
    except Exception as e:
        logger.exception("cb_web_sessions error")
        await _safe_edit(cq, f"❌ Ошибка: {type(e).__name__}: {e}")
        return

    from formatters import format_web_sessions
    sessions = data.get("sessions", [])
    has_next = bool(data.get("next_cursor"))
    await _safe_edit(
        cq,
        format_web_sessions(data),
        reply_markup=web_sessions_kb(sessions, has_next, data.get("next_cursor", "")),
    )


@router.callback_query(F.data.startswith("web:n:"))
async def cb_web_sessions_next(cq: CallbackQuery, config: Config):
    """Пагинация WEB-сессий."""
    cursor = cq.data.split(":", 2)[2]
    client, srv = await get_client(_uid(cq), config)
    try:
        data = await client.get_web_sessions(limit=50, cursor=cursor)
    except ApiError as e:
        await _safe_edit(cq, f"❌ Ошибка: {e}")
        return

    from formatters import format_web_sessions
    sessions = data.get("sessions", [])
    has_next = bool(data.get("next_cursor"))
    await _safe_edit(
        cq,
        format_web_sessions(data),
        reply_markup=web_sessions_kb(sessions, has_next, data.get("next_cursor", "")),
    )


@router.callback_query(F.data.startswith("web:s:"))
async def cb_web_session_detail(cq: CallbackQuery, config: Config):
    """Детали одной WEB-сессии."""
    short_id = cq.data.split(":", 2)[2]
    client, srv = await get_client(_uid(cq), config)

    # Получаем runtime_instance для восстановления полного session_ref
    try:
        status = await client.get_web_status()
        rt = status.get("runtime", {})
        runtime_instance = rt.get("runtime_instance", "")
    except Exception:
        runtime_instance = ""

    # Восстанавливаем полный session_ref
    session_ref = f"ws1.{runtime_instance}.{short_id}" if runtime_instance else short_id

    try:
        data = await client.get_web_session(session_ref)
    except ApiError as e:
        await _safe_edit(cq, f"❌ Ошибка: {e}")
        return
    except Exception as e:
        logger.exception("cb_web_session_detail error")
        await _safe_edit(cq, f"❌ Ошибка: {type(e).__name__}: {e}")
        return

    from formatters import format_web_session_detail
    await _safe_edit(
        cq,
        format_web_session_detail(data),
        reply_markup=web_session_detail_kb(session_ref),
    )


async def _poll_web_operation(
    client, op_id: str, attempts: int = 6, delay: float = 1.0
) -> dict:
    """Поллит статус WEB-операции до терминального состояния или таймаута."""
    last: dict = {}
    for i in range(attempts):
        try:
            last = await client.get_web_operation(op_id)
        except ApiError as e:
            return {"state": "poll_error", "error": str(e)}
        except Exception as e:
            return {"state": "poll_error", "error": f"{type(e).__name__}: {e}"}
        if last.get("state") not in ("queued", "running", None):
            return last
        if i < attempts - 1:
            await asyncio.sleep(delay)
    return last


def _op_counters(op: dict) -> str:
    """Счётчики WEB-операции. Имена полей подстраиваемся под оба варианта API."""
    parts = []
    for key in ("requested", "matched", "signalled", "conflicted", "scanned"):
        val = op.get(key, op.get(f"{key}_total"))
        if val is not None:
            parts.append(f"{key}: {val}")
    return ", ".join(parts)


@router.callback_query(F.data.startswith("web:c:"))
async def cb_web_close_session(cq: CallbackQuery, config: Config):
    """Закрыть WEB-сессию."""
    short_id = cq.data.split(":", 2)[2]
    client, srv = await get_client(_uid(cq), config)

    # Получаем runtime_instance для восстановления полного session_ref
    try:
        status = await client.get_web_status()
        rt = status.get("runtime", {})
        runtime_instance = rt.get("runtime_instance", "")
    except Exception:
        runtime_instance = ""

    if not runtime_instance:
        await cq.answer(t("h.web.runtime_down"), show_alert=True)
        return

    # Восстанавливаем полный session_ref
    session_ref = f"ws1.{runtime_instance}.{short_id}" if runtime_instance else short_id

    try:
        result = await client.close_web_sessions(
            runtime_instance,
            {"kind": "refs", "session_refs": [session_ref]},
        )
    except ApiError as e:
        await cq.answer(f"❌ {e.message}", show_alert=True)
        return

    # Поллим статус операции до терминального состояния
    op_id = result.get("operation_id", "")
    final = await _poll_web_operation(client, op_id) if op_id else {"state": "unknown"}
    state = final.get("state", "?")

    if state == "completed":
        counters = _op_counters(final)
        msg = t("h.web.closed_ok") + (f" ({counters})" if counters else "")
    elif state == "failed":
        reason = final.get("failure") or final.get("failure_token") or t("h.web.op_failed_reason")
        msg = f"❌ Не удалось закрыть: {reason}"
    elif state == "poll_error":
        msg = f"⚠️ Запрос отправлен, но статус не получен: {final.get('error', '')}"
    elif state in ("cancelled",):
        msg = t("h.web.op_cancelled")
    else:
        msg = f"⏳ Операция ещё выполняется (state: {state})"

    await cq.answer(msg, show_alert=True)

    # Возвращаемся к списку сессий
    await cb_web_sessions(cq, config)


@router.callback_query(F.data == "web:debug_clear")
async def cb_web_debug_clear(cq: CallbackQuery, config: Config):
    """Очистить WEB debug-записи."""
    client, srv = await get_client(_uid(cq), config)

    try:
        status = await client.get_web_status()
        rt = status.get("runtime", {})
        runtime_instance = rt.get("runtime_instance", "")
    except Exception:
        runtime_instance = ""

    if not runtime_instance:
        await cq.answer(t("h.web.runtime_down"), show_alert=True)
        return

    try:
        result = await client.clear_web_debug(runtime_instance)
        cleared = result.get("records_cleared", 0)
        await cq.answer(f"✅ Очищено {cleared} записей", show_alert=True)
    except ApiError as e:
        await cq.answer(f"❌ {e.message}", show_alert=True)
        return

    # Обновляем статус
    await cb_web_menu(cq, config)


@router.callback_query(F.data == "web:carrier_reset")
async def cb_web_carrier_reset(cq: CallbackQuery, config: Config):
    """Сбросить WEB carrier learning."""
    client, srv = await get_client(_uid(cq), config)

    try:
        status = await client.get_web_status()
        rt = status.get("runtime", {})
        runtime_instance = rt.get("runtime_instance", "")
    except Exception:
        runtime_instance = ""

    if not runtime_instance:
        await cq.answer(t("h.web.runtime_down"), show_alert=True)
        return

    try:
        result = await client.reset_web_carrier_learning(runtime_instance)
        cleared = result.get("entries_cleared", 0)
        await cq.answer(f"✅ Сброшено {cleared} записей", show_alert=True)
    except ApiError as e:
        await cq.answer(f"❌ {e.message}", show_alert=True)
        return

    # Обновляем статус
    await cb_web_menu(cq, config)


@router.callback_query(F.data == "web:pause")
async def cb_web_pause(cq: CallbackQuery, config: Config):
    """Пауза WEB admission."""
    client, srv = await get_client(_uid(cq), config)
    try:
        status = await client.get_web_status()
        rt = status.get("runtime", {})
        runtime_instance = rt.get("runtime_instance", "")
    except Exception:
        runtime_instance = ""

    if not runtime_instance:
        await cq.answer(t("h.web.runtime_down"), show_alert=True)
        return

    try:
        await client.web_lifecycle_pause(runtime_instance)
        await cq.answer(t("h.web.paused"), show_alert=True)
    except ApiError as e:
        await cq.answer(f"❌ {e.message}", show_alert=True)
        return

    await cb_web_menu(cq, config)


@router.callback_query(F.data == "web:drain")
async def cb_web_drain(cq: CallbackQuery, config: Config):
    """Graceful drain WEB сессий."""
    client, srv = await get_client(_uid(cq), config)
    try:
        status = await client.get_web_status()
        rt = status.get("runtime", {})
        runtime_instance = rt.get("runtime_instance", "")
    except Exception:
        runtime_instance = ""

    if not runtime_instance:
        await cq.answer(t("h.web.runtime_down"), show_alert=True)
        return

    try:
        await client.web_lifecycle_drain(runtime_instance, timeout_secs=30)
        await cq.answer(t("h.web.drain_started"), show_alert=True)
    except ApiError as e:
        await cq.answer(f"❌ {e.message}", show_alert=True)
        return

    await cb_web_menu(cq, config)


@router.callback_query(F.data == "web:resume")
async def cb_web_resume(cq: CallbackQuery, config: Config):
    """Отмена drain, открытие admission."""
    client, srv = await get_client(_uid(cq), config)
    try:
        status = await client.get_web_status()
        rt = status.get("runtime", {})
        runtime_instance = rt.get("runtime_instance", "")
    except Exception:
        runtime_instance = ""

    if not runtime_instance:
        await cq.answer(t("h.web.runtime_down"), show_alert=True)
        return

    try:
        await client.web_lifecycle_resume(runtime_instance)
        await cq.answer(t("h.web.resumed"), show_alert=True)
    except ApiError as e:
        await cq.answer(f"❌ {e.message}", show_alert=True)
        return

    await cb_web_menu(cq, config)


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
@router.message(Command("alerts"))
async def cmd_alerts(message: Message, config: Config):
    if await _lite_blocked(message, config):
        return
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
        "  ⚠ Готовность: admission/upstreams (3.5.11+)\n"
        "  ⚠ Всплеск соединений &gt;50%\n"
        "  ⚠ ME Writers coverage &lt;80%\n"
        "  🏷 Обновление версии\n"
        "  ⚠ Неизвестный SNI\n"
        "  ⚠ Всплеск HS timeout\n"
        "  ⚠ Всплеск плохих TLS клиентов\n"
        "  ⚠ Сброс соединений при handshake\n"
        "  📊 Клиент использовал 80% квоты\n\n"
        "Проверка: каждые 2 мин\n"
        "Трафик: каждые 15 мин\n"
        "Хранение: 30 дней",
        reply_markup=alerts_kb(states),
    )


@router.callback_query(F.data.startswith("alert:toggle:"))
async def cb_alert_toggle(cq: CallbackQuery, config: Config):
    if config.lite_mode:
        await cq.answer(t("h.common.lite"), show_alert=True)
        return
    uid = _uid(cq)
    alert_type = cq.data.split(":")[-1]
    idx = await get_server_index(uid, config)
    srv = config.servers[idx]

    current = await get_alert(uid, srv.name, alert_type)
    new_state = not current
    await set_alert(uid, srv.name, alert_type, threshold=None, enabled=new_state)

    label = t(ALERT_LABELS.get(alert_type, alert_type))
    await cq.answer(
        f"{'✅' if new_state else '☑️'} {label}: "
        f"{t('h.alerts.on') if new_state else t('h.alerts.off')}"
    )

    states = {}
    for atype in ALERT_LABELS:
        states[atype] = await get_alert(uid, srv.name, atype)

    await cq.message.edit_reply_markup(reply_markup=alerts_kb(states))


@router.message(Command("status"))
async def cmd_status(message: Message, config: Config):
    """/status — быстрый статус всех серверов"""
    lines = [t("h.status.title"), ""]
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
    await message.answer("\n\n".join([
        t("h.help.title"),
        t("h.help.commands"),
        t("h.help.menu"),
        t("h.help.reload"),
        t("h.help.card"),
        t("h.help.links"),
        t("h.help.alerts"),
        t("h.help.multi"),
    ]))
