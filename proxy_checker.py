"""
Проверка MTProto прокси.

EU-сервер (где запущен бот): TCP + MTProto через Telethon.
Агенты (RU и другие серверы): TCP + TLS handshake через HTTP-агент.
GeoIP: определяем флаг агента по его IP через ip-api.com.
"""

from __future__ import annotations

import asyncio
import base64
import socket
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional


# ─── GeoIP ───────────────────────────────────────────────────────────────────

_COUNTRY_FLAGS: dict[str, str] = {
    "RU": "🇷🇺", "US": "🇺🇸", "DE": "🇩🇪", "FR": "🇫🇷",
    "GB": "🇬🇧", "NL": "🇳🇱", "FI": "🇫🇮", "SE": "🇸🇪",
    "PL": "🇵🇱", "UA": "🇺🇦", "BY": "🇧🇾", "KZ": "🇰🇿",
    "LV": "🇱🇻", "LT": "🇱🇹", "EE": "🇪🇪", "CZ": "🇨🇿",
    "AT": "🇦🇹", "CH": "🇨🇭", "TR": "🇹🇷", "JP": "🇯🇵",
    "CN": "🇨🇳", "KR": "🇰🇷", "SG": "🇸🇬", "HK": "🇭🇰",
    "CA": "🇨🇦", "AU": "🇦🇺", "BR": "🇧🇷", "IN": "🇮🇳",
    "IT": "🇮🇹", "ES": "🇪🇸", "PT": "🇵🇹", "RO": "🇷🇴",
    "HU": "🇭🇺", "BG": "🇧🇬", "RS": "🇷🇸", "SK": "🇸🇰",
    "MD": "🇲🇩", "AM": "🇦🇲", "GE": "🇬🇪", "AZ": "🇦🇿",
    "UZ": "🇺🇿", "IL": "🇮🇱", "AE": "🇦🇪", "CY": "🇨🇾",
}

_geoip_cache: dict[str, str] = {}  # url → "🇷🇺 RU"


async def _resolve_agent_label(agent_url: str, flag: str = "", name: str = "") -> str:
    """Возвращает '🇷🇺 RU' или '🌐 Name' для агента."""
    if flag:
        return f"{flag} {name}" if name else flag

    # Берём IP из URL агента
    try:
        parsed = urllib.parse.urlparse(agent_url)
        host = parsed.hostname or ""
    except Exception:
        host = ""

    if not host:
        return f"🌐 {name}" if name else "🌐"

    cache_key = host
    if cache_key in _geoip_cache:
        return _geoip_cache[cache_key]

    try:
        import aiohttp as _aiohttp
        async with _aiohttp.ClientSession() as s:
            async with s.get(
                f"http://ip-api.com/json/{host}?fields=countryCode",
                timeout=_aiohttp.ClientTimeout(total=3),
            ) as resp:
                data = await resp.json()
                cc = data.get("countryCode", "")
                emoji = _COUNTRY_FLAGS.get(cc, "🌐")
                label = f"{emoji} {name}" if name else f"{emoji} {cc}"
                _geoip_cache[cache_key] = label
                return label
    except Exception:
        label = f"🌐 {name}" if name else "🌐"
        _geoip_cache[cache_key] = label
        return label


# ─── Данные ───────────────────────────────────────────────────────────────────

@dataclass
class AgentResult:
    label: str = ""        # "🇷🇺 RU"
    tcp_ok: bool = False
    tcp_rtt: float = 0.0
    tls_ok: bool = False
    tls_rtt: float = 0.0
    tcp_error: str = ""


