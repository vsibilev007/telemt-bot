"""
Форматтеры ответов API в читаемый текст для Telegram
"""

from __future__ import annotations
import math
from datetime import UTC, datetime


def fmt_bytes(b: int | None) -> str:
    if b is None:
        return "—"
    if b == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(b, 1024)))
    i = min(i, len(units) - 1)
    p = math.pow(1024, i)
    return f"{b / p:.1f} {units[i]}"


def fmt_uptime(seconds: float) -> str:
    s = int(seconds)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts = []
    if d:
        parts.append(f"{d}д")
    if h:
        parts.append(f"{h}ч")
    if m:
        parts.append(f"{m}м")
    parts.append(f"{s}с")
    return " ".join(parts)


def fmt_ts(epoch: int | None) -> str:
    if not epoch:
        return "—"
    dt = datetime.fromtimestamp(epoch, tz=UTC)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def fmt_bool(v: bool) -> str:
    return "✅" if v else "❌"


def fmt_pct(v: float) -> str:
    return f"{v:.1f}%"


def fmt_rtt(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.1f} мс"


def format_dashboard(health, summary, sysinfo, gates, server_name, online_users):
    status = health.get("status", "?")
    status_icon = "🟢" if status == "ok" else "🔴"
    ro = health.get("read_only", False)
    uptime = summary.get("uptime_seconds", 0)
    conns = summary.get("connections_total", 0)
    bad = summary.get("connections_bad_total", 0)
    hs_to = summary.get("handshake_timeouts_total", 0)
    users_count = summary.get("configured_users", 0)
    version = sysinfo.get("version", "?")
    git = sysinfo.get("git_commit", "")
    git_short = git[:7] if git else ""
    arch = sysinfo.get("target_arch", "?")
    os_name = sysinfo.get("target_os", "?")
    startup = gates.get("startup_status", "?")
    startup_icons = {
        "ready": "🟢",
        "initializing": "🟡",
        "pending": "🟠",
        "failed": "🔴",
        "skipped": "⚪",
    }
    st_icon = startup_icons.get(startup, "❓")
    accepting = gates.get("accepting_new_connections", False)
    use_me = gates.get("use_middle_proxy", False)
    me_ready = gates.get("me_runtime_ready", False)
    bad_percent = (bad / conns * 100) if conns else 0
    load_icon = "🟢" if bad_percent < 2 else "🟡" if bad_percent < 5 else "🔴"
    hs_icon = "🟢" if hs_to < 100 else "🟡" if hs_to < 300 else "🔴"
    online_icon = "🟢" if online_users > 0 else "⚪"
    BAD_LABELS = {
        "tls_handshake_bad_client": "Плохой TLS клиент",
        "direct_modes_disabled": "Прямой режим отключён",
        "unknown_tls_sni": "Неизвестный SNI",
        "tls_clienthello_len_out_of_bounds": "Некорректный ClientHello",
    }
    bad_by_class = summary.get("connections_bad_by_class", [])
    bad_lines = []
    for entry in sorted(bad_by_class, key=lambda x: -x.get("total", 0)):
        cls = entry.get("class", "?")
        total = entry.get("total", 0)
        if total == 0:
            continue
        label = BAD_LABELS.get(cls, cls)
        bad_lines.append(f"  • {label}: <b>{total:,}</b>")
    HS_LABELS = {
        "timeout": ("🟡", "Таймаут"),
        "expected_64_got_0_unexpected_eof": ("⚫", "Обрыв соединения"),
        "expected_64_got_0_connection_reset": ("⚫", "Сброс соединения"),
        "other": ("⚫", "Прочее"),
    }
    hs_by_class = summary.get("handshake_failures_by_class", [])
    hs_lines = []
    for entry in sorted(hs_by_class, key=lambda x: -x.get("total", 0)):
        cls = entry.get("class", "?")
        total = entry.get("total", 0)
        if total == 0:
            continue
        icon, label = HS_LABELS.get(cls, ("⚫", cls))
        hs_lines.append(f"  {icon} {label}: <b>{total:,}</b>")
    lines = [
        f"<b>{server_name}</b>",
        "",
        f"{status_icon} Статус: <b>{status.upper()}</b>  {'🔒 Read-only' if ro else '🔓 RW'}",
        f"⏱ Uptime: <b>{fmt_uptime(uptime)}</b>",
        f"🏷 Версия: <b>v{version}</b>"
        + (f" <code>{git_short}</code>" if git_short else ""),
        f"💻 {arch} / {os_name}",
        "",
        "<b>📈 Соединения</b>",
        f"  Всего: <b>{conns:,}</b>",
        f"  {load_icon} Плохих: {bad:,} ({bad_percent:.1f}%)  |  {hs_icon} HS: {hs_to:,}",
        f"  {online_icon} Онлайн: <b>{online_users}</b> / {users_count}",
    ]
    if bad_lines:
        lines += ["", "<b>🔍 Плохие соединения</b>"] + bad_lines
    if hs_lines:
        lines += ["", "<b>⏳ Фейлы handshake</b>"] + hs_lines
    lines += [
        "",
        "<b>⚙ Runtime</b>",
        f"  {st_icon} {startup}  |  Принимает: {fmt_bool(accepting)}",
        f"  Middle proxy: {fmt_bool(use_me)}  |  ME ready: {fmt_bool(me_ready)}",
    ]
    return "\n".join(lines)


