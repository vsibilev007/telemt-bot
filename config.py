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
        time.tzset()
    except AttributeError:
        pass


@dataclass
class ServerConfig:
    name: str
    url: str
    auth_header: str = ""
    group: str = ""   # Имя кластерной группы. Пусто = одиночный сервер


@dataclass
class AlertThresholds:
    conn_spike_pct: float = 50.0
    conn_spike_min_base: int = 100
    writers_low_pct: float = 80.0
    hs_timeout_spike: int = 50
    bad_client_spike: int = 100
    quota_alert_pct: float = 80.0


@dataclass
class AgentConfig:
    name: str
    url: str
    token: str = ""
    flag: str = ""


@dataclass
class Config:
    bot_token: str
    allowed_users: list[int]
    servers: list[ServerConfig]
    thresholds: AlertThresholds = field(default_factory=AlertThresholds)
    default_server: int = 0
    agents: list[AgentConfig] = field(default_factory=list)
    lite_mode: bool = False  # LITE_MODE=true — минимальный набор функций

    def get_group_members(self, server: ServerConfig) -> list[ServerConfig]:
        """Возвращает все узлы группы. Если сервер одиночный — только он."""
        if not server.group:
            return [server]
        return [s for s in self.servers if s.group == server.group]

    def get_menu_servers(self) -> list[ServerConfig]:
        """
        Список серверов для меню — группы показываем как один сервер
        (первый узел группы). Одиночные — как есть.
        """
        seen_groups: set[str] = set()
        result: list[ServerConfig] = []
        for srv in self.servers:
            if srv.group:
                if srv.group not in seen_groups:
                    seen_groups.add(srv.group)
                    result.append(srv)  # представитель группы
            else:
                result.append(srv)
        return result

    def is_cluster(self, server: ServerConfig) -> bool:
        """True если сервер входит в кластерную группу."""
        return bool(server.group) and len(self.get_group_members(server)) > 1


def _clean(val: str) -> str:
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
    # ── BOT_TOKEN ─────────────────────────────────────────────────────────────
    bot_token = _clean(os.environ.get("BOT_TOKEN", ""))
    if not bot_token:
        raise RuntimeError("BOT_TOKEN не задан в .env или переменных окружения")

    # ── ALLOWED_USERS ─────────────────────────────────────────────────────────
    allowed_raw = _clean(os.environ.get("ALLOWED_USERS", ""))
    allowed_users = [int(x) for x in allowed_raw.split(",") if x.strip().isdigit()]
    if not allowed_users:
        raise ValueError("ALLOWED_USERS не задан (укажите Telegram user_id через запятую)")

    # ── Серверы Telemt ────────────────────────────────────────────────────────
    servers: list[ServerConfig] = []
    i = 1
    while True:
        url = _clean(os.environ.get(f"SERVER_{i}_URL", ""))
        if not url:
            break
        name = _clean(os.environ.get(f"SERVER_{i}_NAME", f"Server {i}"))
        auth = _clean(os.environ.get(f"SERVER_{i}_AUTH", ""))
        group = _clean(os.environ.get(f"SERVER_{i}_GROUP", ""))
        servers.append(ServerConfig(name=name, url=url.rstrip("/"), auth_header=auth, group=group))
        i += 1

    # Fallback: одиночный сервер
    if not servers:
        url = _clean(os.environ.get("SERVER_URL", "http://127.0.0.1:9091"))
        name = _clean(os.environ.get("SERVER_NAME", "Telemt"))
        auth = _clean(os.environ.get("SERVER_AUTH", ""))
        servers.append(ServerConfig(name=name, url=url.rstrip("/"), auth_header=auth))

    # ── Пороги алертов ────────────────────────────────────────────────────────
    thresholds = AlertThresholds(
        conn_spike_pct=_float_env("ALERT_CONN_SPIKE_PCT", 50.0),
        conn_spike_min_base=_int_env("ALERT_CONN_SPIKE_MIN_BASE", 100),
        writers_low_pct=_float_env("ALERT_WRITERS_LOW_PCT", 80.0),
        hs_timeout_spike=_int_env("ALERT_HS_TIMEOUT_SPIKE", 50),
        bad_client_spike=_int_env("ALERT_BAD_CLIENT_SPIKE", 100),
        quota_alert_pct=_float_env("ALERT_QUOTA_PCT", 80.0),
    )

    # ── Агенты проверки прокси ────────────────────────────────────────────────
    agents: list[AgentConfig] = []
    i = 1
    while True:
        url = _clean(os.environ.get(f"AGENT_{i}_URL", ""))
        if not url:
            if i == 1:
                # Fallback: старый формат PROXY_AGENT_URL
                url = _clean(os.environ.get("PROXY_AGENT_URL", ""))
                if url:
                    token = _clean(os.environ.get("PROXY_AGENT_TOKEN", ""))
                    agents.append(AgentConfig(name="RU", url=url, token=token))
            break
        name = _clean(os.environ.get(f"AGENT_{i}_NAME", f"Agent {i}"))
        token = _clean(os.environ.get(f"AGENT_{i}_TOKEN", ""))
        flag = _clean(os.environ.get(f"AGENT_{i}_FLAG", ""))
        agents.append(AgentConfig(name=name, url=url, token=token, flag=flag))
        i += 1

    return Config(
        bot_token=bot_token,
        allowed_users=allowed_users,
        servers=servers,
        thresholds=thresholds,
        agents=agents,
        lite_mode=_clean(os.environ.get("LITE_MODE", "false")).lower() in ("true", "1", "yes"),
    )