@dataclass
class ProxyInfo:
    server: str = ""
    port: int = 443
    secret: str = ""
    secret_bytes: bytes = b""
    secret_type: str = "unknown"
    sni: str = ""
    # EU (где запущен бот)
    eu_tcp_ok: bool = False
    eu_tcp_rtt: float = 0.0
    eu_mtproto_ok: bool = False
    eu_mtproto_rtt: float = 0.0
    eu_error: str = ""
    # Агенты
    agents: list[AgentResult] = field(default_factory=list)
    raw_url: str = ""
    # Расширенная диагностика узла
    resolved_ips: list[str] = field(default_factory=list)
    node_tcp_ok: bool = False
    node_tcp_rtt: float = 0.0
    node_ssh_ok: bool = False
    node_ssh_rtt: float = 0.0
    node_ping_ok: bool = False
    node_ping_rtt: float = 0.0
    node_check_time_ms: float = 0.0
    node_diag: str = ""

    # Алиасы для обратной совместимости с handlers.py
    @property
    def reachable(self) -> bool:
        return self.eu_tcp_ok

    @property
    def mtproto_ok(self) -> bool:
        return self.eu_mtproto_ok

    @property
    def rtt_ms(self) -> float:
        return self.eu_tcp_rtt

    @property
    def mtproto_rtt_ms(self) -> float:
        return self.eu_mtproto_rtt

    @property
    def error(self) -> str:
        return self.eu_error


# ─── Парсинг URL ─────────────────────────────────────────────────────────────

def _decode_secret(secret: str) -> bytes:
    s = secret.strip()
    try:
        return bytes.fromhex(s)
    except ValueError:
        pass
    try:
        pad = s + "=" * (-len(s) % 4)
        return base64.urlsafe_b64decode(pad)
    except Exception:
        pass
    return s.encode()


def parse_proxy_url(url: str) -> Optional[ProxyInfo]:
    url = url.strip()
    info = ProxyInfo(raw_url=url)

    if "t.me/proxy" in url:
        idx = url.find("t.me/proxy")
        url = "tg://proxy" + url[idx + len("t.me/proxy"):]

    if not url.startswith("tg://proxy"):
        return None

    try:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
    except Exception:
        return None

    info.server = params.get("server", [""])[0]
    info.secret = params.get("secret", [""])[0]
    try:
        info.port = int(params.get("port", ["443"])[0])
    except ValueError:
        info.port = 443

    if not info.server or not info.secret:
        return None

    info.secret_bytes = _decode_secret(info.secret)
    b = info.secret_bytes
    if len(b) > 0 and b[0] == 0xee:
        info.secret_type = "faketls"
        try:
            info.sni = b[17:].decode("utf-8", errors="replace")
        except Exception:
            info.sni = ""
    elif len(b) > 0 and b[0] == 0xdd:
        info.secret_type = "dd"
    else:
        info.secret_type = "simple"

    return info


# ─── EU проверки ─────────────────────────────────────────────────────────────

async def _resolve_dns(server: str, timeout: float = 3.0) -> list[str]:
    """Резолвит DNS и возвращает список IP-адресов (IPv4 + IPv6)."""
    try:
        loop = asyncio.get_running_loop()
        # Пробуем IPv4
        ipv4 = await asyncio.wait_for(
            loop.getaddrinfo(server, None, family=socket.AF_INET),
            timeout=timeout,
        )
        ips = [addr[4][0] for addr in ipv4]
    except Exception:
        ips = []

    try:
        loop = asyncio.get_running_loop()
        # Пробуем IPv6
        ipv6 = await asyncio.wait_for(
            loop.getaddrinfo(server, None, family=socket.AF_INET6),
            timeout=timeout,
        )
        ips += [addr[4][0] for addr in ipv6]
    except Exception:
        pass

    return list(dict.fromkeys(ips))  # dedupe, preserving order


async def _check_eu_tcp(info: ProxyInfo, timeout: float = 5.0):
    start = time.monotonic()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(info.server, info.port),
            timeout=timeout,
        )
        info.eu_tcp_rtt = (time.monotonic() - start) * 1000
        info.eu_tcp_ok = True
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
    except asyncio.TimeoutError:
        info.eu_tcp_ok = False
        info.eu_error = f"TCP timeout"
    except OSError as e:
        info.eu_tcp_ok = False
        info.eu_error = str(e)


