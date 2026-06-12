"""
Клиент для Telemt Control API v1
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=10, connect=3)

# Ограничение параллельных запросов к одному инстансу API
_semaphores: dict[str, asyncio.Semaphore] = {}


def _get_semaphore(base_url: str) -> asyncio.Semaphore:
    if base_url not in _semaphores:
        _semaphores[base_url] = asyncio.Semaphore(5)
    return _semaphores[base_url]


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 0):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(f"[{code}] {message}")


class TelemetClient:
    def __init__(self, base_url: str, auth_header: str = ""):
        self.base_url = base_url.rstrip("/")
        self.auth_header = auth_header

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.auth_header:
            h["Authorization"] = self.auth_header
        return h

    async def _request(
        self,
        method: str,
        path: str,
        json: Any = None,
        if_match: Optional[str] = None,
    ) -> dict:
        url = f"{self.base_url}/v1{path}"
        headers = self._headers()
        if if_match:
            headers["If-Match"] = if_match

        sem = _get_semaphore(self.base_url)
        async with sem:
            try:
                async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
                    async with session.request(
                        method, url, headers=headers, json=json
                    ) as resp:
                        data = await resp.json(content_type=None)
                        if not data.get("ok"):
                            err = data.get("error", {})
                            raise ApiError(
                                code=err.get("code", "unknown"),
                                message=err.get("message", str(data)),
                                status=resp.status,
                            )
                        return data.get("data", {})
            except aiohttp.ServerTimeoutError:
                raise ApiError("timeout", f"Нет ответа от API за 10с", status=0)
            except aiohttp.ClientConnectorError as e:
                raise ApiError("unreachable", f"Не удалось подключиться: {e}", status=0)

    # ─── Endpoints ───────────────────────────────────────────────────────────

    async def get_health(self) -> dict:
        return await self._request("GET", "/health")

    async def get_system_info(self) -> dict:
        return await self._request("GET", "/system/info")

    async def get_stats_summary(self) -> dict:
        return await self._request("GET", "/stats/summary")

    async def get_runtime_gates(self) -> dict:
        return await self._request("GET", "/runtime/gates")

    async def get_runtime_initialization(self) -> dict:
        return await self._request("GET", "/runtime/initialization")

    async def get_security_posture(self) -> dict:
        return await self._request("GET", "/security/posture")

    async def get_security_whitelist(self) -> dict:
        return await self._request("GET", "/security/whitelist")

    async def get_limits_effective(self) -> dict:
        return await self._request("GET", "/limits/effective")

    async def get_stats_upstreams(self) -> dict:
        return await self._request("GET", "/stats/upstreams")

    async def get_stats_dcs(self) -> dict:
        return await self._request("GET", "/stats/dcs")

    async def get_stats_me_writers(self) -> dict:
        return await self._request("GET", "/stats/me-writers")

    async def get_runtime_me_quality(self) -> dict:
        return await self._request("GET", "/runtime/me_quality")

    async def get_runtime_upstream_quality(self) -> dict:
        return await self._request("GET", "/runtime/upstream_quality")

    async def get_runtime_events(self, limit: int = 20) -> dict:
        return await self._request("GET", f"/runtime/events/recent?limit={limit}")

    async def get_runtime_connections(self) -> dict:
        return await self._request("GET", "/runtime/connections/summary")

    async def get_users(self) -> list:
        result = await self._request("GET", "/users")
        return result if isinstance(result, list) else []

    async def get_user(self, username: str) -> dict:
        return await self._request("GET", f"/users/{username}")

    async def get_users_quota(self) -> dict:
        """GET /v1/stats/users/quota — сводка использования квот (3.4.12+, путь изменён в 3.4.13)"""
        return await self._request("GET", "/stats/users/quota")

    async def create_user(self, payload: dict) -> dict:
        return await self._request("POST", "/users", json=payload)

    async def patch_user(self, username: str, payload: dict) -> dict:
        return await self._request("PATCH", f"/users/{username}", json=payload)

    async def enable_user(self, username: str) -> dict:
        """POST /v1/users/{username}/enable (3.4.14+)"""
        return await self._request("POST", f"/users/{username}/enable")

    async def disable_user(self, username: str) -> dict:
        """POST /v1/users/{username}/disable (3.4.14+)"""
        return await self._request("POST", f"/users/{username}/disable")

    async def delete_user(self, username: str) -> Any:
        return await self._request("DELETE", f"/users/{username}")

    async def reset_user_quota(self, username: str) -> dict:
        """POST /v1/users/{username}/reset-quota (3.4.11+)"""
        return await self._request("POST", f"/users/{username}/reset-quota")

    async def get_config(self) -> dict:
        """GET /v1/config (3.4.16+)"""
        return await self._request("GET", "/config")

    async def patch_config(self, payload: dict, if_match: str = "") -> dict:
        """PATCH /v1/config (3.4.16+)"""
        return await self._request("PATCH", "/config", json=payload, if_match=if_match or None)

    async def get_runtime_tls_fingerprints(self, limit: int = 100) -> dict:
        """GET /v1/runtime/tls-fingerprints?limit=N (3.4.14+)"""
        return await self._request("GET", f"/runtime/tls-fingerprints?limit={limit}")

    async def ping(self) -> bool:
        try:
            await self.get_health()
            return True
        except Exception:
            return False


# ─── Кластерные операции ─────────────────────────────────────────────────────

@dataclass
class NodeResult:
    """Результат операции на одном узле кластера."""
    server_name: str
    ok: bool
    data: Any = None
    error: str = ""


async def cluster_read(servers: list, method_name: str, *args, **kwargs) -> Any:
    """
    Читает данные с первого доступного узла кластера.
    servers: list[ServerConfig]
    """
    from config import ServerConfig as _SC
    last_error = None
    for srv in servers:
        try:
            client = TelemetClient(srv.url, srv.auth_header)
            method = getattr(client, method_name)
            return await method(*args, **kwargs)
        except ApiError as e:
            last_error = e
            continue
    raise last_error or ApiError("unreachable", "Все узлы кластера недоступны")


async def cluster_write(
    servers: list,
    method_name: str,
    *args,
    **kwargs,
) -> list[NodeResult]:
    """
    Выполняет write-операцию параллельно на всех узлах кластера.
    Возвращает список NodeResult — успех/ошибка по каждому узлу.
    servers: list[ServerConfig]
    """
    async def _call_one(srv) -> NodeResult:
        try:
            client = TelemetClient(srv.url, srv.auth_header)
            method = getattr(client, method_name)
            data = await method(*args, **kwargs)
            return NodeResult(server_name=srv.name, ok=True, data=data)
        except ApiError as e:
            return NodeResult(server_name=srv.name, ok=False, error=f"{e.code}: {e.message}")
        except Exception as e:
            return NodeResult(server_name=srv.name, ok=False, error=str(e)[:100])

    results = await asyncio.gather(*[_call_one(srv) for srv in servers])
    return list(results)


async def cluster_users_with_nodes(servers: list) -> list[dict]:
    """
    Получает список пользователей и добавляет информацию о том,
    на каком узле кластера активны соединения.
    Возвращает пользователей с полем '_nodes': {'HA_A': conns, 'HA_B': conns}
    IP-адреса объединяются с всех узлов.
    """
    async def _get_users_from(srv) -> tuple[str, list]:
        try:
            client = TelemetClient(srv.url, srv.auth_header)
            users = await client.get_users()
            return srv.name, users
        except Exception:
            return srv.name, []

    # Параллельно опрашиваем все узлы
    results = await asyncio.gather(*[_get_users_from(srv) for srv in servers])

    users_by_name: dict[str, dict] = {}
    for srv_name, users in results:
        for u in users:
            username = u["username"]
            if username not in users_by_name:
                users_by_name[username] = dict(u)
                users_by_name[username]["_nodes"] = {}
                users_by_name[username]["_all_ips"] = set()

            conns = u.get("current_connections", 0)
            users_by_name[username]["_nodes"][srv_name] = conns

            # Суммируем соединения по всем узлам
            users_by_name[username]["current_connections"] = sum(
                users_by_name[username]["_nodes"].values()
            )

            # Объединяем IP-адреса со всех узлов
            ip_list = u.get("active_unique_ips_list", [])
            users_by_name[username]["_all_ips"].update(ip_list)

            # Суммируем active_unique_ips — берём максимум между узлами
            # (один клиент не может быть на двух узлах с разных IP одновременно)
            cur_ips = users_by_name[username].get("active_unique_ips", 0)
            node_ips = u.get("active_unique_ips", 0)
            users_by_name[username]["active_unique_ips"] = max(cur_ips, node_ips)

            # recent_unique_ips — берём максимум
            cur_recent = users_by_name[username].get("recent_unique_ips", 0)
            node_recent = u.get("recent_unique_ips", 0)
            users_by_name[username]["recent_unique_ips"] = max(cur_recent, node_recent)

    # Финализируем IP-листы
    for username, u in users_by_name.items():
        all_ips = list(u.pop("_all_ips", set()))
        u["active_unique_ips_list"] = all_ips
        # Если агрегированный список длиннее — обновляем счётчик
        if len(all_ips) > u.get("active_unique_ips", 0):
            u["active_unique_ips"] = len(all_ips)

    return list(users_by_name.values())
