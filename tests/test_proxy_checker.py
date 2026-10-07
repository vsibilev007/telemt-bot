"""Тесты parse_proxy_url / _decode_secret — разбор tg://proxy ссылок."""

import base64

from proxy_checker import _decode_secret, parse_proxy_url

SIMPLE_SECRET = "0123456789abcdef0123456789abcdef"
DD_SECRET = "dd" + SIMPLE_SECRET
DOMAIN = "cloudfront.com"
# ee + 16 байт префикса + домен (SNI читается с байта 17)
FAKETLS_SECRET = "ee" + "00" * 16 + DOMAIN.encode().hex()


def _link(secret: str, server: str = "1.2.3.4", port: int = 443) -> str:
    return f"tg://proxy?server={server}&port={port}&secret={secret}"


class TestParseProxyUrl:
    def test_simple_secret(self):
        info = parse_proxy_url(_link(SIMPLE_SECRET))
        assert info is not None
        assert info.server == "1.2.3.4"
        assert info.port == 443
        assert info.secret_type == "simple"
        assert info.sni == ""

    def test_dd_secret(self):
        info = parse_proxy_url(_link(DD_SECRET))
        assert info is not None
        assert info.secret_type == "dd"
        assert info.sni == ""

    def test_faketls_secret_and_sni(self):
        info = parse_proxy_url(_link(FAKETLS_SECRET))
        assert info is not None
        assert info.secret_type == "faketls"
        assert info.sni == DOMAIN

    def test_tme_link_converted(self):
        info = parse_proxy_url(f"https://t.me/proxy?server=1.2.3.4&port=443&secret={SIMPLE_SECRET}")
        assert info is not None
        assert info.server == "1.2.3.4"

    def test_port_default(self):
        info = parse_proxy_url(f"tg://proxy?server=1.2.3.4&secret={SIMPLE_SECRET}")
        assert info is not None
        assert info.port == 443

    def test_port_invalid_falls_back(self):
        info = parse_proxy_url(f"tg://proxy?server=1.2.3.4&port=abc&secret={SIMPLE_SECRET}")
        assert info is not None
        assert info.port == 443

    def test_not_proxy_url(self):
        assert parse_proxy_url("https://example.com") is None

    def test_missing_secret(self):
        assert parse_proxy_url("tg://proxy?server=1.2.3.4&port=443") is None

    def test_missing_server(self):
        assert parse_proxy_url(f"tg://proxy?port=443&secret={SIMPLE_SECRET}") is None

    def test_whitespace_tolerated(self):
        info = parse_proxy_url(f"  {_link(SIMPLE_SECRET)}\n")
        assert info is not None
        assert info.server == "1.2.3.4"


class TestDecodeSecret:
    def test_hex(self):
        assert _decode_secret(SIMPLE_SECRET) == bytes.fromhex(SIMPLE_SECRET)

    def test_base64url(self):
        raw = b"\xee" + b"\x01" * 15
        b64 = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        assert _decode_secret(b64) == raw

    def test_non_alphabet_chars_stripped(self):
        # base64url-декодер игнорирует символы вне алфавита
        assert _decode_secret("!!!") == b""
