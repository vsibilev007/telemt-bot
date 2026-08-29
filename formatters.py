"""
Форматтеры ответов API в читаемый текст для Telegram
"""

from __future__ import annotations

import base64
import math
import urllib.parse
from typing import Optional

import tz as _tz


def _extract_sni_from_link(link: str) -> str:
    """Извлекает SNI (домен маскировки) из tg://proxy ссылки."""
    try:
        parsed = urllib.parse.urlparse(link)
        params = urllib.parse.parse_qs(parsed.query)
        secret_hex = params.get("secret", [""])[0]
        if not secret_hex:
            return ""

        # Пробуем hex
        try:
            secret_bytes = bytes.fromhex(secret_hex)
        except ValueError:
            # Нечётная длина — пробуем base64url
            try:
                pad = secret_hex + "=" * (-len(secret_hex) % 4)
                secret_bytes = base64.urlsafe_b64decode(pad)
            except Exception:
                return ""

        # FakeTLS: ee prefix, SNI начинается с байта 17
        if len(secret_bytes) > 17 and secret_bytes[0] == 0xee:
            sni = secret_bytes[17:].decode("utf-8", errors="replace")
            # Убираем невидимые/мусорные символы
            sni = "".join(c for c in sni if c.isprintable())
            return sni
    except Exception:
        pass
    return ""


def _extract_secret_from_link(link: str) -> str:
    """Извлекает 16-байтовый секрет из tg://proxy ссылки (без ee/dd префикса)."""
    try:
        parsed = urllib.parse.urlparse(link)
        params = urllib.parse.parse_qs(parsed.query)
        secret_hex = params.get("secret", [""])[0]
        if not secret_hex or len(secret_hex) < 34:
            return ""
        # ee/dd + 32 hex (16 bytes) + SNI
        secret_bytes = bytes.fromhex(secret_hex[:34])
        if secret_bytes[0] in (0xee, 0xdd):
            return secret_hex[2:34]  # 32 hex chars = 16 bytes
    except Exception:
        pass
    return ""


def make_webproxy_link(hostname: str, secret_hex: str, mode: str = "dd") -> str:
    """Генерирует tg://webproxy ссылку для WEB-режима."""
    return f"tg://webproxy?server={hostname}&secret={mode}{secret_hex}"


def _epoch_to_str(epoch: int) -> str:
    return _tz.fmt_datetime(epoch)


def fmt_bytes(b: Optional[int]) -> str:
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


def fmt_ts(epoch: Optional[int]) -> str:
    if not epoch:
        return "—"
    return _tz.fmt_datetime(epoch)


def fmt_bool(v: bool) -> str:
    return "✅" if v else "❌"


def fmt_pct(v: float) -> str:
    return f"{v:.1f}%"


def fmt_rtt(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v:.1f} мс"


# ─── Dashboard ────────────────────────────────────────────────────────────────

