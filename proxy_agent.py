#!/usr/bin/env python3
"""
Proxy Check Agent — TCP + TLS + GeoIP проверка.
Только stdlib, никаких зависимостей.

Использование:
  python3 proxy_agent.py [--host 10.8.1.2] [--port 8765] [--token SECRET]
"""

import argparse
import json
import socket
import ssl
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs


TOKEN = ""
TCP_TIMEOUT = 5.0
TLS_TIMEOUT = 8.0


def _classify_tcp_error(e: Exception) -> str:
    msg = str(e).lower()
    if isinstance(e, socket.timeout):
        return "timeout"
    if isinstance(e, ConnectionRefusedError):
        return "connection_refused"
    if isinstance(e, ConnectionResetError) or "reset" in msg:
        return "connection_reset"
    if "unreachable" in msg or "network" in msg:
        return "network_unreachable"
    if "name or service not known" in msg:
        return "dns_error"
    return str(e)[:80]


def _classify_tls_error(e: Exception) -> str:
    msg = str(e).lower()
    if isinstance(e, socket.timeout):
        return "timeout"
    if isinstance(e, ConnectionResetError) or "reset" in msg:
        return "connection_reset"
    if isinstance(e, ssl.SSLError):
        if "eof" in msg or "unexpected eof" in msg:
            return "unexpected_eof"
        if "handshake" in msg:
            return "handshake_failure"
        if "certificate" in msg:
            return "certificate_error"
        if "alert" in msg:
            return "tls_alert"
        return "ssl_error"
    if isinstance(e, ConnectionRefusedError):
        return "connection_refused"
    return str(e)[:80]


def check_tcp(host: str, port: int, timeout: float = TCP_TIMEOUT) -> dict:
    start = time.monotonic()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        rtt_ms = (time.monotonic() - start) * 1000
        sock.close()
        return {"ok": True, "rtt_ms": round(rtt_ms, 1), "error": None, "error_type": None}
    except Exception as e:
        return {
            "ok": False, "rtt_ms": 0,
            "error": str(e)[:100],
            "error_type": _classify_tcp_error(e),
        }


def check_tls(host: str, port: int, sni: str = "", timeout: float = TLS_TIMEOUT) -> dict:
    server_name = sni if sni else host
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    start = time.monotonic()
    try:
        raw = socket.create_connection((host, port), timeout=timeout)
        raw.settimeout(timeout)
        tls = ctx.wrap_socket(raw, server_hostname=server_name)
        rtt_ms = (time.monotonic() - start) * 1000
        tls.close()
        return {"ok": True, "rtt_ms": round(rtt_ms, 1), "error": None, "error_type": None}
    except Exception as e:
        rtt_ms = (time.monotonic() - start) * 1000
        # SSLError после установки соединения — прокси ответил
        if isinstance(e, ssl.SSLError) and rtt_ms > 150:
            return {"ok": True, "rtt_ms": round(rtt_ms, 1), "error": None, "error_type": None}
        return {
            "ok": False, "rtt_ms": round(rtt_ms, 1) if rtt_ms > 0 else 0,
            "error": str(e)[:100],
            "error_type": _classify_tls_error(e),
        }


def get_geoip(host: str) -> dict:
    """Получить GeoIP через ip-api.com (stdlib only)."""
    # Сначала резолвим
    try:
        ip = socket.gethostbyname(host)
    except Exception:
        ip = host

    try:
        import urllib.request
        url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,org"
        req = urllib.request.Request(url, headers={"User-Agent": "proxy-agent/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            if data.get("status") == "success":
                return {
                    "ip": ip,
                    "country": data.get("country", ""),
                    "country_code": data.get("countryCode", ""),
                    "city": data.get("city", ""),
                    "org": data.get("org", ""),
                }
    except Exception:
        pass

    return {"ip": ip, "country": "", "country_code": "", "city": "", "org": ""}


def check_stability(host: str, port: int, count: int = 5, delay: float = 0.3) -> dict:
    """Проверка стабильности — N подключений подряд."""
    results = []
    for i in range(count):
        start = time.monotonic()
        try:
            sock = socket.create_connection((host, port), timeout=5)
            rtt = (time.monotonic() - start) * 1000
            sock.close()
            results.append({"ok": True, "rtt_ms": round(rtt, 1)})
        except Exception:
            results.append({"ok": False, "rtt_ms": 0})
        if i < count - 1:
            time.sleep(delay)

    success = sum(1 for r in results if r["ok"])
    rtts = [r["rtt_ms"] for r in results if r["ok"]]
    avg_rtt = round(sum(rtts) / len(rtts), 1) if rtts else 0
    min_rtt = round(min(rtts), 1) if rtts else 0
    max_rtt = round(max(rtts), 1) if rtts else 0

    pattern = "stable"
    if success == 0:
        pattern = "blocked"
    elif success < count:
        pattern = "unstable"

    return {
        "total": count, "success": success,
        "success_rate": round(success / count * 100),
        "avg_rtt_ms": avg_rtt, "min_rtt_ms": min_rtt,
        "max_rtt_ms": max_rtt, "pattern": pattern,
    }


class AgentHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if TOKEN:
            token = self.headers.get("X-Token", "")
            if token != TOKEN:
                self._send_json({"error": "unauthorized"}, 401)
                return

        if parsed.path == "/health":
            self._send_json({"status": "ok"})
            return

        if parsed.path == "/check":
            params = parse_qs(parsed.query)
            host = params.get("host", [""])[0].strip()
            sni = params.get("sni", [""])[0].strip()
            try:
                port = int(params.get("port", ["443"])[0])
            except ValueError:
                self._send_json({"error": "invalid port"}, 400)
                return

            if not host:
                self._send_json({"error": "host required"}, 400)
                return

            tcp = check_tcp(host, port)
            result = {"tcp": tcp}

            if tcp["ok"]:
                result["tls"] = check_tls(host, port, sni=sni)
            else:
                result["tls"] = None

            self._send_json(result)
            return

        if parsed.path == "/check_full":
            """Полная проверка: TCP + TLS + GeoIP + стабильность."""
            params = parse_qs(parsed.query)
            host = params.get("host", [""])[0].strip()
            sni = params.get("sni", [""])[0].strip()
            try:
                port = int(params.get("port", ["443"])[0])
            except ValueError:
                self._send_json({"error": "invalid port"}, 400)
                return

            if not host:
                self._send_json({"error": "host required"}, 400)
                return

            tcp = check_tcp(host, port)
            result = {"tcp": tcp, "tls": None, "geoip": {}, "stability": None}

            if tcp["ok"]:
                result["tls"] = check_tls(host, port, sni=sni)
                result["stability"] = check_stability(host, port, count=5, delay=0.3)

            result["geoip"] = get_geoip(host)

            self._send_json(result)
            return

        self._send_json({"error": "not found"}, 404)


def main():
    global TOKEN
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    if args.token:
        TOKEN = args.token

    server = HTTPServer((args.host, args.port), AgentHandler)
    print(f"Proxy agent on {args.host}:{args.port} (TCP + TLS + GeoIP)")
    server.serve_forever()


if __name__ == "__main__":
    main()