def format_user_list(users: list) -> str:
    if not users:
        return "👥 <b>Пользователи</b>\n\nСписок пуст"
    active = sum(1 for u in users if u.get("current_connections", 0) > 0)
    return f"<b>👥 Клиенты</b>  {active} онлайн / {len(users)} всего"


def format_user_detail(u: dict) -> str:
    conns = u.get("current_connections", 0)
    icon = "🟢" if conns > 0 else "⚪"
    octets = fmt_bytes(u.get("total_octets", 0))
    max_tcp = u.get("max_tcp_conns")
    max_ip = u.get("max_unique_ips")
    quota = u.get("data_quota_bytes")
    exp = u.get("expiration_rfc3339")
    active_ips = u.get("active_unique_ips", 0)
    recent_ips = u.get("recent_unique_ips", 0)
    ip_list = u.get("active_unique_ips_list", [])
    links_data = u.get("links", {})
    all_links = (
        links_data.get("classic", [])
        + links_data.get("secure", [])
        + links_data.get("tls", [])
    )
    lines = [
        f"<b>{icon} {u['username']}</b>",
        "",
        f"🔌 Соединений: <b>{conns}</b>",
        f"📊 Трафик: <b>{octets}</b>",
        f"🌐 IP: {active_ips} активных / {recent_ips} недавних",
    ]
    if ip_list:
        shown = ", ".join(ip_list[:4])
        if len(ip_list) > 4:
            shown += f" +{len(ip_list) - 4}"
        lines.append(f"  <code>{shown}</code>")
    lines += [
        "",
        "<b>⚙️ Лимиты</b>",
        f"  Max TCP: {max_tcp or '—'}  |  Max IP: {max_ip or '—'}",
        f"  Квота: {fmt_bytes(quota) if quota else '—'}",
        f"  Истекает: {exp[:10] if exp else '—'}",
        "",
        f"🔗 Ссылок: {len(all_links)}",
    ]
    return "\n".join(lines)


def format_user_links(u: dict) -> tuple[str, list[str]]:
    """Возвращает (текст-заголовок, список ссылок)"""
    username = u.get("username", "?")
    links_data = u.get("links", {})
    classic = links_data.get("classic", [])
    secure = links_data.get("secure", [])
    tls_links = links_data.get("tls", [])
    all_links = classic + secure + tls_links
    if not all_links:
        return f"<b>🔗 Ссылки — {username}</b>\n\n— нет ссылок —", []
    parts = [f"<b>🔗 Ссылки — {username}</b>"]
    if classic:
        parts.append("\n<b>Classic:</b>")
        for link in classic:
            parts.append(link)
    if secure:
        parts.append("\n<b>Secure (DD):</b>")
        for link in secure:
            parts.append(link)
    if tls_links:
        parts.append("\n<b>TLS:</b>")
        for link in tls_links:
            parts.append(link)
    parts.append("\n<i>Нажмите на ссылку, чтобы скопировать и открыть в Telegram</i>")
    return "\n".join(parts), all_links