#def format_dashboard(health, summary, sysinfo, gates, server_name):
#    status = health.get("status", "?")
#    status_icon = "🟢" if status == "ok" else "🔴"
#    ro = health.get("read_only", False)
#
#    uptime = summary.get("uptime_seconds", 0)
#    conns = summary.get("connections_total", 0)
#    bad = summary.get("connections_bad_total", 0)
#    hs_to = summary.get("handshake_timeouts_total", 0)
#    users_count = summary.get("configured_users", 0)
#
#    version = sysinfo.get("version", "?")
#    git = sysinfo.get("git_commit", "")
#    git_short = git[:7] if git else ""
#    arch = sysinfo.get("target_arch", "?")
#    os_name = sysinfo.get("target_os", "?")
#
#    startup = gates.get("startup_status", "?")
#    startup_icons = {"ready": "✅", "initializing": "🔄", "pending": "⏳", "failed": "🔴", "skipped": "⏭"}
#    st_icon = startup_icons.get(startup, "❓")
#    accepting = gates.get("accepting_new_connections", False)
#    use_me = gates.get("use_middle_proxy", False)
#    me_ready = gates.get("me_runtime_ready", False)
#
#    return "\n".join([
#        f"<b>📊 Dashboard — {server_name}</b>",
#        "",
#        f"{status_icon} Статус: <b>{status.upper()}</b>  {'🔒 Read-only' if ro else '🔓 RW'}",
#        f"⏱ Uptime: <b>{fmt_uptime(uptime)}</b>",
#        f"🏷 Версия: <b>v{version}</b>" + (f" <code>{git_short}</code>" if git_short else ""),
#        f"💻 {arch} / {os_name}",
#        "",
#        "<b>📈 Соединения</b>",
#        f"  Всего: <b>{conns:,}</b>  |  Плохих: {bad:,}  |  HS timeout: {hs_to:,}",
#        f"  Пользователей: <b>{users_count}</b>",
#        "",
#        "<b>⚙️ Runtime</b>",
#        f"  {st_icon} {startup}  |  Принимает: {fmt_bool(accepting)}",
#        f"  Middle proxy: {fmt_bool(use_me)}  |  ME ready: {fmt_bool(me_ready)}",
#    ])
def _now_str() -> str:
    return _tz.now_str()


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
        "skipped": "⚪"
    }
    st_icon = startup_icons.get(startup, "❓")
    accepting = gates.get("accepting_new_connections", False)
    use_me = gates.get("use_middle_proxy", False)
    me_ready = gates.get("me_runtime_ready", False)

    bad_percent = (bad / conns * 100) if conns else 0
    load_icon = "🟢" if bad_percent < 2 else "🟡" if bad_percent < 5 else "🔴"
    hs_icon = "🟢" if hs_to < 100 else "🟡" if hs_to < 300 else "🔴"
    online_icon = "🟢" if online_users > 0 else "⚪"

    # --- bad by class ---
    BAD_LABELS = {
        "tls_handshake_bad_client":           "Плохой TLS клиент",
        "direct_modes_disabled":              "Прямой режим отключён",
        "unknown_tls_sni":                    "Неизвестный SNI",
        "tls_clienthello_len_out_of_bounds":  "Некорректный ClientHello",
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

    # --- handshake failures by class ---
    HS_LABELS = {
        "timeout":                              ("🟡", "Таймаут"),
        "expected_64_got_0_unexpected_eof":     ("⚫", "Обрыв соединения"),
        "expected_64_got_0_connection_reset":   ("⚫", "Сброс соединения"),
        "other":                                ("⚫", "Прочее"),
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
        f"🏷 Версия: <b>v{version}</b>" + (f" <code>{git_short}</code>" if git_short else ""),
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
        "",
        f"<i>🕐 Обновлено: {_now_str()}</i>",
    ]

    return "\n".join(lines)

# ─── Users ────────────────────────────────────────────────────────────────────

def format_user_list(users: list) -> str:
    if not users:
        return "👥 <b>Пользователи</b>\n\nСписок пуст"
    active = sum(1 for u in users if u.get("current_connections", 0) > 0)
    return f"<b>👥 Клиенты</b>  {active} онлайн / {len(users)} всего"


def format_user_detail(u: dict) -> str:
    conns = u.get("current_connections", 0)
    # enabled: None — старая версия API (поле отсутствует), считаем включённым
    enabled = u.get("enabled", None)
    icon = "🟢" if conns > 0 else "⚪"
    octets = fmt_bytes(u.get("total_octets", 0))
    max_tcp = u.get("max_tcp_conns")
    max_ip = u.get("max_unique_ips")
    quota = u.get("data_quota_bytes")
    exp = u.get("expiration_rfc3339")
    active_ips = u.get("active_unique_ips", 0)
    recent_ips = u.get("recent_unique_ips", 0)
    ip_list = u.get("active_unique_ips_list", [])
    nodes = u.get("_nodes", {})

    # Rate limits (3.4.12+)
    rate_up = u.get("rate_limit_up_bps")
    rate_down = u.get("rate_limit_down_bps")

    links_data = u.get("links", {})
    all_links = links_data.get("classic", []) + links_data.get("secure", []) + links_data.get("tls", [])

    lines = [
        f"<b>{icon} {u['username']}</b>",
    ]

    # Статус disabled — показываем только если API явно вернул enabled=false
    if enabled is False:
        lines.append("🔴 <b>Клиент отключён</b>")

    lines += [
        "",
        f"🔌 Соединений: <b>{conns}</b>",
    ]

    if nodes:
        node_lines = []
        for node_name, node_conns in nodes.items():
            node_icon = "🟢" if node_conns > 0 else "⚫"
            node_lines.append(f"  {node_icon} {node_name}: {node_conns}")
        lines.append("\n".join(node_lines))

    lines += [
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
        f"  Max TCP: {max_tcp if max_tcp else '—'}  |  Max IP: {max_ip if max_ip else '—'}",
        f"  Квота: {fmt_bytes(quota) if quota else '—'}",
        f"  Истекает: {exp[:10] if exp else '—'}",
    ]

    # Rate limits — показываем только если заданы
    if rate_up or rate_down:
        up_str = f"{fmt_bytes(rate_up)}/с" if rate_up else "—"
        down_str = f"{fmt_bytes(rate_down)}/с" if rate_down else "—"
        lines.append(f"  ⬆️ {up_str}  ⬇️ {down_str}")

    lines += [
        "",
        f"🔗 Ссылок: {len(all_links)}",
    ]

    return "\n".join(lines)


def format_users_quota(data: dict) -> str:
    """Форматирует ответ GET /v1/users/quota (3.4.12+)"""
    lines = ["<b>📊 Квоты пользователей</b>", ""]

    users = data.get("users", [])
    if not users:
        lines.append("<i>Квоты не заданы</i>")
        return "\n".join(lines)

    for u in users:
        name = u.get("username", "?")
        used = u.get("total_octets", 0)
        quota = u.get("data_quota_bytes", 0)
        if quota:
            pct = used / quota * 100
            bar_filled = int(pct / 10)
            bar = "█" * bar_filled + "░" * (10 - bar_filled)
            icon = "🔴" if pct >= 90 else ("🟡" if pct >= 70 else "🟢")
            lines.append(
                f"{icon} <b>{name}</b>\n"
                f"  <code>{bar}</code> {pct:.0f}%\n"
                f"  {fmt_bytes(used)} / {fmt_bytes(quota)}"
            )
        else:
            lines.append(f"⚪ <b>{name}</b> — квота не задана")

    return "\n".join(lines)


def _version_tuple(v: str) -> tuple[int, ...]:
    """Парсит версию '3.4.25' в (3, 4, 25) для сравнения."""
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


# Минимальная версия Telemt для WEB Proxy
WEB_PROXY_MIN_VERSION = (3, 5, 5)


def format_user_links(u: dict, web_config: dict = None, telemt_version: str = "") -> tuple[str, list[str]]:
    """Возвращает (текст-заголовок, список ссылок) с доменами маскировки.
    WEB-ссылки tg://webproxy только для Telemt >= 3.5.5.
    Для старых версий — только TLS-ссылки."""
    username = u.get("username", "?")
    links_data = u.get("links", {})
    classic = links_data.get("classic", [])
    secure = links_data.get("secure", [])
    tls_links = links_data.get("tls", [])
    all_links = classic + secure + tls_links

    if not all_links:
        return f"<b>🔗 Ссылки — {username}</b>\n\n— нет ссылок —", []

    parts = [f"<b>🔗 Ссылки — {username}</b>"]

    # WEB-ссылки (tg://webproxy) — только для Telemt >= 3.5.5
    web_links = []
    has_web_support = _version_tuple(telemt_version) >= WEB_PROXY_MIN_VERSION
    if web_config and has_web_support:
        vhosts = web_config.get("vhosts", [])
        for vh in vhosts:
            hostname = vh.get("host", "")
            profiles = vh.get("profiles", [])
            for prof in profiles:
                if prof.get("user") == username:
                    mode = prof.get("secret_mode", "dd")
                    # Извлекаем секрет из TLS-ссылок
                    for link in tls_links:
                        secret = _extract_secret_from_link(link)
                        if secret:
                            web_link = make_webproxy_link(hostname, secret, mode)
                            web_links.append((hostname, web_link))
                            break  # Один секрет на профиль
                    break  # Один профиль на vhost

    if web_links:
        parts.append("\n<b>WEB Proxy:</b>")
        for hostname, link in web_links:
            parts.append(f"🌐 <b>{hostname}</b>")
            parts.append(f"<code>{link}</code>")

    if classic:
        parts.append("\n<b>Classic:</b>")
        for link in classic:
            parts.append(f"<code>{link}</code>")

    if secure:
        parts.append("\n<b>Secure (DD):</b>")
        for link in secure:
            parts.append(f"<code>{link}</code>")

    # TLS-ссылки показываем всегда (WEB Proxy доступен не на всех платформах)
    if tls_links:
        parts.append("\n<b>TLS:</b>")
        for link in tls_links:
            sni = _extract_sni_from_link(link)
            if sni:
                parts.append(f"🌐 <b>{sni}</b>")
            parts.append(f"<code>{link}</code>")

    parts.append("\n<i>Нажмите на ссылку, чтобы скопировать</i>")
    return "\n".join(parts), all_links + [wl[1] for wl in web_links]


# ─── Runtime ──────────────────────────────────────────────────────────────────

def format_runtime_gates(g: dict) -> str:
    startup = g.get("startup_status", "?")
    prog = g.get("startup_progress_pct", 0)
    stage = g.get("startup_stage", "?")
    icons = {"ready": "✅", "initializing": "🔄", "pending": "⏳", "failed": "🔴", "skipped": "⏭"}

    return "\n".join([
        "<b>🎯 Runtime Gates</b>",
        "",
        f"  Startup: {icons.get(startup,'❓')} <b>{startup}</b> ({prog:.0f}%)",
        f"  Стадия: {stage}",
        f"  Принимает соед.: {fmt_bool(g.get('accepting_new_connections', False))}",
        f"  Middle proxy: {fmt_bool(g.get('use_middle_proxy', False))}",
        f"  ME ready: {fmt_bool(g.get('me_runtime_ready', False))}",
        f"  ME→DC fallback: {fmt_bool(g.get('me2dc_fallback_enabled', False))}",
    ])


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
    icons = {"ready": "✅", "initializing": "🔄", "pending": "⏳", "failed": "🔴", "skipped": "⏭", "running": "🔄"}

    lines = [
        "<b>🚀 Runtime Init</b>",
        "",
        f"  {icons.get(status,'❓')} <b>{status}</b> ({prog:.0f}%)  |  {'⚠️ degraded' if degraded else 'ok'}",
        f"  Режим: {mode}  |  Время: {elapsed} мс",
        f"  Готов: {fmt_ts(ready_at)}",
        "",
        f"<b>ME:</b> {icons.get(me_status,'❓')} {me_status} — {me_stage}",
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
        f"  Reconnect: {counters.get('reconnect_attempt_total',0):,} / {counters.get('reconnect_success_total',0):,} ✅",
        f"  Reader EOF: {counters.get('reader_eof_total',0):,}  KDF drift: {counters.get('kdf_drift_total',0):,}",
        f"  Idle close by peer: {counters.get('idle_close_by_peer_total',0):,}",
        "",
        "<b>Route drops:</b>",
        f"  No conn: {drops.get('no_conn_total',0):,}  Ch closed: {drops.get('channel_closed_total',0):,}  Queue: {drops.get('queue_full_total',0):,}",
    ]

    if dc_rtt:
        lines.append("\n<b>DC RTT:</b>")
        for dc in sorted(dc_rtt, key=lambda x: x.get("dc", 0)):
            alive = dc.get("alive_writers", 0)
            req = dc.get("required_writers", 0)
            cov = dc.get("coverage_pct", 0)
            cov_icon = "🟢" if cov >= 100 else ("🟡" if cov >= 50 else "🔴")
            lines.append(f"  DC{dc['dc']}: {fmt_rtt(dc.get('rtt_ema_ms'))} | {alive}/{req} {cov_icon}{cov:.0f}%")

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
            f"  Всего: {summary.get('configured_total',0)}  🟢 {summary.get('healthy_total',0)}  🔴 {summary.get('unhealthy_total',0)}",
        ]

    if upstreams:
        lines.append("\n<b>Upstreams:</b>")
        for u in upstreams[:8]:
            h = "🟢" if u.get("healthy") else "🔴"
            lines.append(f"  {h} {u.get('address','?')} | {fmt_rtt(u.get('effective_latency_ms'))}")

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
        f"  Всего: <b>{totals.get('current_connections',0):,}</b>",
        f"  ME: {totals.get('current_connections_me',0):,}  Direct: {totals.get('current_connections_direct',0):,}",
        f"  Активных юзеров: {totals.get('active_users',0)}",
    ]

    by_conn = top.get("by_connections", [])
    if by_conn:
        lines.append("\n<b>Топ по соединениям:</b>")
        for u in by_conn[:5]:
            lines.append(f"  <code>{u['username']}</code> — {u['current_connections']}🔌 {fmt_bytes(u.get('total_octets',0))}")

    return "\n".join(lines)


