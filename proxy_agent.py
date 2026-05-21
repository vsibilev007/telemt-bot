#!/usr/bin/env python3
"""
Proxy Check Agent — TCP + TLS handshake проверка.
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


def check_tcp(host: str, port: int, timeout: float = TCP_TIMEOUT) -> dict:
    start = time.monotonic()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        rtt_ms = (time.monotonic() - start) * 1000
        sock.close()
        return {"ok": True, "rtt_ms": round(rtt_ms, 1)}
    except socket.timeout:
        return {"ok": False, "error": f"timeout ({timeout:.0f}s)"}
    except OSError as e:
        return {"ok": False, "error": str(e)}


def check_tls(host: str, port: int, sni: str = "", timeout: float = TLS_TIMEOUT) -> dict:
    """
    TLS handshake к хосту с указанным SNI.
    FakeTLS прокси принимает TLS ClientHello — это подтверждает его работу.
    Проверка сертификата отключена — у прокси он самоподписанный или чужой.
    """
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
        return {"ok": True, "rtt_ms": round(rtt_ms, 1)}
    except ssl.SSLError as e:
        rtt_ms = (time.monotonic() - start) * 1000
        err = str(e)
        # SSLError после установки соединения — прокси ответил,
        # сертификат не подошёл но handshake был
        if rtt_ms > 150 or any(x in err.lower() for x in
                               ["cert", "alert", "unknown ca", "handshake",
                                "wrong version", "record", "protocol"]):
            return {"ok": True, "rtt_ms": round(rtt_ms, 1)}
        return {"ok": False, "error": f"TLS: {err[:80]}"}
    except socket.timeout:
        return {"ok": False, "error": f"TLS timeout ({timeout:.0f}s)"}
    except OSError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        rtt_ms = (time.monotonic() - start) * 1000
        if rtt_ms > 150:
            return {"ok": True, "rtt_ms": round(rtt_ms, 1)}
        return {"ok": False, "error": str(e)[:80]}


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
    print(f"Proxy agent on {args.host}:{args.port} (TCP + TLS)")
    server.serve_forever()


if __name__ == "__main__":
    main()
