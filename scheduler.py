"""
Фоновые задачи: мониторинг, сбор трафика, алерты
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from functools import wraps

import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from api_client import TelemetClient, ApiError
from config import Config, AlertThresholds
import database as db

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_bot = None
_config: Config | None = None

DB_PATH = db.DB_PATH


# ─── Декоратор: защищённый запуск джобы ─────────────────────────────────────

def safe_job(name: str):
    """Оборачивает джобу в try/except — исключение логируется, задача не умирает."""
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                logger.error("Джоба [%s] упала с ошибкой: %s", name, e, exc_info=True)
        return wrapper
    return decorator


# ─── Setup ──────────────────────────────────────────────────────────────────

def setup(bot, config: Config):
    global _scheduler, _bot, _config
    _bot = bot
    _config = config
    _scheduler = AsyncIOScheduler(timezone="UTC")

    _scheduler.add_job(
        _collect_traffic,
        IntervalTrigger(minutes=15),
        id="collect_traffic",
        replace_existing=True,
    )
    _scheduler.add_job(
        _check_health,
        IntervalTrigger(minutes=2),
        id="check_health",
        replace_existing=True,
    )
    _scheduler.add_job(
        _cleanup,
        IntervalTrigger(hours=24),
        id="cleanup",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler запущен (3 задачи)")


def stop():
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler остановлен")


# ─── DB helpers ─────────────────────────────────────────────────────────────

async def _get_meta(server_name: str, key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute(
            "SELECT value FROM server_meta WHERE server_name=? AND key=?",
            (server_name, key),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def _set_meta(server_name: str, key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """INSERT INTO server_meta(server_name, key, value)
               VALUES(?,?,?)
               ON CONFLICT(server_name, key) DO UPDATE SET value=excluded.value""",
            (server_name, key, value),
        )
        await conn.commit()


# ─── Tasks ──────────────────────────────────────────────────────────────────

@safe_job("collect_traffic")
async def _collect_traffic():
    if not _config:
        return
    for srv in _config.servers:
        try:
            client = TelemetClient(srv.url, srv.auth_header)
            users = await client.get_users()
            if users:
                await db.save_traffic_snapshot(srv.name, users)

                # Алерт: клиент превысил 80% квоты
                thr = _config.thresholds
                for u in users:
                    quota = u.get("data_quota_bytes", 0)
                    used = u.get("total_octets", 0)
                    if quota and quota > 0:
                        pct = used / quota * 100
                        if pct >= thr.quota_alert_pct:
                            await _fire_alert(
                                srv.name, "quota_warn",
                                f"📊 <b>{srv.name}</b> — клиент <code>{u['username']}</code> "
                                f"использовал {pct:.0f}% квоты "
                                f"({_fmt_bytes(used)} / {_fmt_bytes(quota)})",
                                cooldown=3600,
                            )

                logger.debug("Трафик собран: %s (%d users)", srv.name, len(users))
        except ApiError as e:
            logger.warning("API ошибка сбора трафика [%s]: %s", srv.name, e)
        except Exception as e:
            logger.warning("Ошибка сбора трафика [%s]: %s", srv.name, e)


@safe_job("check_health")
async def _check_health():
    if not _config or not _bot:
        return

    for srv in _config.servers:
        try:
            client = TelemetClient(srv.url, srv.auth_header)
            health = await client.get_health()
            summary = await client.get_stats_summary()

            status = health.get("status", "unknown")
            connections = summary.get("connections_total", 0)

            prev = await db.get_server_status(srv.name)
            await db.update_server_status(srv.name, status, connections)

            thr = _config.thresholds

            # Статус упал
            if prev and prev["status"] == "ok" and status != "ok":
                await _fire_alert(
                    srv.name, "status_down",
                    f"🔴 <b>{srv.name}</b> — статус изменился: <b>{status}</b>",
                )

            # Статус восстановился
            if prev and prev["status"] != "ok" and status == "ok":
                await _fire_alert(
                    srv.name, "status_up",
                    f"🟢 <b>{srv.name}</b> — статус восстановлен: <b>OK</b>",
                    cooldown=0,
                )

            # Всплеск соединений
            if prev and prev["connections"] > thr.conn_spike_min_base:
                delta_pct = (connections - prev["connections"]) / prev["connections"] * 100
                if delta_pct > thr.conn_spike_pct:
                    await _fire_alert(
                        srv.name, "conn_spike",
                        f"⚡ <b>{srv.name}</b> — всплеск соединений: "
                        f"{prev['connections']:,} → {connections:,} (+{delta_pct:.0f}%)",
                    )

            # ME Writers coverage
            try:
                writers = await client.get_stats_me_writers()
                coverage = writers.get("summary", {}).get("coverage_pct", 100)
                if coverage < thr.writers_low_pct:
                    await _fire_alert(
                        srv.name, "writers_low",
                        f"⚠️ <b>{srv.name}</b> — ME Writers coverage: {coverage:.0f}%",
                    )
            except Exception:
                pass

            # Версия изменилась
            try:
                sysinfo = await client.get_system_info()
                version = sysinfo.get("version", "")
                if version:
                    prev_version = await _get_meta(srv.name, "version")
                    await _set_meta(srv.name, "version", version)
                    if prev_version and prev_version != version:
                        await _fire_alert(
                            srv.name, "version_change",
                            f"🏷 <b>{srv.name}</b> — обновление telemt: "
                            f"<b>v{prev_version}</b> → <b>v{version}</b>",
                            cooldown=0,
                        )
            except Exception:
                pass

            # Счётчики bad/handshake классов
            try:
                bad_by_class = {
                    e["class"]: e["total"]
                    for e in summary.get("connections_bad_by_class", [])
                }
                hs_by_class = {
                    e["class"]: e["total"]
                    for e in summary.get("handshake_failures_by_class", [])
                }
                current_counters = {**bad_by_class, **hs_by_class}
                prev_raw = await _get_meta(srv.name, "counters")
                prev_counters = json.loads(prev_raw) if prev_raw else {}
                await _set_meta(srv.name, "counters", json.dumps(current_counters))


                if prev_counters:
                    def delta(key: str) -> int:
                        return current_counters.get(key, 0) - prev_counters.get(key, 0)

                    d_sni = delta("unknown_tls_sni")
                    if d_sni > 0:
                        await _fire_alert(
                            srv.name, "bad_unknown_sni",
                            f"⚠️ <b>{srv.name}</b> — неизвестный SNI: +{d_sni} за 2 мин",
                            cooldown=300,
                        )

                    d_hs = delta("timeout")
                    if d_hs >= thr.hs_timeout_spike:
                        await _fire_alert(
                            srv.name, "hs_timeout_spike",
                            f"⚠️ <b>{srv.name}</b> — всплеск handshake timeout: +{d_hs} за 2 мин",
                            cooldown=120,
                        )

                    d_bad = delta("tls_handshake_bad_client")
                    if d_bad >= thr.bad_client_spike:
                        await _fire_alert(
                            srv.name, "bad_client_spike",
                            f"⚠️ <b>{srv.name}</b> — всплеск плохих TLS клиентов: +{d_bad} за 2 мин",
                            cooldown=120,
                        )

                    d_reset = delta("expected_64_got_0_connection_reset")
                    if d_reset > 0:
                        await _fire_alert(
                            srv.name, "hs_conn_reset",
                            f"⚠️ <b>{srv.name}</b> — сброс соединений при handshake: +{d_reset} за 2 мин",
                            cooldown=300,
                        )
            except Exception:
                pass

        except Exception as e:
            prev = await db.get_server_status(srv.name)
            if not prev or prev["status"] != "unreachable":
                await db.update_server_status(srv.name, "unreachable", 0)
                await _fire_alert(
                    srv.name, "status_down",
                    f"🔴 <b>{srv.name}</b> — сервер недоступен: {type(e).__name__}: {e}",
                    cooldown=300,
                )
            logger.warning("Ошибка проверки [%s]: %s", srv.name, e)


@safe_job("cleanup")
async def _cleanup():
    await db.cleanup_old_data(days=30)
    logger.info("Очистка старых данных выполнена")


# ─── Alert dispatcher ────────────────────────────────────────────────────────

async def _fire_alert(
    server_name: str, alert_type: str, message: str, cooldown: int = 120
):
    if cooldown > 0 and await db.was_alert_fired_recently(server_name, alert_type, cooldown):
        return

    await db.log_alert(server_name, alert_type, message)

    if not _bot or not _config:
        return

    for user_id in _config.allowed_users:
        try:
            enabled = await db.get_alert(user_id, server_name, alert_type)
            if not enabled:
                continue
            await _bot.send_message(user_id, f"🚨 <b>Алерт</b>\n\n{message}")
        except Exception as e:
            logger.warning("Не удалось отправить алерт user_id=%d: %s", user_id, e)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _fmt_bytes(b: int) -> str:
    for unit, thr in [("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)]:
        if b >= thr:
            return f"{b / thr:.1f} {unit}"
    return f"{b} B"