# ─── Security ─────────────────────────────────────────────────────────────────

def format_security_posture(d: dict) -> str:
    return "\n".join([
        "<b>🛡️ Security Posture</b>",
        "",
        f"  Read-only: {fmt_bool(d.get('api_read_only', False))}",
        f"  Whitelist: {fmt_bool(d.get('api_whitelist_enabled', False))} ({d.get('api_whitelist_entries',0)} записей)",
        f"  Auth header: {fmt_bool(d.get('api_auth_header_enabled', False))}",
        f"  PROXY protocol: {fmt_bool(d.get('proxy_protocol_enabled', False))}",
        f"  Log level: {d.get('log_level','?')}",
        f"  Telemetry core: {fmt_bool(d.get('telemetry_core_enabled', False))}",
        f"  Telemetry user: {fmt_bool(d.get('telemetry_user_enabled', False))}",
        f"  ME telemetry: {d.get('telemetry_me_level','?')}",
    ])


def format_security_whitelist(d: dict) -> str:
    entries = d.get("entries", [])
    lines = [
        "<b>📋 IP Whitelist</b>",
        "",
        f"  Активен: {fmt_bool(d.get('enabled', False))}  |  Записей: {d.get('entries_total',0)}",
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

    return "\n".join([
        "<b>⚙️ Effective Limits</b>",
        "",
        f"  Update interval: {d.get('update_every_secs','?')}с  |  ME reinit: {d.get('me_reinit_every_secs','?')}с",
        "",
        "<b>Timeouts:</b>",
        f"  Handshake: {to.get('client_handshake_secs','?')}с  TG connect: {to.get('tg_connect_secs','?')}с",
        f"  Keepalive: {to.get('client_keepalive_secs','?')}с",
        "",
        "<b>Upstream:</b>",
        f"  Retry: {up.get('connect_retry_attempts','?')} попыток  Backoff: {up.get('connect_retry_backoff_ms','?')}мс",
        f"  Budget: {up.get('connect_budget_ms','?')}мс",
        "",
        "<b>Middle Proxy:</b>",
        f"  Floor: {mp.get('floor_mode','?')}  |  ME→DC fallback: {fmt_bool(mp.get('me2dc_fallback', False))}",
    ])


# ─── Upstreams ────────────────────────────────────────────────────────────────

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
            f"  Всего: {summary.get('configured_total',0)}  🟢 {summary.get('healthy_total',0)}  🔴 {summary.get('unhealthy_total',0)}",
            f"  Direct: {summary.get('direct_total',0)}  SOCKS5: {summary.get('socks5_total',0)}",
        ]

    if upstreams:
        lines.append("\n<b>Список:</b>")
        for u in upstreams:
            h = "🟢" if u.get("healthy") else "🔴"
            rtt = fmt_rtt(u.get("effective_latency_ms"))
            kind = u.get("route_kind", "?")
            addr = u.get("address", "?")
            fails = u.get("fails", 0)
            lines.append(f"  {h} [{kind}] {addr} {rtt}" + (f" ⚠️{fails}" if fails else ""))

    if zero:
        a = zero.get("connect_attempt_total", 0)
        s = zero.get("connect_success_total", 0)
        lines.append(f"\n  Итого: {a:,} попыток / {s:,} успешных")

    return "\n".join(lines)


