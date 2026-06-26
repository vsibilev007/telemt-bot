"""
Проверка MTProto прокси — на основе check_tg_proxy.

Проверки: TCP, TLS, MTProto (raw), стабильность, DPI-детекция, DNS.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import socket
import ssl
import struct
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional


# ─── Данные ───────────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    success: bool = False
    rtt_ms: float = 0.0
    error: str = ""
    error_type: str = ""
    detail: str = ""


@dataclass
class StabilityResult:
    total: int = 0
    success: int = 0
    success_rate: float = 0.0
    avg_rtt_ms: float = 0.0
    min_rtt_ms: float = 0.0
    max_rtt_ms: float = 0.0
    jitter_ms: float = 0.0
    pattern: str = "unknown"


@dataclass
class DpiResult:
    sni_filtering: Optional[bool] = None
    http_probe_responds: bool = False
    http_is_web: bool = False
    rst_detected: bool = False


@dataclass
class DnsResult:
    system_ips: list[str] = field(default_factory=list)
    consistent: bool = True
    direct_ip: bool = False


@dataclass
class AgentResult:
    label: str = ""
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
    raw_url: str = ""
    # Результаты проверок
    tcp: CheckResult = field(default_factory=CheckResult)
    tls: CheckResult = field(default_factory=CheckResult)
    mtproto: CheckResult = field(default_factory=CheckResult)
    stability: StabilityResult = field(default_factory=StabilityResult)
    dpi: DpiResult = field(default_factory=DpiResult)
    dns: DnsResult = field(default_factory=DnsResult)
    server_info: dict = field(default_factory=dict)
    # Агенты
    agents: list[AgentResult] = field(default_factory=list)
    # Время
    check_time_ms: float = 0.0

    # Алиасы
    @property
    def reachable(self) -> bool:
        return self.tcp.success

    @property
    def mtproto_ok(self) -> bool:
        return self.mtproto.success

    @property
    def rtt_ms(self) -> float:
        return self.tcp.rtt_ms

    @property
    def eu_tcp_ok(self) -> bool:
        return self.tcp.success

    @property
    def eu_tcp_rtt(self) -> float:
        return self.tcp.rtt_ms

    @property
    def eu_mtproto_ok(self) -> bool:
        return self.mtproto.success

    @property
    def eu_mtproto_rtt(self) -> float:
        return self.mtproto.rtt_ms


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


# ─── Классификация ошибок ────────────────────────────────────────────────────

def _classify_tcp_error(e: Exception) -> str:
    msg = str(e).lower()
    if isinstance(e, asyncio.TimeoutError):
        return "timeout"
    if isinstance(e, ConnectionRefusedError):
        return "connection_refused"
    if isinstance(e, ConnectionResetError) or "reset" in msg:
        return "connection_reset"
    if "unreachable" in msg or "network" in msg:
        return "network_unreachable"
    if "no route" in msg:
        return "no_route"
    if "name or service not known" in msg or "getaddrinfo" in msg:
        return "dns_error"
    return str(e)[:80]


def _classify_tls_error(e: Exception) -> str:
    msg = str(e).lower()
    if isinstance(e, asyncio.TimeoutError):
        return "timeout"
    if isinstance(e, ConnectionResetError) or "reset" in msg:
        return "connection_reset"
    if isinstance(e, ssl.SSLError):
        if "eof" in msg or "unexpected eof" in msg:
            return "unexpected_eof"
        if "handshake" in msg:
            return "handshake_failure"
        if "certificate" in msg:
            return "certificate_error"
        if "alert" in msg:
            return "tls_alert"
        return f"ssl_error"
    if isinstance(e, ConnectionRefusedError):
        return "connection_refused"
    if isinstance(e, OSError) and ("timed out" in msg or "timeout" in msg):
        return "timeout"
    return str(e)[:80]


# ─── TCP проверка ─────────────────────────────────────────────────────────────

async def check_tcp(host: str, port: int, timeout: float = 10) -> CheckResult:
    start = time.monotonic()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout,
        )
        rtt = (time.monotonic() - start) * 1000
        writer.close()
        await writer.wait_closed()
        return CheckResult(success=True, rtt_ms=round(rtt, 1))
    except Exception as e:
        return CheckResult(
            success=False, error=str(e)[:100],
            error_type=_classify_tcp_error(e),
        )


# ─── TLS проверка ─────────────────────────────────────────────────────────────

async def check_tls(host: str, port: int, sni: str, timeout: float = 10) -> CheckResult:
    if not sni:
        return CheckResult(success=False, error="no SNI available")

    start = time.monotonic()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ctx, server_hostname=sni),
            timeout=timeout,
        )
        rtt = (time.monotonic() - start) * 1000
        writer.close()
        await writer.wait_closed()
        return CheckResult(success=True, rtt_ms=round(rtt, 1))
    except Exception as e:
        return CheckResult(
            success=False, error=str(e)[:100],
            error_type=_classify_tls_error(e),
        )


# ─── MTProto проверка (raw) ──────────────────────────────────────────────────

async def check_mtproto(host: str, port: int, secret_hex: str, timeout: float = 10) -> CheckResult:
    start = time.monotonic()
    try:
        secret_bytes = bytes.fromhex(secret_hex)
    except ValueError:
        # Пробуем base64url
        try:
            pad = secret_hex + "=" * (-len(secret_hex) % 4)
            import base64
            secret_bytes = base64.urlsafe_b64decode(pad)
        except Exception:
            return CheckResult(success=False, error="invalid secret")

    if len(secret_bytes) < 17:
        return CheckResult(success=False, error="secret too short")

    tag = secret_bytes[0]
    key_secret = secret_bytes[1:17]

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout,
        )
    except asyncio.TimeoutError:
        return CheckResult(success=False, error="tcp timeout", error_type="timeout")
    except Exception as e:
        return CheckResult(success=False, error=str(e)[:100], error_type=_classify_tcp_error(e))

    try:
        init_payload = _build_obfuscated_init(key_secret, tag)
        writer.write(init_payload)
        await writer.drain()
        connect_rtt = (time.monotonic() - start) * 1000

        try:
            data = await asyncio.wait_for(reader.read(128), timeout=3)
            rtt = (time.monotonic() - start) * 1000
            if data:
                return CheckResult(success=True, rtt_ms=round(connect_rtt, 1), detail="responded")
            else:
                elapsed_after_send = rtt - connect_rtt
                if elapsed_after_send > 1000:
                    return CheckResult(success=True, rtt_ms=round(connect_rtt, 1), detail="kept_alive")
                return CheckResult(success=False, rtt_ms=round(connect_rtt, 1), error="init rejected", detail="closed")
        except asyncio.TimeoutError:
            return CheckResult(success=True, rtt_ms=round(connect_rtt, 1), detail="kept_alive")

    except ConnectionResetError:
        rtt = (time.monotonic() - start) * 1000
        return CheckResult(success=False, rtt_ms=round(rtt, 1), error="connection reset")
    except Exception as e:
        rtt = (time.monotonic() - start) * 1000
        return CheckResult(success=False, rtt_ms=round(rtt, 1), error=str(e)[:100])
    finally:
        writer.close()
        await writer.wait_closed()


def _build_obfuscated_init(key_secret: bytes, tag: int) -> bytes:
    while True:
        nonce = os.urandom(64)
        if nonce[0] == 0xEF:
            continue
        first_int = struct.unpack("<I", nonce[:4])[0]
        if first_int in (0x44414548, 0x54534F50, 0x20544547, 0x4954504F,
                         0xDDDDDDDD, 0xEEEEEEEE, 0x02010316):
            continue
        if nonce[:4] == b'\x16\x03\x01\x02':
            continue
        break

    nonce = bytearray(nonce)

    if tag == 0xDD:
        nonce[56:60] = b'\xdd\xdd\xdd\xdd'
    elif tag == 0xEE:
        nonce[56:60] = b'\xef\xef\xef\xef'
    else:
        nonce[56:60] = b'\xef\xef\xef\xef'

    enc_key_data = bytes(nonce[8:40]) + key_secret
    enc_key = hashlib.sha256(enc_key_data).digest()
    enc_iv = bytes(nonce[40:56])

    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    enc_cipher = Cipher(algorithms.AES(enc_key), modes.CTR(enc_iv))
    encryptor = enc_cipher.encryptor()

    encrypted_part = encryptor.update(bytes(nonce[56:64]))
    result = bytearray(nonce)
    result[56:64] = encrypted_part

    return bytes(result)


# ─── Стабильность ────────────────────────────────────────────────────────────

async def check_stability(host: str, port: int, count: int = 10, delay: float = 0.3) -> StabilityResult:
    results = []

    async def _single_connect():
        start = time.monotonic()
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=5,
            )
            rtt = (time.monotonic() - start) * 1000
            writer.close()
            await writer.wait_closed()
            return True, round(rtt, 1)
        except asyncio.TimeoutError:
            return False, 0
        except Exception:
            return False, 0

    for i in range(count):
        ok, rtt = await _single_connect()
        results.append((ok, rtt))
        if i < count - 1:
            await asyncio.sleep(delay)

    success = sum(1 for ok, _ in results if ok)
    rtts = [rtt for ok, rtt in results if ok]
    avg_rtt = round(sum(rtts) / len(rtts), 1) if rtts else 0
    min_rtt = round(min(rtts), 1) if rtts else 0
    max_rtt = round(max(rtts), 1) if rtts else 0
    jitter = round(max_rtt - min_rtt, 1) if rtts else 0

    pattern = "stable"
    if success == 0:
        pattern = "blocked"
    elif success < count:
        pattern = "unstable"

    return StabilityResult(
        total=count, success=success,
        success_rate=round(success / count * 100),
        avg_rtt_ms=avg_rtt, min_rtt_ms=min_rtt,
        max_rtt_ms=max_rtt, jitter_ms=jitter,
        pattern=pattern,
    )


# ─── DPI-детекция ─────────────────────────────────────────────────────────────

async def _try_tls_connect(host: str, port: int, sni: str) -> dict:
    start = time.monotonic()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ctx, server_hostname=sni),
            timeout=8,
        )
        rtt = (time.monotonic() - start) * 1000
        writer.close()
        await writer.wait_closed()
        return {"ok": True, "rtt_ms": round(rtt, 1)}
    except asyncio.TimeoutError:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:80]}


async def _http_probe(host: str, port: int, sni: str = "") -> dict:
    hostname = sni or host
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=5,
        )
        writer.write(f"GET / HTTP/1.1\r\nHost: {hostname}\r\nConnection: close\r\n\r\n".encode())
        await writer.drain()
        data = await asyncio.wait_for(reader.read(1024), timeout=5)
        writer.close()
        await writer.wait_closed()
        response = data[:200].decode("utf-8", errors="replace")
        is_http = response.startswith("HTTP/")
        return {"responds": True, "is_http": is_http, "snippet": response[:100]}
    except asyncio.TimeoutError:
        return {"responds": False, "is_http": False, "snippet": ""}
    except Exception as e:
        return {"responds": False, "is_http": False, "snippet": str(e)[:100]}


async def check_dpi(host: str, port: int, sni: str) -> DpiResult:
    result = DpiResult()

    if sni:
        # Проверяем разные SNI-профили
        profiles = {
            "correct": sni,
            "cdn": "www.google.com",
            "nonexistent": "rand-check.invalid",
        }
        sni_results = {}
        for name, test_sni in profiles.items():
            sni_results[name] = await _try_tls_connect(host, port, test_sni)

        correct_ok = sni_results["correct"]["ok"]
        cdn_ok = sni_results["cdn"]["ok"]
        nonexist_ok = sni_results["nonexistent"]["ok"]

        if correct_ok and cdn_ok and nonexist_ok:
            result.sni_filtering = False
        elif not correct_ok and cdn_ok:
            result.sni_filtering = True
        elif not correct_ok and not cdn_ok and not nonexist_ok:
            result.sni_filtering = None
        else:
            result.sni_filtering = "partial"

    # HTTP-проба
    http_result = await _http_probe(host, port, sni)
    result.http_probe_responds = http_result.get("responds", False)
    result.http_is_web = http_result.get("is_http", False)

    return result


# ─── DNS проверка ─────────────────────────────────────────────────────────────

def _is_ip(host: str) -> bool:
    try:
        socket.inet_aton(host)
        return True
    except OSError:
        return False


async def check_dns(host: str) -> DnsResult:
    result = DnsResult()

    if _is_ip(host):
        result.direct_ip = True
        result.system_ips = [host]
        return result

    try:
        loop = asyncio.get_running_loop()
        res = await asyncio.wait_for(
            loop.getaddrinfo(host, None, family=socket.AF_INET),
            timeout=3,
        )
        result.system_ips = list(dict.fromkeys(r[4][0] for r in res))
    except Exception:
        result.system_ips = []

    return result


# ─── GeoIP ───────────────────────────────────────────────────────────────────

_COUNTRY_FLAGS: dict[str, str] = {
    "RU": "🇷🇺", "US": "🇺🇸", "DE": "🇩🇪", "FR": "🇫🇷",
    "GB": "🇬🇧", "NL": "🇳🇱", "FI": "🇫🇮", "SE": "🇸🇪",
    "PL": "🇵🇱", "UA": "🇺🇦", "BY": "🇧🇾", "KZ": "🇰🇿",
    "TR": "🇹🇷", "JP": "🇯🇵", "KR": "🇰🇷", "SG": "🇸🇬",
    "CA": "🇨🇦", "AU": "🇦🇺", "BR": "🇧🇷", "IN": "🇮🇳",
    "LV": "🇱🇻", "LT": "🇱🇹", "EE": "🇪🇪", "CZ": "🇨🇿",
    "AT": "🇦🇹", "CH": "🇨🇭", "IT": "🇮🇹", "ES": "🇪🇸",
    "PT": "🇵🇹", "RO": "🇷🇴", "HU": "🇭🇺", "BG": "🇧🇬",
    "RS": "🇷🇸", "SK": "🇸🇰", "MD": "🇲🇩", "AM": "🇦🇲",
    "GE": "🇬🇪", "AZ": "🇦🇿", "UZ": "🇺🇿", "IL": "🇮🇱",
    "AE": "🇦🇪", "CY": "🇨🇾", "CN": "🇨🇳", "HK": "🇭🇰",
    "ID": "🇮🇩", "TH": "🇹🇭", "VN": "🇻🇳", "MY": "🇲🇾",
    "PH": "🇵🇭", "BD": "🇧🇩", "PK": "🇵🇰", "NG": "🇳🇬",
    "ZA": "🇿🇦", "EG": "🇪🇬", "KE": "🇰🇪", "AR": "🇦🇷",
    "CL": "🇨🇱", "CO": "🇨🇴", "PE": "🇵🇪", "MX": "🇲🇽",
}

_geoip_cache: dict[str, str] = {}


async def get_server_info(host: str) -> dict:
    """Получить информацию о сервере через ip-api.com."""
    if _is_ip(host):
        return {"ip": host, "country": "", "city": "", "org": ""}

    try:
        # Сначала резолвим
        loop = asyncio.get_running_loop()
        res = await asyncio.wait_for(
            loop.getaddrinfo(host, None, family=socket.AF_INET),
            timeout=3,
        )
        ip = res[0][4][0] if res else host
    except Exception:
        ip = host

    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,org,as",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                data = await resp.json()
                if data.get("status") == "success":
                    return {
                        "ip": ip,
                        "country": data.get("country", ""),
                        "country_code": data.get("countryCode", ""),
                        "city": data.get("city", ""),
                        "org": data.get("org", ""),
                        "asn": data.get("as", ""),
                    }
    except Exception:
        pass

    return {"ip": ip, "country": "", "city": "", "org": ""}


# ─── Агенты ───────────────────────────────────────────────────────────────────

async def _check_via_agent(
    info: ProxyInfo,
    agent_url: str,
    agent_token: str,
    label: str,
    timeout: float = 12.0,
) -> AgentResult:
    result = AgentResult(label=label)
    try:
        import aiohttp
        url = f"{agent_url.rstrip('/')}/check"
        params = {"host": info.server, "port": info.port, "sni": info.sni}
        headers = {"X-Token": agent_token} if agent_token else {}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params=params, headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                data = await resp.json()
                tcp = data.get("tcp", {})
                tls = data.get("tls") or {}
                result.tcp_ok = tcp.get("ok", False)
                result.tcp_rtt = tcp.get("rtt_ms", 0.0)
                result.tls_ok = tls.get("ok", False)
                result.tls_rtt = tls.get("rtt_ms", 0.0)
                if not result.tcp_ok:
                    result.tcp_error = tcp.get("error", "недоступен")[:60]
    except Exception as e:
        result.tcp_ok = False
        result.tcp_error = str(e)[:60]
    return result


async def _resolve_agent_label(agent_url: str, flag: str = "", name: str = "") -> str:
    if flag:
        return f"{flag} {name}" if name else flag
    try:
        parsed = urllib.parse.urlparse(agent_url)
        host = parsed.hostname or ""
    except Exception:
        host = ""
    if not host:
        return f"🌐 {name}" if name else "🌐"
    if host in _geoip_cache:
        return _geoip_cache[host]
    try:
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"http://ip-api.com/json/{host}?fields=countryCode",
                timeout=aiohttp.ClientTimeout(total=3),
            ) as resp:
                data = await resp.json()
                cc = data.get("countryCode", "")
                emoji = _COUNTRY_FLAGS.get(cc, "🌐")
                label = f"{emoji} {name}" if name else f"{emoji} {cc}"
                _geoip_cache[host] = label
                return label
    except Exception:
        label = f"🌐 {name}" if name else "🌐"
        _geoip_cache[host] = label
        return label


# ─── Полная проверка узла ─────────────────────────────────────────────────────

async def check_node_full(info: ProxyInfo, timeout: float = 5.0, agents=None) -> ProxyInfo:
    """Полная проверка узла: TCP + TLS + MTProto + стабильность + DPI + DNS + GeoIP + агенты."""
    start_total = time.monotonic()

    # Параллельно: TCP, TLS, DNS, GeoIP
    tcp_task = asyncio.create_task(check_tcp(info.server, info.port, timeout))
    tls_task = asyncio.create_task(check_tls(info.server, info.port, info.sni, timeout)) if info.sni else None
    dns_task = asyncio.create_task(check_dns(info.server))
    geoip_task = asyncio.create_task(get_server_info(info.server))

    info.tcp = await tcp_task
    info.tls = await tls_task if tls_task else CheckResult(success=False, error="no SNI")
    info.dns = await dns_task
    info.server_info = await geoip_task

    # MTProto (если TCP доступен и есть секрет)
    if info.tcp.success and info.secret:
        info.mtproto = await check_mtproto(info.server, info.port, info.secret, timeout=10)

    # Стабильность (5 проверок вместо 10 для скорости)
    if info.tcp.success:
        info.stability = await check_stability(info.server, info.port, count=5, delay=0.3)

    # DPI-детекция (если TCP доступен)
    if info.tcp.success and info.sni:
        info.dpi = await check_dpi(info.server, info.port, info.sni)

    # Агенты
    if agents:
        agent_labels = await asyncio.gather(*[
            _resolve_agent_label(a.url, a.flag, a.name) for a in agents
        ])
        agent_results = await asyncio.gather(*[
            _check_via_agent(info, a.url, a.token, label)
            for a, label in zip(agents, agent_labels)
        ])
        info.agents = list(agent_results)

    info.check_time_ms = (time.monotonic() - start_total) * 1000

    return info


# ─── Простая проверка (для кнопки «Проверить прокси») ─────────────────────────

async def check_proxy(info: ProxyInfo, timeout: float = 5.0, agents=None) -> ProxyInfo:
    """Простая проверка: TCP + MTProto + агенты."""
    start = time.monotonic()

    # TCP
    info.tcp = await check_tcp(info.server, info.port, timeout)

    # MTProto
    if info.tcp.success and info.secret:
        info.mtproto = await check_mtproto(info.server, info.port, info.secret, timeout=20)

    # Агенты
    if agents:
        agent_labels = await asyncio.gather(*[
            _resolve_agent_label(a.url, a.flag, a.name) for a in agents
        ])
        agent_results = await asyncio.gather(*[
            _check_via_agent(info, a.url, a.token, label)
            for a, label in zip(agents, agent_labels)
        ])
        info.agents = list(agent_results)

    info.check_time_ms = (time.monotonic() - start) * 1000
    return info


# ─── Форматирование (простое) ────────────────────────────────────────────────

def format_proxy_result(info: ProxyInfo) -> str:
    type_labels = {
        "faketls": "🛡 FakeTLS",
        "dd": "🔵 DD",
        "simple": "⚪ Simple",
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

    tcp_icon = "🟢" if info.tcp.success else "🔴"
    tcp_rtt = f"{info.tcp.rtt_ms:.0f} мс" if info.tcp.success else (info.tcp.error or "—")
    lines.append(f"  {tcp_icon} TCP ({info.port}): {tcp_rtt}")

    if info.mtproto.success:
        lines.append(f"  🟢 MTProto: {info.mtproto.rtt_ms:.0f} мс")
    elif info.tcp.success:
        lines.append(f"  🔴 MTProto: {info.mtproto.error or 'недоступен'}")

    for ar in info.agents:
        tcp_icon = "🟢" if ar.tcp_ok else "🔴"
        tcp_rtt = f"{ar.tcp_rtt:.0f} мс" if ar.tcp_ok else f"<i>{ar.tcp_error or '—'}</i>"
        line = f"  {ar.label} — TCP: {tcp_icon} {tcp_rtt}"
        if ar.tcp_ok:
            tls_icon = "🟢" if ar.tls_ok else "🔴"
            tls_rtt = f"{ar.tls_rtt:.0f} мс" if ar.tls_ok else "—"
            line += f"  |  TLS: {tls_icon} {tls_rtt}"
        lines.append(line)

    if not info.tcp.success and info.tcp.error:
        lines += ["", f"❌ <b>Ошибка:</b> <code>{info.tcp.error}</code>"]

    return "\n".join(lines)


# ─── Форматирование (расширенное) ────────────────────────────────────────────

def format_node_result(info: ProxyInfo) -> str:
    """Форматирует результат полной диагностики узла."""
    # Итоговый статус
    if info.mtproto.success:
        status = "OK"
        status_icon = "✅"
    elif info.tcp.success:
        status = "PARTIAL"
        status_icon = "🟡"
    else:
        status = "FAIL"
        status_icon = "❌"

    lines = [
        f"{status_icon} <b>Проверка узла {info.server}</b>",
        "",
    ]

    # GeoIP
    gi = info.server_info
    if gi and gi.get("country"):
        flag = _COUNTRY_FLAGS.get(gi.get("country_code", ""), "🌐")
        loc = f"{gi.get('city', '')}, {gi.get('country', '')}" if gi.get("city") else gi.get("country", "")
        org = gi.get("org", "")
        line = f"  📍 {flag} {loc}"
        if org:
            line += f" — <i>{org}</i>"
        lines.append(line)
        lines.append("")

    # ─── Проверка с сервера (бот) ──────────────────────────────────────────────
    lines.append("<b>🖥 Сервер (бот):</b>")

    # TCP
    tcp_icon = "✅" if info.tcp.success else "❌"
    tcp_text = f"{info.tcp.rtt_ms:.0f} мс" if info.tcp.success else (info.tcp.error_type or "недоступен")
    lines.append(f"  {tcp_icon} TCP ({info.port}): {tcp_text}")

    # TLS
    if info.sni:
        tls_icon = "✅" if info.tls.success else ("⚠️" if info.tls.success is None else "❌")
        tls_text = f"{info.tls.rtt_ms:.0f} мс" if info.tls.success else (info.tls.error_type or "—")
        lines.append(f"  {tls_icon} TLS ({info.sni}): {tls_text}")

    # MTProto
    if info.mtproto.success:
        lines.append(f"  ✅ MTProto: {info.mtproto.rtt_ms:.0f} мс ({info.mtproto.detail})")
    elif info.tcp.success:
        lines.append(f"  ❌ MTProto: {info.mtproto.error or 'недоступен'}")

    # Стабильность
    if info.stability.total > 0:
        stab_icon = "✅" if info.stability.pattern == "stable" else ("⚠️" if info.stability.pattern == "unstable" else "❌")
        lines.append(f"  {stab_icon} Стабильность: {info.stability.success}/{info.stability.total} ({info.stability.success_rate}%) — {info.stability.pattern}")

    # DPI
    if info.dpi.sni_filtering is not None:
        dpi_icon = "✅" if not info.dpi.sni_filtering else "⚠️"
        lines.append(f"  {dpi_icon} DPI-фильтрация SNI: {'да' if info.dpi.sni_filtering else 'нет'}")

    # ─── Агенты ────────────────────────────────────────────────────────────────
    if info.agents:
        lines.append("")
        lines.append("<b>📡 Агенты:</b>")
        for ar in info.agents:
            tcp_icon = "🟢" if ar.tcp_ok else "🔴"
            tcp_rtt = f"{ar.tcp_rtt:.0f} мс" if ar.tcp_ok else f"<i>{ar.tcp_error or '—'}</i>"
            lines.append(f"  <b>{ar.label}</b>")
            lines.append(f"    TCP: {tcp_icon} {tcp_rtt}")
            if ar.tcp_ok:
                tls_icon = "🟢" if ar.tls_ok else "🔴"
                tls_rtt = f"{ar.tls_rtt:.0f} мс" if ar.tls_ok else "—"
                lines.append(f"    TLS: {tls_icon} {tls_rtt}")

    # Диагностика
    parts = []
    if info.mtproto.success:
        parts.append("MTProto доступен")
    if info.tcp.success:
        if info.mtproto.success:
            parts.append("сервис отвечает штатно")
        else:
            parts.append("TCP доступен, но MTProto не работает")
    if not parts:
        parts.append("нет соединения с узлом")

    lines.append("")
    lines.append(f"  {'✅' if info.mtproto.success else '⚠️'} Диагностика: {', '.join(parts)}")
    lines.append(f"  ⏱ Время проверки: {info.check_time_ms:.0f} ms")
    lines.append(f"  {status_icon} Итоговый статус: {status}")

    return "\n".join(lines)
