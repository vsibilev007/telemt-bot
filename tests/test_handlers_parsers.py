"""Тесты парсеров handlers.py: _parse_exp, _parse_config_value, _version_at_least."""

from datetime import datetime, timezone

from handlers import _parse_config_value, _parse_exp, _version_at_least


class TestParseExp:
    def test_rfc3339_utc(self):
        dt = _parse_exp("2026-10-07T12:00:00Z")
        assert dt == datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)

    def test_rfc3339_offset(self):
        dt = _parse_exp("2026-10-07T12:00:00+03:00")
        assert dt is not None
        assert dt.utcoffset().total_seconds() == 3 * 3600

    def test_garbage(self):
        assert _parse_exp("garbage") is None

    def test_empty(self):
        assert _parse_exp("") is None


class TestParseConfigValue:
    def test_bools(self):
        assert _parse_config_value("true") is True
        assert _parse_config_value("True") is True
        assert _parse_config_value("false") is False

    def test_nulls(self):
        assert _parse_config_value("null") is None
        assert _parse_config_value("none") is None
        assert _parse_config_value("нет") is None

    def test_int(self):
        assert _parse_config_value("42") == 42

    def test_int_with_spaces(self):
        assert _parse_config_value("  42 ") == 42

    def test_float(self):
        assert _parse_config_value("3.14") == 3.14

    def test_json_list(self):
        assert _parse_config_value("[1, 2, 3]") == [1, 2, 3]

    def test_json_dict(self):
        assert _parse_config_value('{"a": 1}') == {"a": 1}

    def test_json_string_keeps_quotes_stripped(self):
        assert _parse_config_value('"hello"') == "hello"

    def test_plain_string(self):
        assert _parse_config_value("hello world") == "hello world"

    def test_domain_string(self):
        assert _parse_config_value("front.example.com") == "front.example.com"

    def test_broken_json_is_string(self):
        assert _parse_config_value("[1, 2") == "[1, 2"


class TestVersionAtLeast:
    def test_equal(self):
        assert _version_at_least("3.4.25", 3, 4, 25) is True

    def test_newer(self):
        assert _version_at_least("3.5.11", 3, 4, 25) is True

    def test_older(self):
        assert _version_at_least("3.4.14", 3, 4, 25) is False

    def test_short_version_padded(self):
        assert _version_at_least("3.4", 3, 4, 0) is True
        assert _version_at_least("3.4", 3, 4, 25) is False

    def test_empty_version_is_permissive(self):
        assert _version_at_least("", 3, 4, 25) is True

    def test_garbage_version_is_permissive(self):
        assert _version_at_least("garbage", 3, 4, 25) is True