# ─── DCs ──────────────────────────────────────────────────────────────────────

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
        lines.append(f"  {cov_icon} DC{dc.get('dc','?')}: {alive}/{req} writers ({cov:.0f}%) | RTT {rtt} | {load}🔌")

    return "\n".join(lines)


def format_me_writers(d: dict) -> str:
    if not d.get("middle_proxy_enabled"):
        return f"<b>✍️ ME Writers</b>\n\n❌ {d.get('reason', 'unavailable')}"

    summary = d.get("summary", {})
    writers = d.get("writers", [])

    lines = [
        "<b>✍️ ME Writers</b>",
        "",
        f"  Endpoints: {summary.get('available_endpoints',0)}/{summary.get('configured_endpoints',0)} ({fmt_pct(summary.get('available_pct',0))})",
        f"  Writers: {summary.get('alive_writers',0)}/{summary.get('required_writers',0)} ({fmt_pct(summary.get('coverage_pct',0))})",
    ]

    if writers:
        lines.append(f"\n<b>Writers ({len(writers)}):</b>")
        state_icons = {"warm": "🟡", "active": "🟢", "draining": "🔵"}
        for w in writers[:50]:
            icon = state_icons.get(w.get("state", ""), "⚪")
            clients = w.get("bound_clients", 0)
            lines.append(
                f"  {icon} DC{w.get('dc','?')} {w.get('endpoint','?')} | {fmt_rtt(w.get('rtt_ema_ms'))} | {clients}🔌"
            )
        if len(writers) > 50:
            lines.append(f"  … ещё {len(writers)-50}")

    return "\n".join(lines)



