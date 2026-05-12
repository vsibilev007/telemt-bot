"""
Конфигурация бота из переменных окружения или .env файла
"""

import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Применяем TZ сразу после загрузки .env — до любых datetime вызовов
_tz_raw = os.environ.get("TZ", "")
_tz = _tz_raw.split("#")[0].strip() if _tz_raw else ""
if _tz:
    os.environ["TZ"] = _tz
    try:
        import time
        time.tzset()  # применяет TZ на уровне libc (Linux/macOS)
    except AttributeError:
        pass  # Windows не поддерживает tzset — там TZ читается иначе


@dataclass
class ServerConfig:
    name: str
    url: str
    auth_header: str = ""


@dataclass
class AlertThresholds:
    """Пороги срабатывания алертов — настраиваются через .env"""

    # Всплеск соединений: +N% при базе не менее M
    conn_spike_pct: float = 50.0        # ALERT_CONN_SPIKE_PCT
    conn_spike_min_base: int = 100      # ALERT_CONN_SPIKE_MIN_BASE

    # ME Writers coverage ниже N%
    writers_low_pct: float = 80.0       # ALERT_WRITERS_LOW_PCT

    # Handshake timeout: +N за 2 мин
    hs_timeout_spike: int = 50          # ALERT_HS_TIMEOUT_SPIKE

    # Плохих TLS клиентов: +N за 2 мин
    bad_client_spike: int = 100         # ALERT_BAD_CLIENT_SPIKE

    # Квота: алерт при использовании N% от data_quota_bytes
    quota_alert_pct: float = 80.0       # ALERT_QUOTA_PCT


@dataclass
class Config:
    bot_token: str
    allowed_users: list[int]
    servers: list[ServerConfig]
    thresholds: AlertThresholds = field(default_factory=AlertThresholds)
    default_server: int = 0


def _clean(val: str) -> str:
    """'80  # comment' → '80'"""
    return val.split("#")[0].strip()


def _float_env(key: str, default: float) -> float:
    try:
        return float(_clean(os.environ.get(key, str(default))))
    except (ValueError, TypeError):
        return default


def _int_env(key: str, default: int) -> int:
    try:
        return int(_clean(os.environ.get(key, str(default))))
    except (ValueError, TypeError):
        return default


def load_config() -> Config:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN не задан в переменных окружения")

    raw_users = os.environ.get("ALLOWED_USERS", "")
    allowed_users = [int(u.strip()) for u in raw_users.split(",") if u.strip().isdigit()]
    if not allowed_users:
        raise ValueError("ALLOWED_USERS не задан (укажите Telegram user_id через запятую)")

    # Нумерованные серверы: SERVER_1_URL, SERVER_1_NAME, SERVER_1_AUTH ...
    servers: list[ServerConfig] = []
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
        url = os.environ.get("SERVER_URL", "http://127.0.0.1:9091")
        name = os.environ.get("SERVER_NAME", "Telemt")
        auth = os.environ.get("SERVER_AUTH", "")
        servers.append(ServerConfig(name=name, url=url.rstrip("/"), auth_header=auth))

    thresholds = AlertThresholds(
        conn_spike_pct=_float_env("ALERT_CONN_SPIKE_PCT", 50.0),
        conn_spike_min_base=_int_env("ALERT_CONN_SPIKE_MIN_BASE", 100),
        writers_low_pct=_float_env("ALERT_WRITERS_LOW_PCT", 80.0),
        hs_timeout_spike=_int_env("ALERT_HS_TIMEOUT_SPIKE", 50),
        bad_client_spike=_int_env("ALERT_BAD_CLIENT_SPIKE", 100),
        quota_alert_pct=_float_env("ALERT_QUOTA_PCT", 80.0),
    )

    return Config(
        bot_token=token,
        allowed_users=allowed_users,
        servers=servers,
        thresholds=thresholds,
    )
