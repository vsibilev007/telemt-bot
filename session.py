"""
Менеджер серверных сессий — хранит выбранный сервер для каждого пользователя
"""

from __future__ import annotations

from api_client import TelemetClient
from config import Config, ServerConfig

_user_server: dict[int, int] = {}  # user_id -> server_index


def get_server_index(user_id: int, config: Config) -> int:
    idx = _user_server.get(user_id, config.default_server)
    return max(0, min(idx, len(config.servers) - 1))


def set_server_index(user_id: int, idx: int) -> None:
    _user_server[user_id] = idx


def get_client(user_id: int, config: Config) -> tuple[TelemetClient, ServerConfig]:
    idx = get_server_index(user_id, config)
    srv = config.servers[idx]
    return TelemetClient(srv.url, srv.auth_header), srv