# ─── TLS Fingerprints (3.4.14+) ───────────────────────────────────────────────

def _fmt_fp_row(fp: dict, show_scope: bool = False) -> list[str]:
    ja4   = fp.get("ja4", "?")
    ja3   = fp.get("ja3", "")
    total = fp.get("total", 0)
    auths = fp.get("auth_success", 0)
    bad   = fp.get("bad_or_probe", 0)
    last  = fp.get("last_seen_epoch_secs")
    scope = fp.get("scope", "")

    if bad > 0 and auths == 0:
        status = "🔴"
    elif bad > 0:
        status = "🟡"
    else:
        status = "🟢"

    time_str  = f"  <i>{_tz.fmt_dt(last, '%H:%M')}</i>" if last else ""
    scope_str = ("\n  📍 <code>" + scope + "</code>") if show_scope and scope else ""
    ja3_str   = ("\n  JA3: <code>" + ja3 + "</code>") if ja3 else ""

    row = (
        status + " <code>" + ja4 + "</code>" + time_str + "\n"
        + "  ×" + str(total) + " | ✅" + str(auths) + " | 🔴" + str(bad)
        + ja3_str + scope_str
    )
    return [row]


def format_tls_fingerprints(d: dict) -> str:
    enabled = d.get("enabled", False)
    reason  = d.get("reason")

    if not enabled or reason:
        return (
            f"<b>🔍 TLS Fingerprints</b>\n\n"
            f"❌ {reason or 'unavailable'}\n\n"
            f"<i>Требуется general.beobachten = true в конфиге</i>"
        )

    data         = d.get("data") or {}
    by_fp        = data.get("by_fingerprint", [])
    by_ip        = data.get("by_ip", [])
    by_user      = data.get("by_user", [])
    dropped      = data.get("dropped_total", 0)
    parse_err    = data.get("parse_error_total", 0)
    retention    = data.get("retention_secs", 0)

    auth_total = sum(fp.get("auth_success", 0) for fp in by_fp)
    bad_total  = sum(fp.get("bad_or_probe", 0) for fp in by_fp)

    lines = [
        "<b>🔍 TLS Fingerprints</b>",
        f"<i>Уникальных: {len(by_fp)} | ✅ {auth_total} успешных | 🔴 {bad_total} плохих/зондов</i>",
        f"<i>Окно: {retention // 60} мин | Отброшено: {dropped} | Ошибок: {parse_err}</i>",
    ]

    sep = "┄" * 20

    # ── by_fingerprint ────────────────────────────────────────────────────────
    if by_fp:
        lines += ["", "<b>По fingerprint:</b>"]
        rows = sorted(by_fp, key=lambda x: -x.get("total", 0))[:10]
        for i, fp in enumerate(rows):
            if i > 0:
                lines.append(sep)
            lines += _fmt_fp_row(fp, show_scope=False)

    # ── by_ip — только плохие ─────────────────────────────────────────────────
    bad_by_ip = [fp for fp in by_ip if fp.get("bad_or_probe", 0) > 0]
    if bad_by_ip:
        lines += ["", "<b>🔴 Плохие по IP:</b>"]
        rows = sorted(bad_by_ip, key=lambda x: -x.get("bad_or_probe", 0))[:5]
        for i, fp in enumerate(rows):
            if i > 0:
                lines.append(sep)
            lines += _fmt_fp_row(fp, show_scope=True)

        # ── by_user ───────────────────────────────────────────────────────────────
    if by_user:
        lines += ["", "<b>По пользователям:</b>"]
        user_totals: dict[str, dict] = {}
        for fp in by_user:
            scope = fp.get("scope", "?")
            if scope not in user_totals:
                user_totals[scope] = {"total": 0, "auth_success": 0, "bad_or_probe": 0}
            user_totals[scope]["total"]        += fp.get("total", 0)
            user_totals[scope]["auth_success"] += fp.get("auth_success", 0)
            user_totals[scope]["bad_or_probe"] += fp.get("bad_or_probe", 0)

        for username, stats in sorted(user_totals.items(), key=lambda x: -x[1]["total"])[:8]:
            bad  = stats["bad_or_probe"]
            auth = stats["auth_success"]
            icon = "🔴" if bad > 0 and auth == 0 else ("🟡" if bad > 0 else "🟢")
            lines.append(f"  {icon} <b>{username}</b>  ×{stats['total']} | ✅{auth} | 🔴{bad}")

    lines.append(f"\n<i>🕐 {_now_str()}</i>")
    return "\n".join(lines)