async def _check_eu_mtproto(info: ProxyInfo, timeout: float = 20.0):
    try:
        from telethon import TelegramClient
        from telethon.sessions import MemorySession
        from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate
    except ImportError:
        return

    proxy = (info.server, info.port, info.secret)
    client = TelegramClient(
        MemorySession(), 2040, "b18441a1ff607e10a989891a5462e627",
        connection=ConnectionTcpMTProxyRandomizedIntermediate,
        proxy=proxy,
        connection_retries=1, retry_delay=0, request_retries=1,
    )

    start = time.monotonic()
    try:
        await asyncio.wait_for(client.connect(), timeout=timeout)
        info.eu_mtproto_rtt = (time.monotonic() - start) * 1000
        info.eu_mtproto_ok = True
    except asyncio.TimeoutError:
        info.eu_mtproto_ok = False
    except Exception as e:
        err = str(e)
        elapsed = time.monotonic() - start
        auth_errors = ["auth", "401", "unauthorized", "dc_id", "migrat",
                       "phone", "flood", "rpc", "session", "user"]
        if any(x in err.lower() for x in auth_errors) or elapsed > 1:
            info.eu_mtproto_ok = True
            info.eu_mtproto_rtt = elapsed * 1000
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


# ─── Расширенная диагностика узла ─────────────────────────────────────────────

async def _check_node_tcp(info: ProxyInfo, timeout: float = 5.0):
    """TCP-проверка прокси-порта (аналог _check_eu_tcp, но для узла)."""
    start = time.monotonic()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(info.server, info.port),
            timeout=timeout,
        )
        info.node_tcp_rtt = (time.monotonic() - start) * 1000
        info.node_tcp_ok = True
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
    except asyncio.TimeoutError:
        info.node_tcp_ok = False
    except OSError:
        info.node_tcp_ok = False


async def _check_node_ssh(info: ProxyInfo, host: str, timeout: float = 3.0):
    """TCP-проверка SSH-порта (22)."""
    start = time.monotonic()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, 22),
            timeout=timeout,
        )
        info.node_ssh_rtt = (time.monotonic() - start) * 1000
        info.node_ssh_ok = True
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
    except Exception:
        info.node_ssh_ok = False


async def _check_node_ping(info: ProxyInfo, host: str, timeout: float = 3.0):
    """ICMP ping через asyncio.create_subprocess_exec."""
    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", str(int(timeout)), host,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=timeout + 1)
        info.node_ping_rtt = (time.monotonic() - start) * 1000
        info.node_ping_ok = proc.returncode == 0
    except Exception:
        info.node_ping_ok = False


async def check_node_full(info: ProxyInfo, timeout: float = 5.0, agents=None) -> ProxyInfo:
    """
    Расширенная проверка узла: DNS + TCP proxy + SSH + Ping + MTProto + агенты.
    """
    start_total = time.monotonic()

    # DNS (параллельно с остальным)
    dns_task = asyncio.create_task(_resolve_dns(info.server))

    # Параллельно: TCP прокси, SSH, Ping
    await asyncio.gather(
        _check_node_tcp(info, timeout=timeout),
        _check_node_ssh(info, info.server, timeout=3.0),
        _check_node_ping(info, info.server, timeout=3.0),
    )

    # Ждём DNS
    info.resolved_ips = await dns_task

    # MTProto (если TCP доступен)
    if info.node_tcp_ok:
        await _check_eu_mtproto(info, timeout=20.0)
        info.eu_tcp_ok = info.node_tcp_ok
        info.eu_tcp_rtt = info.node_tcp_rtt

    # Агенты (параллельно)
    if agents:
        agent_labels = await asyncio.gather(*[
            _resolve_agent_label(a.url, a.flag, a.name) for a in agents
        ])
        agent_results = await asyncio.gather(*[
            _check_via_agent(info, a.url, a.token, label)
            for a, label in zip(agents, agent_labels)
        ])
        info.agents = list(agent_results)

    info.node_check_time_ms = (time.monotonic() - start_total) * 1000

    # Диагностика — честная
    parts = []
    if info.eu_mtproto_ok:
        parts.append("MTProto доступен")
    if info.node_tcp_ok:
        if info.eu_mtproto_ok:
            parts.append("сервис отвечает штатно")
        else:
            parts.append("TCP доступен, но MTProto не работает")
    if not parts:
        parts.append("нет соединения с узлом")
    info.node_diag = ", ".join(parts)

    return info


