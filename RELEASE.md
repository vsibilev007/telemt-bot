# Release Notes

## WEB Proxy Support (Telemt 3.5.5+)

- **WEB Proxy menu** — new button in main menu (visible only for Telemt 3.5.5+)
- **Status** — lifecycle, runtime, limits, streams, sessions, learning, debug
- **Sessions** — list active WEB sessions with pagination and details (IP, carrier, user agent)
- **Management** — close sessions, clear debug records, reset carrier learning
- **WEB links** — auto-generate `tg://webproxy?server=HOST&secret=ddSECRET` for users
- **Auto-profiles** — WEB profile automatically added when creating users
- **Auto-removal** — WEB profile removed before deleting access user
- **Version check** — for Telemt 3.4.25 and below, only TLS links are shown
- **api_client.py** — new methods: get_web_status(), get_web_sessions(), get_web_session(), close_web_sessions(), clear_web_debug(), reset_web_carrier_learning()
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
