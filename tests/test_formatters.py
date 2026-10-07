"""Тесты formatters.py: SNI/секрет из ссылок, tg://webproxy, deep links."""

import base64

from formatters import (
    _extract_sni_from_link,
    _extract_secret_from_link,
    make_webproxy_link,
    tg_deep_link,
)

SECRET_HEX = "0123456789abcdef0123456789abcdef"
DOMAIN = "cloudfront.com"
FAKETLS_SECRET = "ee" + "00" * 16 + DOMAIN.encode().hex()


def _proxy_link(secret: str) -> str:
    return f"tg://proxy?server=1.2.3.4&port=443&secret={secret}"


class TestExtractSni:
    def test_faketls_link(self):
        assert _extract_sni_from_link(_proxy_link(FAKETLS_SECRET)) == DOMAIN

    def test_dd_link_has_no_sni(self):
        assert _extract_sni_from_link(_proxy_link("dd" + SECRET_HEX)) == ""

    def test_empty_secret(self):
        assert _extract_sni_from_link("tg://proxy?server=1.2.3.4&port=443") == ""


class TestExtractSecret:
    def test_dd_link(self):
        assert _extract_secret_from_link(_proxy_link("dd" + SECRET_HEX)) == SECRET_HEX

    def test_ee_link(self):
        # ee + 32 hex + SNI → секрет без префикса
        assert _extract_secret_from_link(_proxy_link(FAKETLS_SECRET)) == "00" * 16

    def test_short_secret(self):
        assert _extract_secret_from_link(_proxy_link("aabb")) == ""


class TestMakeWebproxyLink:
    def test_dd_no_path(self):
        link = make_webproxy_link("proxy.example.com", SECRET_HEX)
        assert link == f"tg://webproxy?server=proxy.example.com&secret=dd{SECRET_HEX}"

    def test_plain_no_path(self):
        link = make_webproxy_link("proxy.example.com", SECRET_HEX, mode="plain")
        assert link == f"tg://webproxy?server=proxy.example.com&secret={SECRET_HEX}"

    def test_with_base_path(self):
        link = make_webproxy_link("proxy.example.com", SECRET_HEX, base_path="telegram/web")
        raw = bytes.fromhex(SECRET_HEX)
        marked = b"\x70\xdd" + raw
        expected_secret = base64.urlsafe_b64encode(marked).decode().rstrip("=")
        assert link == (
            "tg://webproxy?server=proxy.example.com%2Ftelegram%2Fweb"
            f"&secret={expected_secret}"
        )

    def test_base_path_slashes_normalized(self):
        a = make_webproxy_link("h", SECRET_HEX, base_path="web")
        b = make_webproxy_link("h", SECRET_HEX, base_path="/web/")
        assert a == b


class TestTgDeepLink:
    def test_tme_proxy(self):
        url = "https://t.me/proxy?server=1.2.3.4&port=443&secret=ab"
        assert tg_deep_link(url) == "tg://proxy?server=1.2.3.4&port=443&secret=ab"

    def test_tme_webproxy(self):
        url = "https://t.me/webproxy?server=h&secret=ab"
        assert tg_deep_link(url) == "tg://webproxy?server=h&secret=ab"

    def test_tg_unchanged(self):
        url = "tg://proxy?server=1.2.3.4&port=443&secret=ab"
        assert tg_deep_link(url) == url

    def test_other_url_unchanged(self):
        assert tg_deep_link("https://example.com/x") == "https://example.com/x"