# ─── WEB Proxy ────────────────────────────────────────────────────────────────

_LIFECYCLE_ICONS = {
    "running": "🟢",
    "starting": "🟡",
    "draining": "🟠",
    "drained": "🔴",
    "no_web_listener": "⚪",
    "deadline_exceeded": "🔴",
}

_CARRIER_LABELS = {
    "https": "HTTPS",
    "https-lanes": "HTTPS Lanes",
    "websocket": "WebSocket",
    "websocket-lanes": "WS Lanes",
}

_STATE_ICONS = {
    "provisional": "🟡",
    "committed": "🔵",
    "healthy": "🟢",
    "closing": "🔴",
    "superseded": "⚪",
    "closed": "⚫",
}


def format_web_status(d: dict) -> str:
    """Форматирует GET /v1/runtime/web/status."""
    lifecycle = d.get("lifecycle", "unknown")
    icon = _LIFECYCLE_ICONS.get(lifecycle, "❓")
    available = d.get("available", False)
    age_ms = d.get("lifecycle_age_ms", 0)
    age_str = f"{age_ms // 60000}м" if age_ms > 60000 else f"{age_ms // 1000}с"
    listeners = d.get("listeners", [])
    eff_enabled = d.get("effective_config_enabled", False)

    lines = [
        f"<b>🌐 WEB Proxy Status</b>",
        f"{icon} Lifecycle: <b>{lifecycle}</b> ({age_str})",
        f"Config enabled: {'✅' if eff_enabled else '❌'}",
    ]
    if listeners:
        lines.append(f"Listeners: <code>{', '.join(listeners)}</code>")

    rt = d.get("runtime")
    if rt:
        gen = rt.get("generation_id", "?")
        ri = rt.get("runtime_instance", "")[:12]
        lines.append(f"\n<b>Runtime</b> (gen {gen}, <code>{ri}…</code>)")

        mgr = rt.get("manager", {})
        issuance = mgr.get("issuance_enabled", False)
        lines.append(f"Issuance: {'✅' if issuance else '❌'}")

        limits = rt.get("limits", {})
        if limits:
            lines.append(f"Limits: max_sessions={limits.get('max_sessions', '?')}, "
                         f"max_http_handlers={limits.get('max_http_handlers', '?')}")

        # Stream plane
        sp = rt.get("stream_plane", {})
        if sp:
            active = sp.get("active_streams", 0)
            total = sp.get("total_streams", 0)
            lines.append(f"Streams: {active} active / {total} total")

        # Manager plane
        mp = rt.get("manager_plane", {})
        if mp:
            sessions = mp.get("active_sessions", 0)
            bootstraps = mp.get("active_bootstraps", 0)
            lines.append(f"Sessions: {sessions} | Bootstraps: {bootstraps}")

        # WebSocket plane
        wsp = rt.get("websocket_plane", {})
        if wsp:
            ws_active = wsp.get("active_connections", 0)
            ws_total = wsp.get("total_connections", 0)
            lines.append(f"WebSocket: {ws_active} active / {ws_total} total")

        # Learning plane
        lp = rt.get("learning_plane", {})
        if lp:
            epoch = lp.get("epoch", "?")
            entries = lp.get("entries", 0)
            lines.append(f"Learning: epoch={epoch}, entries={entries}")

        # Debug plane
        dp = rt.get("debug_plane", {})
        if dp:
            records = dp.get("records", 0)
            bytes_held = dp.get("bytes", 0)
            lines.append(f"Debug: {records} records, {fmt_bytes(bytes_held)}")

        partial = rt.get("partial", [])
        if partial:
            lines.append(f"<i>⚠️ Partial: {', '.join(partial)}</i>")
    elif not available:
        reason = d.get("reason", "")
        if reason:
            lines.append(f"\n❌ {reason}")

    lines.append(f"\n<i>🕐 {_now_str()}</i>")
    return "\n".join(lines)


