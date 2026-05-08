"""
Фоновые задачи: мониторинг, сбор трафика, алерты
"""

from __future__ import annotations
import json
import logging
import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import database as db
from api_client import TelemetClient
from config import Config

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None
_bot = None
_config: Config | None = None
DB_PATH = db.DB_PATH


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
    logger.info("Scheduler запущен")


def stop():
    if _scheduler:
        _scheduler.shutdown(wait=False)


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


async def _collect_traffic():
    if not _config:
        return
    for srv in _config.servers:
        try:
            client = TelemetClient(srv.url, srv.auth_header)
            users = await client.get_users()
            if users:
                await db.save_traffic_snapshot(srv.name, users)
                logger.debug("Трафик собран: %s (%d users)", srv.name, len(users))
        except Exception as e:
            logger.warning("Ошибка сбора трафика [%s]: %s", srv.name, e)


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
            if prev and prev["status"] == "ok" and status != "ok":
                await _fire_alert(
                    srv.name,
                    "status_down",
                    f"🔴 <b>{srv.name}</b> — статус изменился: <b>{status}</b>",
                )
            if prev and prev["status"] != "ok" and status == "ok":
                await _fire_alert(
                    srv.name,
                    "status_up",
                    f"🟢 <b>{srv.name}</b> — статус восстановлен: <b>OK</b>",
                    cooldown=0,
                )
            if prev and prev["connections"] > 100:
                delta_pct = (
                    (connections - prev["connections"]) / prev["connections"] * 100
                )
                if delta_pct > 50:
                    await _fire_alert(
                        srv.name,
                        "conn_spike",
                        f"⚠ <b>{srv.name}</b> — всплеск соединений: "
                        f"{prev['connections']:,} → {connections:,} (+{delta_pct:.0f}%)",
                    )
            try:
                writers = await client.get_stats_me_writers()
                summary_w = writers.get("summary", {})
                coverage = summary_w.get("coverage_pct", 100)
                if coverage < 80:
                    await _fire_alert(
                        srv.name,
                        "writers_low",
                        f"⚠ <b>{srv.name}</b> — ME Writers coverage низкий: {coverage:.0f}%",
                    )
            except Exception:
                pass
            try:
                sysinfo = await client.get_system_info()
                version = sysinfo.get("version", "")
                if version:
                    prev_version = await _get_meta(srv.name, "version")
                    await _set_meta(srv.name, "version", version)
                    if prev_version and prev_version != version:
                        await _fire_alert(
                            srv.name,
                            "version_change",
                            f"🏷 <b>{srv.name}</b> — обновление telemt: "
                            f"<b>v{prev_version}</b> → <b>v{version}</b>",
                            cooldown=0,
                        )
            except Exception:
                pass
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
                prev_counters_raw = await _get_meta(srv.name, "counters")
                prev_counters = (
                    json.loads(prev_counters_raw) if prev_counters_raw else {}
                )
                await _set_meta(srv.name, "counters", json.dumps(current_counters))
                if prev_counters:

                    def delta(key):
                        return current_counters.get(key, 0) - prev_counters.get(key, 0)

                    d_sni = delta("unknown_tls_sni")
                    if d_sni > 0:
                        await _fire_alert(
                            srv.name,
                            "bad_unknown_sni",
                            f"⚠ <b>{srv.name}</b> — неизвестный SNI: +{d_sni} за 2 мин",
                            cooldown=300,
                        )
                    d_hs_timeout = delta("timeout")
                    if d_hs_timeout >= 50:
                        await _fire_alert(
                            srv.name,
                            "hs_timeout_spike",
                            f"⚠ <b>{srv.name}</b> — всплеск handshake timeout: +{d_hs_timeout} за 2 мин",
                            cooldown=120,
                        )
                    d_bad_client = delta("tls_handshake_bad_client")
                    if d_bad_client >= 100:
                        await _fire_alert(
                            srv.name,
                            "bad_client_spike",
                            f"⚠ <b>{srv.name}</b> — всплеск плохих TLS клиентов: +{d_bad_client} за 2 мин",
                            cooldown=120,
                        )
                    d_reset = delta("expected_64_got_0_connection_reset")
                    if d_reset > 0:
                        await _fire_alert(
                            srv.name,
                            "hs_conn_reset",
                            f"⚠ <b>{srv.name}</b> — сброс соединений при handshake: +{d_reset} за 2 мин",
                            cooldown=300,
                        )
            except Exception:
                pass
        except Exception as e:
            prev = await db.get_server_status(srv.name)
            if not prev or prev["status"] != "unreachable":
                await db.update_server_status(srv.name, "unreachable", 0)
                await _fire_alert(
                    srv.name,
                    "unreachable",
                    f"🔴 <b>{srv.name}</b> — сервер недоступен: {type(e).__name__}",
                    cooldown=300,
                )


async def _fire_alert(
    server_name: str, alert_type: str, message: str, cooldown: int = 120
):
    """Отправляет алерт всем пользователям у которых включён этот тип алерта"""
    if cooldown > 0 and await db.was_alert_fired_recently(
        server_name, alert_type, cooldown
    ):
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


async def _cleanup():
    await db.cleanup_old_data(days=30)
    logger.info("Очистка старых данных выполнена")
