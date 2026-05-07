"""
Клиент для Telemt Control API v1
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=10)


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
        if isinstance(result, list):
            return result
        return []

    async def get_user(self, username: str) -> dict:
        return await self._request("GET", f"/users/{username}")

    async def create_user(self, payload: dict) -> dict:
        return await self._request("POST", "/users", json=payload)

    async def patch_user(self, username: str, payload: dict) -> dict:
        return await self._request("PATCH", f"/users/{username}", json=payload)

    async def delete_user(self, username: str) -> Any:
        return await self._request("DELETE", f"/users/{username}")

    async def ping(self) -> bool:
        """Быстрая проверка доступности API"""
        try:
            await self.get_health()
            return True
        except Exception:
            return False
