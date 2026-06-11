"""
Системная информация о сервере где запущен бот
"""

from __future__ import annotations

import asyncio
import os
import socket
import time
from datetime import datetime, timezone

import psutil
import tz as _tz


def _sys_now_str() -> str:
    return _tz.now_str()


def _fmt_bytes(b: int) -> str:
    for unit, thr in [("TB", 1 << 40), ("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)]:
        if b >= thr:
            return f"{b / thr:.2f} {unit}"
    return f"{b} B"


def _fmt_uptime(seconds: float) -> str:
    s = int(seconds)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts = []
    if d: parts.append(f"{d} дн")
    if h: parts.append(f"{h} ч")
    if m: parts.append(f"{m} мин")
    if not d: parts.append(f"{s} сек")
    return " ".join(parts)


async def get_system_info() -> dict:
    """Собирает системную информацию — запускается в executor чтобы не блокировать event loop"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _collect_sync)


def _collect_sync() -> dict:
    # CPU
    cpu_pct = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count()
    load1, load5, load15 = os.getloadavg()

    # RAM
    mem = psutil.virtual_memory()

    # Диск (корень)
    disk = psutil.disk_usage("/")

    # Сеть — суммарно
    net = psutil.net_io_counters()

    # Uptime
    boot_ts = psutil.boot_time()
    uptime_secs = time.time() - boot_ts

    # Hostname + IP
    hostname = socket.gethostname()
    try:
        ipv4 = socket.gethostbyname(hostname)
    except Exception:
        ipv4 = "—"

    # Все IP интерфейсов (кроме loopback)
    ips = []
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                ips.append(addr.address)

    # TCP/UDP соединения
    try:
        conns = psutil.net_connections()
        tcp_count = sum(1 for c in conns if c.type.name == "SOCK_STREAM")
        udp_count = sum(1 for c in conns if c.type.name == "SOCK_DGRAM")
    except Exception:
        tcp_count = udp_count = 0

    # Процессы
    proc_count = len(psutil.pids())

    # Температура CPU (если доступна)
    temp_str = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    temp_str = f"{entries[0].current:.0f}°C"
                    break
    except Exception:
        pass

    return {
        "hostname": hostname,
        "ips": ips,
        "uptime_secs": uptime_secs,
        "cpu_pct": cpu_pct,
        "cpu_count": cpu_count,
        "load1": load1,
        "load5": load5,
        "load15": load15,
        "mem_used": mem.used,
        "mem_total": mem.total,
        "mem_pct": mem.percent,
        "disk_used": disk.used,
        "disk_total": disk.total,
        "disk_pct": disk.percent,
        "net_sent": net.bytes_sent,
        "net_recv": net.bytes_recv,
        "tcp_count": tcp_count,
        "udp_count": udp_count,
        "proc_count": proc_count,
        "temp": temp_str,
    }


def format_system_status(info: dict, telemt_status: str = "unknown", telemt_conns: int = 0) -> str:
    """Форматирует системный статус в стиле скриншота"""

    uptime = _fmt_uptime(info["uptime_secs"])
    ips_str = "  ".join(info["ips"][:4]) if info["ips"] else "—"
    hostname = info["hostname"]

    mem_used = _fmt_bytes(info["mem_used"])
    mem_total = _fmt_bytes(info["mem_total"])
    mem_pct = info["mem_pct"]

    disk_used = _fmt_bytes(info["disk_used"])
    disk_total = _fmt_bytes(info["disk_total"])
    disk_pct = info["disk_pct"]

    net_sent = _fmt_bytes(info["net_sent"])
    net_recv = _fmt_bytes(info["net_recv"])

    cpu_pct = info["cpu_pct"]
    load = f"{info['load1']:.2f}, {info['load5']:.2f}, {info['load15']:.2f}"

    # Иконки состояния
    telemt_icon = "🟢" if telemt_status == "ok" else ("🔴" if telemt_status == "unreachable" else "🟡")

    mem_icon = "🟢" if mem_pct < 70 else ("🟡" if mem_pct < 85 else "🔴")
    disk_icon = "🟢" if disk_pct < 75 else ("🟡" if disk_pct < 90 else "🔴")
    cpu_icon = "🟢" if cpu_pct < 60 else ("🟡" if cpu_pct < 85 else "🔴")

    lines = [
        f"🖥 Имя хоста: <code>{hostname}</code>",
        f"🌐 IPv4: <code>{ips_str}</code>",
        f"⏳ Время работы: {uptime}",
        "",
        f"{cpu_icon} CPU: {cpu_pct:.1f}%  |  Ядер: {info['cpu_count']}",
        f"📊 Нагрузка: {load}",
        f"{mem_icon} ОЗУ: {mem_used} / {mem_total} ({mem_pct:.0f}%)",
        f"{disk_icon} Диск: {disk_used} / {disk_total} ({disk_pct:.0f}%)",
        "",
        f"🔵 TCP соединений: {info['tcp_count']}",
        f"🔶 UDP соединений: {info['udp_count']}",
        f"⚙️ Процессов: {info['proc_count']}",
        f"🌍 Трафик: ↑{net_sent}  ↓{net_recv}",
    ]

    if info.get("temp"):
        lines.append(f"🌡 Температура CPU: {info['temp']}")

    lines += [
        "",
        f"{telemt_icon} Состояние Telemt: <b>{telemt_status}</b>",
        f"👥 Всего принятых подключений: <b>{telemt_conns}</b>",
        "",
        f"<i>🕐 Обновлено: {_sys_now_str()}</i>",
    ]

    return "\n".join(lines)