def format_runtime_gates(g: dict) -> str:
    startup = g.get("startup_status", "?")
    prog = g.get("startup_progress_pct", 0)
    stage = g.get("startup_stage", "?")
    icons = {
        "ready": "✅",
        "initializing": "🔄",
        "pending": "⏳",
        "failed": "🔴",
        "skipped": "⏭",
    }
    return "\n".join(
        [
            "<b>🎯 Runtime Gates</b>",
            "",
            f"  Startup: {icons.get(startup, '❓')} <b>{startup}</b> ({prog:.0f}%)",
            f"  Стадия: {stage}",
            f"  Принимает соед.: {fmt_bool(g.get('accepting_new_connections', False))}",
            f"  Middle proxy: {fmt_bool(g.get('use_middle_proxy', False))}",
            f"  ME ready: {fmt_bool(g.get('me_runtime_ready', False))}",
            f"  ME→DC fallback: {fmt_bool(g.get('me2dc_fallback_enabled', False))}",
        ]
    )


def format_runtime_init(d: dict) -> str:
    status = d.get("status", "?")
    prog = d.get("progress_pct", 0)
    degraded = d.get("degraded", False)
    elapsed = d.get("total_elapsed_ms", 0)
    mode = d.get("transport_mode", "?")
    ready_at = d.get("ready_at_epoch_secs")
    me = d.get("me", {})
    me_status = me.get("status", "?")
    me_stage = me.get("current_stage", "?")
    me_err = me.get("last_error")
    components = d.get("components", [])
    icons = {
        "ready": "✅",
        "initializing": "🔄",
        "pending": "⏳",
        "failed": "🔴",
        "skipped": "⏭",
        "running": "🔄",
    }
    lines = [
        "<b>🚀 Runtime Init</b>",
        "",
        f"  {icons.get(status, '❓')} <b>{status}</b> ({prog:.0f}%)  |  {'⚠️ degraded' if degraded else 'ok'}",
        f"  Режим: {mode}  |  Время: {elapsed} мс",
        f"  Готов: {fmt_ts(ready_at)}",
        "",
        f"<b>ME:</b> {icons.get(me_status, '❓')} {me_status} — {me_stage}",
    ]
    if me_err:
        lines.append(f"  ⚠️ {me_err}")
    if components:
        lines.append("")
        lines.append("<b>Компоненты:</b>")
        for c in components:
            c_icon = icons.get(c.get("status", ""), "❓")
            dur = c.get("duration_ms")
            dur_str = f" {dur}мс" if dur else ""
            lines.append(f"  {c_icon} {c.get('title', c.get('id', '?'))}{dur_str}")
    return "\n".join(lines)


def format_me_quality(d: dict) -> str:
    if not d.get("enabled") or not d.get("data"):
        return f"<b>📈 ME Quality</b>\n\n❌ {d.get('reason', 'unavailable')}"
    data = d["data"]
    counters = data.get("counters", {})
    drops = data.get("route_drops", {})
    dc_rtt = data.get("dc_rtt", [])
    lines = [
        "<b>📈 ME Quality</b>",
        "",
        f"  Reconnect: {counters.get('reconnect_attempt_total', 0):,} / {counters.get('reconnect_success_total', 0):,} ✅",
        f"  Reader EOF: {counters.get('reader_eof_total', 0):,}  KDF drift: {counters.get('kdf_drift_total', 0):,}",
        f"  Idle close by peer: {counters.get('idle_close_by_peer_total', 0):,}",
        "",
        "<b>Route drops:</b>",
        f"  No conn: {drops.get('no_conn_total', 0):,}  Ch closed: {drops.get('channel_closed_total', 0):,}  Queue: {drops.get('queue_full_total', 0):,}",
    ]
    if dc_rtt:
        lines.append("\n<b>DC RTT:</b>")
        for dc in sorted(dc_rtt, key=lambda x: x.get("dc", 0)):
            alive = dc.get("alive_writers", 0)
            req = dc.get("required_writers", 0)
            cov = dc.get("coverage_pct", 0)
            cov_icon = "🟢" if cov >= 100 else ("🟡" if cov >= 50 else "🔴")
            lines.append(
                f"  DC{dc['dc']}: {fmt_rtt(dc.get('rtt_ema_ms'))} | {alive}/{req} {cov_icon}{cov:.0f}%"
            )
    return "\n".join(lines)


