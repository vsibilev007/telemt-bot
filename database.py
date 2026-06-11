"""
SQLite БД: история трафика, настройки алертов, сессии пользователей
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = "telemt_bot.db"


# ─── Инициализация ────────────────────────────────────────────────────────────

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            -- История трафика
            CREATE TABLE IF NOT EXISTS traffic_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT NOT NULL,
                username    TEXT NOT NULL,
                octets      INTEGER NOT NULL,
                connections INTEGER NOT NULL DEFAULT 0,
                sampled_at  INTEGER NOT NULL
            );
            -- Основной индекс: запросы по серверу+юзеру+времени
            CREATE INDEX IF NOT EXISTS idx_traffic_user
                ON traffic_history(server_name, username, sampled_at);
            -- Индекс для сводки по всем юзерам за период
            CREATE INDEX IF NOT EXISTS idx_traffic_server_time
                ON traffic_history(server_name, sampled_at);

            -- Статус серверов
            CREATE TABLE IF NOT EXISTS server_status (
                server_name TEXT PRIMARY KEY,
                status      TEXT NOT NULL DEFAULT 'unknown',
                connections INTEGER NOT NULL DEFAULT 0,
                checked_at  INTEGER NOT NULL DEFAULT 0
            );

            -- Настройки алертов пользователей
            CREATE TABLE IF NOT EXISTS alert_settings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                server_name TEXT NOT NULL,
                alert_type  TEXT NOT NULL,
                threshold   REAL,
                enabled     INTEGER NOT NULL DEFAULT 1,
                UNIQUE(user_id, server_name, alert_type)
            );

            -- Лог сработавших алертов
            CREATE TABLE IF NOT EXISTS alert_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT NOT NULL,
                alert_type  TEXT NOT NULL,
                message     TEXT NOT NULL,
                fired_at    INTEGER NOT NULL
            );
            -- Индекс для cooldown-проверки и истории
            CREATE INDEX IF NOT EXISTS idx_alert_log_lookup
                ON alert_log(server_name, alert_type, fired_at);

            -- История DPI/ТСПУ счётчиков (каждые 2 мин)
            CREATE TABLE IF NOT EXISTS dpi_history (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name             TEXT NOT NULL,
                sampled_at              INTEGER NOT NULL,
                connections_total       INTEGER NOT NULL DEFAULT 0,
                unknown_tls_sni         INTEGER NOT NULL DEFAULT 0,
                tls_handshake_bad_client INTEGER NOT NULL DEFAULT 0,
                direct_modes_disabled   INTEGER NOT NULL DEFAULT 0,
                hs_timeout              INTEGER NOT NULL DEFAULT 0,
                hs_connection_reset     INTEGER NOT NULL DEFAULT 0,
                hs_unexpected_eof       INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_dpi_server_time
                ON dpi_history(server_name, sampled_at);

            -- Мета-данные серверов (version, counters и т.п.)
            CREATE TABLE IF NOT EXISTS server_meta (
                server_name TEXT NOT NULL,
                key         TEXT NOT NULL,
                value       TEXT NOT NULL,
                PRIMARY KEY (server_name, key)
            );

            -- Выбранный сервер для каждого пользователя (сохраняется между рестартами)
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id      INTEGER PRIMARY KEY,
                server_index INTEGER NOT NULL DEFAULT 0,
                updated_at   INTEGER NOT NULL DEFAULT 0
            );
        """)
        await db.commit()
    logger.info("БД инициализирована: %s", DB_PATH)


# ─── Трафик ───────────────────────────────────────────────────────────────────

async def save_traffic_snapshot(server_name: str, users: list):
    now = _now()
    rows = [
        (server_name, u["username"], u.get("total_octets", 0), u.get("current_connections", 0), now)
        for u in users
    ]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT INTO traffic_history(server_name, username, octets, connections, sampled_at)"
            " VALUES(?,?,?,?,?)",
            rows,
        )
        await db.commit()


async def get_traffic_history(server_name: str, username: str, days: int = 7) -> list[dict]:
    since = _now() - days * 86400
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
    """Дельта трафика всех пользователей за период — для сводки."""
    since = _now() - days * 86400
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


# ─── Статус серверов ──────────────────────────────────────────────────────────

async def update_server_status(server_name: str, status: str, connections: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO server_status(server_name, status, connections, checked_at)
               VALUES(?,?,?,?)
               ON CONFLICT(server_name) DO UPDATE SET
                 status=excluded.status,
                 connections=excluded.connections,
                 checked_at=excluded.checked_at""",
            (server_name, status, connections, _now()),
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


# ─── Алерты ───────────────────────────────────────────────────────────────────

async def set_alert(
    user_id: int, server_name: str, alert_type: str,
    threshold: float | None, enabled: bool = True,
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


async def get_alert(user_id: int, server_name: str, alert_type: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT enabled FROM alert_settings"
            " WHERE user_id=? AND server_name=? AND alert_type=?",
            (user_id, server_name, alert_type),
        ) as cur:
            row = await cur.fetchone()
            return bool(row[0]) if row else False


async def get_alerts(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM alert_settings WHERE user_id=? AND enabled=1", (user_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def log_alert(server_name: str, alert_type: str, message: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO alert_log(server_name, alert_type, message, fired_at) VALUES(?,?,?,?)",
            (server_name, alert_type, message, _now()),
        )
        await db.commit()


async def was_alert_fired_recently(
    server_name: str, alert_type: str, within_secs: int = 300
) -> bool:
    since = _now() - within_secs
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM alert_log"
            " WHERE server_name=? AND alert_type=? AND fired_at>? LIMIT 1",
            (server_name, alert_type, since),
        ) as cur:
            return await cur.fetchone() is not None


async def get_recent_alerts(server_name: str, limit: int = 20) -> list[dict]:
    """История последних сработавших алертов — для команды /alert_log."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT alert_type, message, fired_at
               FROM alert_log
               WHERE server_name=?
               ORDER BY fired_at DESC
               LIMIT ?""",
            (server_name, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ─── Сессии пользователей ─────────────────────────────────────────────────────

async def get_user_server_index(user_id: int, default: int = 0) -> int:
    """Возвращает сохранённый индекс сервера для пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT server_index FROM user_sessions WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else default


async def set_user_server_index(user_id: int, index: int):
    """Сохраняет выбранный пользователем индекс сервера."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO user_sessions(user_id, server_index, updated_at)
               VALUES(?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                 server_index=excluded.server_index,
                 updated_at=excluded.updated_at""",
            (user_id, index, _now()),
        )
        await db.commit()



# ─── Очистка ──────────────────────────────────────────────────────────────────

async def cleanup_old_data(days: int = 30):
    cutoff = _now() - days * 86400
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM traffic_history WHERE sampled_at<?", (cutoff,))
        await db.execute("DELETE FROM alert_log WHERE fired_at<?", (cutoff,))
        await db.commit()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> int:
    return int(datetime.now(timezone.utc).timestamp())