def format_web_sessions(data: dict) -> str:
    """Форматирует GET /v1/runtime/web/sessions."""
    sessions = data.get("sessions", [])
    total = data.get("total", len(sessions))
    next_cursor = data.get("next_cursor", "")
    truncated = data.get("scan_truncated", False)

    if not sessions:
        return (
            "<b>🌐 WEB Sessions</b>\n\n"
            "Активных сессий нет.\n\n"
            f"<i>🕐 {_now_str()}</i>"
        )

    lines = [
        f"<b>🌐 WEB Sessions</b> ({total})",
        "",
    ]

    for s in sessions[:20]:
        ref = s.get("session_ref", "?")
        short_ref = ref.split(".")[-1][:8] if "." in ref else ref[:8]
        user = s.get("user", "?")
        ip = s.get("client_ip", s.get("ip", "?"))
        carrier = s.get("carrier", "?")
        state = s.get("state", "?")
        streams = s.get("streams", s.get("active_streams", 0))
        age_ms = s.get("age_ms", 0)
        idle_ms = s.get("idle_ms", 0)
        age_s = age_ms // 1000 if age_ms else s.get("age_secs", 0)
        idle_s = idle_ms // 1000 if idle_ms else s.get("idle_secs", 0)

        state_icon = _STATE_ICONS.get(state, "❓")
        carrier_label = _CARRIER_LABELS.get(carrier, carrier)
        age_str = f"{age_s // 60}м" if age_s >= 60 else f"{age_s}с"
        idle_str = f"{idle_s // 60}м" if idle_s >= 60 else f"{idle_s}с"

        lines.append(
            f"{state_icon} <code>{short_ref}</code>  "
            f"<b>{user}</b>  {ip}\n"
            f"   {carrier_label} | streams={streams} | "
            f"age={age_str} | idle={idle_str}"
        )

    if truncated:
        lines.append(f"\n<i>⚠️ Показано {len(sessions)} из {total} (scan limit)</i>")
    if next_cursor:
        lines.append(f"<i>Есть ещё (cursor: {next_cursor[:16]}…)</i>")

    lines.append(f"\n<i>🕐 {_now_str()}</i>")
    return "\n".join(lines)