def format_upstream_quality(d: dict) -> str:
    counters = d.get("counters", {})
    summary = d.get("summary")
    upstreams = d.get("upstreams")
    attempt = counters.get("connect_attempt_total", 0)
    success = counters.get("connect_success_total", 0)
    fail = counters.get("connect_fail_total", 0)
    lines = [
        "<b>🔗 Upstream Quality</b>",
        "",
        f"  Попыток: {attempt:,}  Успешных: {success:,}  Ошибок: {fail:,}",
    ]
    if summary:
        lines += [
            "",
            f"  Всего: {summary.get('configured_total', 0)}  🟢 {summary.get('healthy_total', 0)}  🔴 {summary.get('unhealthy_total', 0)}",
        ]
    if upstreams:
        lines.append("\n<b>Upstreams:</b>")
        for u in upstreams[:8]:
            h = "🟢" if u.get("healthy") else "🔴"
            lines.append(
                f"  {h} {u.get('address', '?')} | {fmt_rtt(u.get('effective_latency_ms'))}"
            )
    return "\n".join(lines)


def format_runtime_events(d: dict) -> str:
    if not d.get("enabled"):
        return f"<b>📋 Events</b>\n\n❌ {d.get('reason', 'unavailable')}"
    payload = d.get("data") or {}
    events = payload.get("events", [])
    dropped = payload.get("dropped_total", 0)
    lines = [f"<b>📋 Recent Events</b>  dropped: {dropped}", ""]
    if not events:
        lines.append("— нет событий —")
    else:
        for ev in reversed(events[-15:]):
            ts = fmt_ts(ev.get("ts_epoch_secs"))
            etype = ev.get("event_type", "?")
            ctx = ev.get("context", "")[:60]
            lines.append(f"<code>{ts[-8:-4]}</code> <b>{etype}</b>")
            if ctx:
                lines.append(f"  <i>{ctx}</i>")
    return "\n".join(lines)


def format_connections(d: dict) -> str:
    if not d.get("enabled"):
        return f"<b>👥 Connections</b>\n\n❌ {d.get('reason', 'unavailable')}"
    payload = d.get("data") or {}
    totals = payload.get("totals", {})
    top = payload.get("top", {})
    lines = [
        "<b>👥 Connections</b>",
        "",
        f"  Всего: <b>{totals.get('current_connections', 0):,}</b>",
        f"  ME: {totals.get('current_connections_me', 0):,}  Direct: {totals.get('current_connections_direct', 0):,}",
        f"  Активных юзеров: {totals.get('active_users', 0)}",
    ]
    by_conn = top.get("by_connections", [])
    if by_conn:
        lines.append("\n<b>Топ по соединениям:</b>")
        for u in by_conn[:5]:
            lines.append(
                f"  <code>{u['username']}</code> — {u['current_connections']}🔌 {fmt_bytes(u.get('total_octets', 0))}"
            )
    return "\n".join(lines)


def format_security_posture(d: dict) -> str:
    return "\n".join(
        [
            "<b>🛡️ Security Posture</b>",
            "",
            f"  Read-only: {fmt_bool(d.get('api_read_only', False))}",
            f"  Whitelist: {fmt_bool(d.get('api_whitelist_enabled', False))} ({d.get('api_whitelist_entries', 0)} записей)",
            f"  Auth header: {fmt_bool(d.get('api_auth_header_enabled', False))}",
            f"  PROXY protocol: {fmt_bool(d.get('proxy_protocol_enabled', False))}",
            f"  Log level: {d.get('log_level', '?')}",
            f"  Telemetry core: {fmt_bool(d.get('telemetry_core_enabled', False))}",
            f"  Telemetry user: {fmt_bool(d.get('telemetry_user_enabled', False))}",
            f"  ME telemetry: {d.get('telemetry_me_level', '?')}",
        ]
    )


def format_security_whitelist(d: dict) -> str:
    entries = d.get("entries", [])
    lines = [
        "<b>📋 IP Whitelist</b>",
        "",
        f"  Активен: {fmt_bool(d.get('enabled', False))}  |  Записей: {d.get('entries_total', 0)}",
        f"  Обновлён: {fmt_ts(d.get('generated_at_epoch_secs'))}",
    ]
    if entries:
        lines.append("")
        for e in entries:
            lines.append(f"  <code>{e}</code>")
    return "\n".join(lines)


