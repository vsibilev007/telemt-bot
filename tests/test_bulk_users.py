"""Тесты массовых операций: парсер bulk-спецификации и чекбокс-клавиатура."""

import pytest

from handlers import _bulk_names, _parse_bulk_spec
from keyboards import users_list_kb, users_sel_delete_confirm_kb


def _users(n: int = 3) -> list[dict]:
    return [
        {"username": f"user{i}", "current_connections": 0, "total_octets": 0,
         "active_unique_ips": 0}
        for i in range(1, n + 1)
    ]


def _buttons(kb):
    return [btn for row in kb.inline_keyboard for btn in row]


class TestBulkNames:
    def test_auto_index(self):
        assert _bulk_names("guest", 3) == ["guest1", "guest2", "guest3"]

    def test_placeholder(self):
        assert _bulk_names("vpn{n}", 2) == ["vpn1", "vpn2"]


class TestParseBulkSpec:
    def test_basic(self):
        names, days, quota = _parse_bulk_spec("guest 5 30")
        assert names == [f"guest{i}" for i in range(1, 6)]
        assert days == 30
        assert quota == 0

    def test_placeholder_and_quota(self):
        names, days, quota = _parse_bulk_spec("vpn{n} 3 7 50")
        assert names == ["vpn1", "vpn2", "vpn3"]
        assert days == 7
        assert quota == 50

    def test_zero_days_no_expiration(self):
        _, days, _ = _parse_bulk_spec("guest 10 0")
        assert days == 0

    def test_too_few_args(self):
        with pytest.raises(ValueError):
            _parse_bulk_spec("guest 5")

    def test_count_range(self):
        with pytest.raises(ValueError):
            _parse_bulk_spec("guest 0 30")
        with pytest.raises(ValueError):
            _parse_bulk_spec("guest 51 30")

    def test_bad_days(self):
        with pytest.raises(ValueError):
            _parse_bulk_spec("guest 5 abc")

    def test_bad_name_chars(self):
        with pytest.raises(ValueError):
            _parse_bulk_spec("привет! 2 30")

    def test_name_too_long(self):
        with pytest.raises(ValueError):
            _parse_bulk_spec("g" * 45 + " 2 30")

    def test_quota_negative(self):
        with pytest.raises(ValueError):
            _parse_bulk_spec("guest 2 30 -5")


class TestUsersListKbModes:
    def test_normal_mode_new_buttons(self):
        kb = users_list_kb(_users(), 0)
        texts = [b.text for b in _buttons(kb)]
        assert "➕ Новый" in texts
        assert "➕➕ Массово" in texts
        assert "☑️ Выбрать" in texts

    def test_sel_mode_checkboxes(self):
        kb = users_list_kb(_users(), 0, sel_mode=True, selected={"user2"})
        btns = _buttons(kb)
        marks = {b.callback_data: b.text for b in btns if b.callback_data.startswith("user:sel:")}
        assert marks["user:sel:user1"].startswith("⬜")
        assert marks["user:sel:user2"].startswith("☑️")
        # Кнопка просмотра в режиме выбора не используется
        assert not any(b.callback_data.startswith("user:view:") for b in btns)

    def test_sel_mode_actions_with_count(self):
        kb = users_list_kb(_users(), 0, sel_mode=True, selected={"user1", "user3"})
        texts = [b.text for b in _buttons(kb)]
        assert "🔴 Откл (2)" in texts
        assert "✅ Вкл (2)" in texts
        assert "🗑 Удалить (2)" in texts
        assert "✔ Готово" in texts

    def test_sel_mode_zero_count(self):
        kb = users_list_kb(_users(), 0, sel_mode=True, selected=set())
        texts = [b.text for b in _buttons(kb)]
        assert "🔴 Откл (0)" in texts
        assert "🗑 Удалить (0)" in texts

    def test_sel_delete_confirm_kb(self):
        kb = users_sel_delete_confirm_kb(3)
        texts = [b.text for b in _buttons(kb)]
        assert "🗑 Да, удалить (3)" in texts
        assert "◀ Отмена" in texts

    def test_all_callbacks_within_64_bytes(self):
        # Имена до 40 символов (BULK_NAME_MAX) должны влезать во все callback
        long_users = [{"username": "n" * 40, "current_connections": 0,
                       "total_octets": 0, "active_unique_ips": 0}]
        for kb in (
            users_list_kb(long_users, 0),
            users_list_kb(long_users, 0, sel_mode=True, selected={"n" * 40}),
            users_sel_delete_confirm_kb(1),
        ):
            for b in _buttons(kb):
                assert len(b.callback_data.encode()) <= 64, b.callback_data