def format_web_session_detail(d: dict) -> str:
    """Форматирует GET /v1/runtime/web/sessions/{ref}."""
    ref = d.get("session_ref", "?")
    user = d.get("user", "?")
    ip = d.get("client_ip", d.get("ip", "?"))
    host = d.get("host", "?")
    carrier = d.get("carrier", "?")
    state = d.get("state", "?")
    streams = d.get("streams", d.get("active_streams", 0))
    tasks = d.get("tasks", d.get("active_tasks", 0))
    lanes = d.get("lanes", d.get("active_lanes", 0))
    ws_conns = d.get("websocket_active", d.get("active_websocket_connections", 0))
    age_ms = d.get("age_ms", 0)
    idle_ms = d.get("idle_ms", 0)
    age_s = age_ms // 1000 if age_ms else d.get("age_secs", 0)
    idle_s = idle_ms // 1000 if idle_ms else d.get("idle_secs", 0)
    idle_s = d.get("idle_secs", 0)
    pending = d.get("pending_bytes", 0)
    control = d.get("control_bytes", 0)
    ua = d.get("user_agent", "")
    key_id = d.get("key_id", "")
    attempt = d.get("attempt", "")
    negotiation_left = d.get("negotiation_time_remaining_secs")

    state_icon = _STATE_ICONS.get(state, "❓")
    carrier_label = _CARRIER_LABELS.get(carrier, carrier)

    lines = [
        f"<b>🌐 WEB Session</b>",
        f"Ref: <code>{ref}</code>",
        f"{state_icon} State: <b>{state}</b>",
        "",
        f"👤 User: <b>{user}</b>",
        f"📍 IP: <code>{ip}</code>",
        f"🏷 Host: <code>{host}</code>",
        f"🔗 Carrier: <b>{carrier_label}</b>",
    ]
    if attempt:
        lines.append(f"Attempt: {attempt}")

    lines.append("")
    lines.append(f"Streams: {streams} | Tasks: {tasks} | Lanes: {lanes}")
    if ws_conns:
        lines.append(f"WebSocket connections: {ws_conns}")
    lines.append(f"Pending: {fmt_bytes(pending)} | Control: {fmt_bytes(control)}")
    lines.append(f"Age: {age_s // 60}м {age_s % 60}с | Idle: {idle_s}с")

    if ua:
        ua_short = ua[:60] + ("…" if len(ua) > 60 else "")
        lines.append(f"UA: <code>{ua_short}</code>")
    if key_id:
        lines.append(f"Key: <code>{key_id}</code>")
    if negotiation_left is not None:
        lines.append(f"Negotiation left: {negotiation_left}с")

    lines.append(f"\n<i>🕐 {_now_str()}</i>")
    return "\n".join(lines)