def format_limits(d: dict) -> str:
    to = d.get("timeouts", {})
    up = d.get("upstream", {})
    mp = d.get("middle_proxy", {})
    return "\n".join(
        [
            "<b>⚙️ Effective Limits</b>",
            "",
            f"  Update interval: {d.get('update_every_secs', '?')}с  |  ME reinit: {d.get('me_reinit_every_secs', '?')}с",
            "",
            "<b>Timeouts:</b>",
            f"  Handshake: {to.get('client_handshake_secs', '?')}с  TG connect: {to.get('tg_connect_secs', '?')}с",
            f"  Keepalive: {to.get('client_keepalive_secs', '?')}с",
            "",
            "<b>Upstream:</b>",
            f"  Retry: {up.get('connect_retry_attempts', '?')} попыток  Backoff: {up.get('connect_retry_backoff_ms', '?')}мс",
            f"  Budget: {up.get('connect_budget_ms', '?')}мс",
            "",
            "<b>Middle Proxy:</b>",
            f"  Floor: {mp.get('floor_mode', '?')}  |  ME→DC fallback: {fmt_bool(mp.get('me2dc_fallback', False))}",
        ]
    )


def format_upstreams(d: dict) -> str:
    enabled = d.get("enabled", False)
    reason = d.get("reason")
    summary = d.get("summary")
    upstreams = d.get("upstreams")
    zero = d.get("zero", {})
    lines = ["<b>🔗 Upstreams</b>", ""]
    if not enabled or reason:
        lines.append(f"  Runtime: ❌ {reason or 'unavailable'}")
    else:
        lines.append("  Runtime: ✅")
    if summary:
        lines += [
            "",
            f"  Всего: {summary.get('configured_total', 0)}  🟢 {summary.get('healthy_total', 0)}  🔴 {summary.get('unhealthy_total', 0)}",
            f"  Direct: {summary.get('direct_total', 0)}  SOCKS5: {summary.get('socks5_total', 0)}",
        ]
    if upstreams:
        lines.append("\n<b>Список:</b>")
        for u in upstreams:
            h = "🟢" if u.get("healthy") else "🔴"
            rtt = fmt_rtt(u.get("effective_latency_ms"))
            kind = u.get("route_kind", "?")
            addr = u.get("address", "?")
            fails = u.get("fails", 0)
            lines.append(
                f"  {h} [{kind}] {addr} {rtt}" + (f" ⚠️{fails}" if fails else "")
            )
    if zero:
        a = zero.get("connect_attempt_total", 0)
        s = zero.get("connect_success_total", 0)
        lines.append(f"\n  Итого: {a:,} попыток / {s:,} успешных")
    return "\n".join(lines)


def format_dcs(d: dict) -> str:
    if not d.get("middle_proxy_enabled"):
        return f"<b>📡 DC Status</b>\n\n❌ {d.get('reason', 'unavailable')}"
    dcs = d.get("dcs", [])
    lines = ["<b>📡 DC Status</b>", ""]
    for dc in sorted(dcs, key=lambda x: x.get("dc", 0)):
        alive = dc.get("alive_writers", 0)
        req = dc.get("required_writers", 0)
        cov = dc.get("coverage_pct", 0)
        rtt = fmt_rtt(dc.get("rtt_ms"))
        load = dc.get("load", 0)
        cov_icon = "🟢" if cov >= 100 else ("🟡" if cov >= 50 else "🔴")
        lines.append(
            f"  {cov_icon} DC{dc.get('dc', '?')}: {alive}/{req} writers ({cov:.0f}%) | RTT {rtt} | {load}🔌"
        )
    return "\n".join(lines)


def format_me_writers(d: dict) -> str:
    if not d.get("middle_proxy_enabled"):
        return f"<b>✍️ ME Writers</b>\n\n❌ {d.get('reason', 'unavailable')}"
    summary = d.get("summary", {})
    writers = d.get("writers", [])
    lines = [
        "<b>✍️ ME Writers</b>",
        "",
        f"  Endpoints: {summary.get('available_endpoints', 0)}/{summary.get('configured_endpoints', 0)} ({fmt_pct(summary.get('available_pct', 0))})",
        f"  Writers: {summary.get('alive_writers', 0)}/{summary.get('required_writers', 0)} ({fmt_pct(summary.get('coverage_pct', 0))})",
    ]
    if writers:
        lines.append(f"\n<b>Writers ({len(writers)}):</b>")
        state_icons = {"warm": "🟡", "active": "🟢", "draining": "🔵"}
        for w in writers[:50]:
            icon = state_icons.get(w.get("state", ""), "⚪")
            clients = w.get("bound_clients", 0)
            lines.append(
                f"  {icon} DC{w.get('dc', '?')} {w.get('endpoint', '?')} | {fmt_rtt(w.get('rtt_ema_ms'))} | {clients}🔌"
            )
        if len(writers) > 50:
            lines.append(f"  … ещё {len(writers) - 50}")
    return "\n".join(lines)
