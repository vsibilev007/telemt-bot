# Release Notes

## Bulk User Operations

- **Multi-select mode** — "☑️ Выбрать" in the users list turns rows into checkboxes (paged, no refetch on toggle); "🔴 Откл / ✅ Вкл / 🗑 Удалить" apply to all selected users with per-user cluster results
- **Bulk delete** — confirmation screen; WEB profiles are stripped from every cluster node before DELETE (the API rejects users referenced by a WEB profile)
- **Bulk create** — "➕➕ Массово" button: one-line spec `template count days [quota_GB]` (e.g. `guest 10 30`, `vpn{n} 3 7 50`) creates numbered users with expiration/quota; existing names are skipped, not failed
- All WEB profiles for a bulk batch are added in a single `PATCH /v1/config?reload=instant` instead of one patch per user
- Names are limited to 40 chars so `user:links:` callbacks stay under Telegram's 64-byte limit

## Config Editor Reload

- **Apply + reload in one request** — "⚡ +instant" / "🌙 +drain" buttons next to "Применить" (PATCH /v1/config?reload=..., single If-Match revision)
- **Post-apply reload offer** — after a patch that reports `runtime_reload_required`, the bot offers instant/drain reload buttons (POST /v1/system/reload)
- **Accurate restart reporting** — uses `runtime_reload_required` / `process_restart_required` / `deferred_process_fields`; falls back to legacy `restart_required` on Telemt 3.4.16–3.4.24
- **Version gating** — reload buttons hidden on Telemt < 3.4.25

## WEB Operations Polling

- **Close operation status** — after closing a WEB session the bot polls `GET /v1/runtime/web/operations/{id}` up to ~6s and reports the terminal state with counters (matched/signalled) or failure reason
- Removed duplicated `get_web_status` call in the close handler

## Readiness Alert (Telemt 3.5.11+)

- **New alert type `not_ready`** — every 2 min the bot checks `GET /v1/health/ready` and alerts when the server stops accepting new clients (`admission_closed` / `no_healthy_upstreams`), plus recovery notice
- Toggle in /alerts — "Готовность (admission/upstreams)"; endpoint 404 on older Telemt is auto-detected and skipped

## HTTP Session Reuse

- **Keep-alive pool** — `api_client` now reuses one `aiohttp.ClientSession` per API instance instead of creating a session per request (no TCP/TLS handshake on every call)
- Single retry on `ServerDisconnectedError` (idle keep-alive connection closed by server)
- Sessions closed on bot shutdown (`close_http_sessions()`)

## Tests & CI

- **pytest suite** — parser tests for `parse_proxy_url` (classic/dd/FakeTLS SNI), `_parse_config_value`, `_parse_exp`, `_version_at_least`, SNI/secret extraction, `make_webproxy_link`, `tg_deep_link`, config-editor keyboards (incl. 64-byte callback_data limit)
- Run locally: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest && .venv/bin/python -m pytest tests/ -q`
- **CI** — new `test` job (venv + pytest) gates the build alongside lint

## Cleanup

- Removed unused `telethon` dependency and its logger silencing
- `tests/` and `conftest.py` excluded from the Docker image

## Telemt 3.5.11 API Support

- **rotate-secret** — user secret rotation via the dedicated `POST /v1/users/{username}/rotate-secret` endpoint (updates admission identity and WEB capability in one call)
- **WEB links** — `tg://webproxy` links built the way Telegram Desktop expects: marker 0x70 (+0xDD), base64url secret, base path encoded into the server part
- **Runtime snapshots** — new menus/endpoints: `/v1/health/ready`, `/v1/stats/zero/all`, `/v1/stats/minimal/all`, `/v1/stats/users/active-ips`, `/v1/runtime/me_pool_state`, `/v1/runtime/nat_stun`, `/v1/runtime/me-selftest`
- **User deletion** — no longer waits on an instant reload; WEB profiles are stripped first so the API accepts the delete
- **tg:// deep links** — proxy connect buttons open Telegram's add-proxy window directly (QR codes removed)
- **Lite mode** — alert/check/reload commands are hard-disabled, not just hidden from the menu
- **Docker scan** — base image digest bumped, Debian packages upgraded, pip removed from the runtime image to clear HIGH Trivy findings
- **Quota alert** — fixed enablement and completed command/env reference docs

## WEB Proxy Support (Telemt 3.5.5+)

