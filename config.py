"""
Конфигурация бота из переменных окружения или .env файла
"""

import os
from dataclasses import dataclass, field
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class ServerConfig:
    name: str
    url: str
    auth_header: str = ""


@dataclass
class Config:
    bot_token: str
    allowed_users: list[int]
    servers: list[ServerConfig]
    default_server: int = 0


def load_config() -> Config:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN не задан в переменных окружения")

    raw_users = os.environ.get("ALLOWED_USERS", "")
    allowed_users = []
    for u in raw_users.split(","):
        u = u.strip()
        if u.isdigit():
            allowed_users.append(int(u))

    if not allowed_users:
        raise ValueError("ALLOWED_USERS не задан (укажите Telegram user_id через запятую)")

    # Серверы задаются как:
    # SERVER_1_NAME, SERVER_1_URL, SERVER_1_AUTH
    # SERVER_2_NAME, SERVER_2_URL, SERVER_2_AUTH  ... и т.д.
    # Или просто один сервер: SERVER_URL, SERVER_AUTH, SERVER_NAME
    servers = []

    # Проверяем нумерованные серверы
    i = 1
    while True:
        url = os.environ.get(f"SERVER_{i}_URL")
        if not url:
            break
        name = os.environ.get(f"SERVER_{i}_NAME", f"Server {i}")
        auth = os.environ.get(f"SERVER_{i}_AUTH", "")
        servers.append(ServerConfig(name=name, url=url.rstrip("/"), auth_header=auth))
        i += 1

    # Fallback: одиночный сервер
    if not servers:
        url = os.environ.get("SERVER_URL")
        if not url:
            # Дефолт для разработки
            url = "http://127.0.0.1:9091"
        name = os.environ.get("SERVER_NAME", "Telemt")
        auth = os.environ.get("SERVER_AUTH", "")
        servers.append(ServerConfig(name=name, url=url.rstrip("/"), auth_header=auth))

    return Config(
        bot_token=token,
        allowed_users=allowed_users,
        servers=servers,
    )
