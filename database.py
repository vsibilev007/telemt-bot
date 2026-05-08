"""
SQLite БД для хранения истории трафика и настроек алертов
"""

from __future__ import annotations
import logging
from datetime import UTC, datetime
import aiosqlite

logger = logging.getLogger(__name__)
DB_PATH = "telemt_bot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS traffic_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT NOT NULL,
                username    TEXT NOT NULL,
                octets      INTEGER NOT NULL,
                connections INTEGER NOT NULL DEFAULT 0,
                sampled_at  INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_traffic_user
                ON traffic_history(server_name, username, sampled_at);
            CREATE TABLE IF NOT EXISTS server_status (
                server_name TEXT PRIMARY KEY,
                status      TEXT NOT NULL DEFAULT 'unknown',
                connections INTEGER NOT NULL DEFAULT 0,
                checked_at  INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS alert_settings (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                server_name     TEXT NOT NULL,
                alert_type      TEXT NOT NULL,
                threshold       REAL,
                enabled         INTEGER NOT NULL DEFAULT 1,
                UNIQUE(user_id, server_name, alert_type)
            );
            CREATE TABLE IF NOT EXISTS alert_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT NOT NULL,
                alert_type  TEXT NOT NULL,
                message     TEXT NOT NULL,
                fired_at    INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS server_meta (
                server_name TEXT NOT NULL,
                key         TEXT NOT NULL,
                value       TEXT NOT NULL,
                PRIMARY KEY (server_name, key)
            );
        """)
        await db.commit()
    logger.info("БД инициализирована: %s", DB_PATH)


async def save_traffic_snapshot(server_name: str, users: list):
    now = int(datetime.now(UTC).timestamp())
    rows = [
        (
            server_name,
            u["username"],
            u.get("total_octets", 0),
            u.get("current_connections", 0),
            now,
        )
        for u in users
    ]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT INTO traffic_history(server_name, username, octets, connections, sampled_at) VALUES(?,?,?,?,?)",
            rows,
        )
        await db.commit()


async def get_traffic_history(
    server_name: str, username: str, days: int = 7
) -> list[dict]:
    since = int(datetime.now(UTC).timestamp()) - days * 86400
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT sampled_at, octets, connections
               FROM traffic_history
               WHERE server_name=? AND username=? AND sampled_at>=?
               ORDER BY sampled_at""",
            (server_name, username, since),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_traffic_delta(server_name: str, username: str, days: int = 7) -> dict:
    """Разница трафика между первой и последней точкой за период"""
    rows = await get_traffic_history(server_name, username, days)
    if len(rows) < 2:
        return {"delta_bytes": 0, "points": len(rows), "days": days}
    delta = rows[-1]["octets"] - rows[0]["octets"]
    return {
        "delta_bytes": max(0, delta),
        "points": len(rows),
        "days": days,
        "first_at": rows[0]["sampled_at"],
        "last_at": rows[-1]["sampled_at"],
    }


async def get_all_users_traffic_delta(server_name: str, days: int = 7) -> list[dict]:
    """Дельта трафика всех пользователей за период — для сводки"""
    since = int(datetime.now(UTC).timestamp()) - days * 86400
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT username,
                      MAX(octets) - MIN(octets) AS delta_bytes,
                      MAX(connections)          AS max_conns,
                      COUNT(*)                  AS points
               FROM traffic_history
               WHERE server_name=? AND sampled_at>=?
               GROUP BY username
               ORDER BY delta_bytes DESC""",
            (server_name, since),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def update_server_status(server_name: str, status: str, connections: int):
    now = int(datetime.now(UTC).timestamp())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO server_status(server_name, status, connections, checked_at)
               VALUES(?,?,?,?)
               ON CONFLICT(server_name) DO UPDATE SET
                 status=excluded.status,
                 connections=excluded.connections,
                 checked_at=excluded.checked_at""",
            (server_name, status, connections, now),
        )
        await db.commit()


async def get_server_status(server_name: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM server_status WHERE server_name=?", (server_name,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def set_alert(
    user_id: int,
    server_name: str,
    alert_type: str,
    threshold: float | None,
    enabled: bool = True,
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO alert_settings(user_id, server_name, alert_type, threshold, enabled)
               VALUES(?,?,?,?,?)
               ON CONFLICT(user_id, server_name, alert_type) DO UPDATE SET
                 threshold=excluded.threshold,
                 enabled=excluded.enabled""",
            (user_id, server_name, alert_type, threshold, int(enabled)),
        )
        await db.commit()


async def get_alerts(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM alert_settings WHERE user_id=? AND enabled=1", (user_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def log_alert(server_name: str, alert_type: str, message: str):
    now = int(datetime.now(UTC).timestamp())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO alert_log(server_name, alert_type, message, fired_at) VALUES(?,?,?,?)",
            (server_name, alert_type, message, now),
        )
        await db.commit()


async def was_alert_fired_recently(
    server_name: str, alert_type: str, within_secs: int = 300
) -> bool:
    since = int(datetime.now(UTC).timestamp()) - within_secs
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM alert_log WHERE server_name=? AND alert_type=? AND fired_at>? LIMIT 1",
            (server_name, alert_type, since),
        ) as cur:
            return await cur.fetchone() is not None


async def cleanup_old_data(days: int = 30):
    cutoff = int(datetime.now(UTC).timestamp()) - days * 86400
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM traffic_history WHERE sampled_at<?", (cutoff,))
        await db.execute("DELETE FROM alert_log WHERE fired_at<?", (cutoff,))
        await db.commit()


async def get_alert(user_id: int, server_name: str, alert_type: str) -> bool:
    """Возвращает True если алерт включён, False если выключен или не существует."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT enabled FROM alert_settings WHERE user_id=? AND server_name=? AND alert_type=?",
            (user_id, server_name, alert_type),
        ) as cur:
            row = await cur.fetchone()
            return bool(row[0]) if row else False