- **WEB Proxy menu** — new button in main menu (visible only for Telemt 3.5.5+)
- **Status** — lifecycle, runtime, limits, streams, sessions, learning, debug, ingress, operator lifecycle, capacity, carrier negotiation
- **Sessions** — list active WEB sessions with pagination and details (IP, carrier, user agent)
- **Management** — close sessions, clear debug records, reset carrier learning
- **Lifecycle control** (Telemt 3.5.7+) — pause admission, graceful drain with timeout, resume
- **WEB links** — auto-generate `tg://webproxy?server=HOST&secret=ddSECRET` for users
- **Auto-profiles** — WEB profile automatically added when creating users
- **Auto-removal** — WEB profile removed before deleting access user
- **Version check** — for Telemt 3.4.25 and below, only TLS links are shown
- **api_client.py** — new methods: get_web_status(), get_web_sessions(), get_web_session(), close_web_sessions(), clear_web_debug(), reset_web_carrier_learning(), web_lifecycle_pause(), web_lifecycle_drain(), web_lifecycle_resume()
- **formatters.py** — new formatters: format_web_status(), format_web_sessions(), format_web_session_detail(), make_webproxy_link()
- **keyboards.py** — new keyboards: web_menu_kb(), web_sessions_kb(), web_session_detail_kb()

## Runtime Reload (Telemt 3.4.25+)

- **/reload command** — safe runtime configuration reload without process restart
  - `/reload instant` — instant switch, old sessions terminated
  - `/reload drain` — graceful shutdown of old sessions
- **/reload_status command** — check reload operation status
- **api_client.py** — new methods: system_reload(), get_reload_status()
- **PATCH /v1/config** — support `?reload=instant|drain` parameter for patch + reload in one request

## Docker Image

- **Production Dockerfile** — multi-stage build (builder → final) based on python:3.11-slim-bookworm
- **Non-root user** appuser (UID 10001) — container does not run as root
- **Hardening**: read_only, cap_drop: ALL, no-new-privileges, mem_limit: 256m, pids_limit: 256
- **Named volume** telemt-data:/data — safe database storage with correct permissions
- **Layer trimming**: removes __pycache__, test directories, .pyc/.pyx/.pyi files

## CI/CD

- **GitHub Actions** — pipeline: lint → build → scan → push on main branch and v*.*.* tags
- **Lint**: ruff check on every PR
- **Trivy scan** — HIGH/CRITICAL vulnerability scanning before push; build fails on findings
- **GHCR**: image published to ghcr.io with tags: latest, v1.2.3, 1.2, sha-abc1234
- **GHA cache**: BuildKit caches layers between builds for faster rebuilds

## Node Diagnostics

- **/check command** — full node diagnostics via `tg://proxy?...` links
- **Check Proxy button** — now uses full diagnostics
- **Checks**: TCP, TLS, MTProto (raw), stability, DPI detection, DNS, GeoIP
- **Output**: per-protocol status, diagnostics, check time, final status (OK/PARTIAL/FAIL)
- **Agents** (RU, etc.) checked in parallel

## SNI Domain Display

- **Client card** — masking domain (SNI) shown above each TLS link
- **QR buttons** — show domain instead of generic QR (📷 domain.name)
- SNI extraction from FakeTLS secret is automatic

## Telemt API 3.4.14-3.4.25

- **Reset quota** — "Reset Quota" button in client card (POST /v1/users/{username}/reset-quota)
- **api_client.py** — new methods: reset_user_quota(), get_config(), patch_config(), system_reload(), get_reload_status()
- **Config editor** — "Config" button in main menu, 6 sections via PATCH /v1/config
- **Runtime reload** — /reload instant|drain, /reload_status, PATCH /v1/config?reload=instant

## Configuration Backup

- **Backup** — reads full telemt.toml from disk (API does not expose access/server/network sections)

## Security Fixes (Dependencies)

- Pillow 12.1.1 → 12.3.0
- setuptools updated in Docker image

## Bug Fixes

- **proxy_checker.py** — rewritten based on check_tg_proxy: raw MTProto, stability, DPI, GeoIP
- **proxy_checker.py** — handle ValueError/OSError in MTProto check
- **bot.py** — simplified proxy logic (AiohttpSession(proxy=))
- **handlers.py** — fixed `fields is {}` → `fields == {}`
- **handlers.py** — replaced deprecated asyncio.get_event_loop() with get_running_loop()
- **handlers.py** — error handling for message deletion
- **handlers.py** — index validation in cb_server_select, cb_users_page, cb_user_toggle
- **scheduler.py** — heartbeat file for Docker HEALTHCHECK
- **scheduler.py** — removed redundant catch (ApiError, Exception)
- **database.py** — absolute database path for systemd
- **formatters.py** — removed duplicate _now_str()
- **export_toml.py** — config path configurable via TELEMT_CONFIG_PATH

## Documentation

- Step-by-step installation for Ubuntu/Debian/CentOS/Alpine
- systemd unit files for bot and agent
- Docker installation
- Proxy agent configuration
- Full configuration reference
- Bilingual README (English + Russian)
- WEB Proxy setup guide
