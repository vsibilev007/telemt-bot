"""
Менеджер серверных сессий — выбор активного сервера для пользователя.
Выбор сохраняется в БД и переживает рестарты бота.
"""

from __future__ import annotations

from api_client import TelemetClient
from config import Config, ServerConfig
import database as db


async def get_server_index(user_id: int, config: Config) -> int:
    idx = await db.get_user_server_index(user_id, default=config.default_server)
    return max(0, min(idx, len(config.servers) - 1))


async def set_server_index(user_id: int, idx: int) -> None:
    await db.set_user_server_index(user_id, idx)


async def get_client(user_id: int, config: Config) -> tuple[TelemetClient, ServerConfig]:
    idx = await get_server_index(user_id, config)
    srv = config.servers[idx]
    return TelemetClient(srv.url, srv.auth_header), srv