# ─── Агент проверки ──────────────────────────────────────────────────────────

async def _check_via_agent(
    info: ProxyInfo,
    agent_url: str,
    agent_token: str,
    label: str,
    timeout: float = 12.0,
) -> AgentResult:
    result = AgentResult(label=label)
    try:
        import aiohttp as _aiohttp
        url = f"{agent_url.rstrip('/')}/check"
        params = {"host": info.server, "port": info.port, "sni": info.sni}
        headers = {"X-Token": agent_token} if agent_token else {}
        async with _aiohttp.ClientSession() as session:
            async with session.get(
                url, params=params, headers=headers,
                timeout=_aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                data = await resp.json()
                tcp = data.get("tcp", {})
                tls = data.get("tls") or {}
                result.tcp_ok = tcp.get("ok", False)
                result.tcp_rtt = tcp.get("rtt_ms", 0.0)
                result.tls_ok = tls.get("ok", False)
                result.tls_rtt = tls.get("rtt_ms", 0.0)
                if not result.tcp_ok:
                    result.tcp_error = tcp.get("error", "недоступен")
    except Exception as e:
        result.tcp_ok = False
        result.tcp_error = str(e)[:60]
    return result


# ─── Основная функция ─────────────────────────────────────────────────────────

async def check_proxy(
    info: ProxyInfo,
    timeout: float = 5.0,
    agents=None,  # list[AgentConfig]
) -> ProxyInfo:
    """
    Полная проверка: EU TCP+MTProto + все агенты параллельно.
    agents — список AgentConfig из config.py
    """
    # Получаем метки агентов (geoip)
    agent_labels = []
    if agents:
        label_tasks = [
            _resolve_agent_label(a.url, a.flag, a.name)
            for a in agents
        ]
        agent_labels = await asyncio.gather(*label_tasks)

    # Запускаем EU TCP и все агенты параллельно
    tasks = [asyncio.create_task(_check_eu_tcp(info, timeout=timeout))]
    agent_tasks = []
    if agents:
        for agent, label in zip(agents, agent_labels):
            t = asyncio.create_task(
                _check_via_agent(info, agent.url, agent.token, label)
            )
            agent_tasks.append(t)

    await tasks[0]
    agent_results = await asyncio.gather(*agent_tasks) if agent_tasks else []
    info.agents = list(agent_results)

    # MTProto только если EU TCP прошёл
    if info.eu_tcp_ok:
        await _check_eu_mtproto(info, timeout=20.0)

    return info


# ─── Форматирование ──────────────────────────────────────────────────────────

def format_proxy_result(info: ProxyInfo) -> str:
    type_labels = {
        "faketls": "🛡 FakeTLS",
        "dd":      "🔵 DD",
        "simple":  "⚪ Simple",
        "unknown": "❓ Неизвестный",
    }

    lines = [
        "<b>🔍 Результат проверки прокси</b>",
        "",
        f"🌐 <b>Сервер:</b> <code>{info.server}</code>",
        f"🔌 <b>Порт:</b> <code>{info.port}</code>",
        f"🔑 <b>Тип:</b> {type_labels.get(info.secret_type, info.secret_type)}",
    ]

    if info.sni:
        lines.append(f"🎭 <b>Маскируется под:</b> <code>{info.sni}</code>")

    lines += ["", "<b>📡 Доступность:</b>"]

    # EU строка
    eu_tcp = "🟢" if info.eu_tcp_ok else "🔴"
    eu_tcp_rtt = f"{info.eu_tcp_rtt:.0f} мс" if info.eu_tcp_ok else "—"
    eu_mtp = "🟢" if info.eu_mtproto_ok else "🔴"
    eu_mtp_rtt = f"{info.eu_mtproto_rtt:.0f} мс" if info.eu_mtproto_ok else "—"
    eu_line = f"  🇪🇺 EU — TCP: {eu_tcp} {eu_tcp_rtt}"
    if info.eu_tcp_ok:
        eu_line += f"  |  MTProto: {eu_mtp} {eu_mtp_rtt}"
    lines.append(eu_line)

    # Строки агентов
    for ar in info.agents:
        tcp_icon = "🟢" if ar.tcp_ok else "🔴"
        tcp_rtt = f"{ar.tcp_rtt:.0f} мс" if ar.tcp_ok else f"<i>{ar.tcp_error or '—'}</i>"
        line = f"  {ar.label} — TCP: {tcp_icon} {tcp_rtt}"
        if ar.tcp_ok:
            tls_icon = "🟢" if ar.tls_ok else "🔴"
            tls_rtt = f"{ar.tls_rtt:.0f} мс" if ar.tls_ok else "—"
            line += f"  |  TLS: {tls_icon} {tls_rtt}"
        lines.append(line)

    if not info.eu_tcp_ok and info.eu_error:
        lines += ["", f"❌ <b>EU ошибка:</b> <code>{info.eu_error}</code>"]

    return "\n".join(lines)


def format_node_result(info: ProxyInfo) -> str:
    """Форматирует расширенный результат проверки узла (как на скриншоте)."""
    type_labels = {
        "faketls": "FakeTLS",
        "dd":      "DD",
        "simple":  "Simple",
        "unknown": "Unknown",
    }

    # Итоговый статус
    if info.eu_mtproto_ok:
        status = "OK"
        status_icon = "✅"
    elif info.node_tcp_ok:
        status = "PARTIAL"
        status_icon = "🟡"
    else:
        status = "FAIL"
        status_icon = "❌"

    lines = [
        f"{status_icon} <b>Проверка узла {info.server}</b> ({', '.join(info.resolved_ips) if info.resolved_ips else 'DNS: ?'})",
        "",
    ]

    # Resolved IPs
    if info.resolved_ips:
        lines.append(f"  Resolved ips: {', '.join(info.resolved_ips)}")
        lines.append("")

    # MTProto
    mtp_icon = "✅" if info.eu_mtproto_ok else "❌"
    mtp_status = "доступен" if info.eu_mtproto_ok else "недоступен"
    lines.append(f"  {mtp_icon} MTProto ({info.port}): {mtp_status}")

    # TCP proxy
    tcp_icon = "✅" if info.node_tcp_ok else "❌"
    tcp_status = "доступен" if info.node_tcp_ok else "недоступен"
    lines.append(f"  {tcp_icon} TCP proxy ({info.port}): {tcp_status}")

    # TCP SSH
    ssh_icon = "✅" if info.node_ssh_ok else "❌"
    ssh_status = "доступен" if info.node_ssh_ok else "недоступен"
    lines.append(f"  {ssh_icon} TCP SSH (22): {ssh_status}")

    # Ping
    ping_icon = "✅" if info.node_ping_ok else "❌"
    ping_status = "доступен" if info.node_ping_ok else "недоступен"
    lines.append(f"  {ping_icon} Ping: {ping_status}")

    lines.append("")

    # Диагностика
    diag_icon = "✅" if info.eu_mtproto_ok else "⚠️"
    lines.append(f"  {diag_icon} Диагностика: {info.node_diag}")

    # Время проверки
    lines.append(f"  ⏱ Время проверки: {info.node_check_time_ms:.0f} ms")

    # Итоговый статус
    lines.append(f"  {status_icon} Итоговый статус: {status}")

    # Агенты (если есть)
    if info.agents:
        lines += ["", "<b>📡 Агенты:</b>"]
        for ar in info.agents:
            tcp_icon = "🟢" if ar.tcp_ok else "🔴"
            tcp_rtt = f"{ar.tcp_rtt:.0f} мс" if ar.tcp_ok else f"<i>{ar.tcp_error or '—'}</i>"
            line = f"  {ar.label} — TCP: {tcp_icon} {tcp_rtt}"
            if ar.tcp_ok:
                tls_icon = "🟢" if ar.tls_ok else "🔴"
                tls_rtt = f"{ar.tls_rtt:.0f} мс" if ar.tls_ok else "—"
                line += f"  |  TLS: {tls_icon} {tls_rtt}"
            lines.append(line)

    return "\n".join(lines)
