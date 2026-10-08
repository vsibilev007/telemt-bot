"""Тесты отображения WEB-сессий: короткий ID и кнопки."""

from formatters import format_web_sessions
from keyboards import web_sessions_kb


def _session(n: int, user: str = "alice") -> dict:
    # Telemt генерирует ID как zero-padded u64 счётчик: ws1.<instance>.<16 hex>
    return {
        "session_ref": f"ws1.0123456789abcdef0123456789abcdef.{n:016x}",
        "user": user,
        "client_ip": "203.0.113.10",
        "carrier": "https-lanes",
        "state": "healthy",
        "streams": 3,
        "age_ms": 1754 * 60 * 1000,
        "idle_ms": 3 * 1000,
    }


class TestShortSessionId:
    def test_list_shows_counter_tail_not_zeros(self):
        # Регрессия: [:8] показывал «00000000» у всех сессий, потому что
        # ID — zero-padded счётчик; различимы только последние 8 символов
        data = {"sessions": [_session(1), _session(2)], "total": 2}
        text = format_web_sessions(data)
        assert "00000001" in text
        assert "00000002" in text
        assert "<code>00000000</code>" not in text

    def test_button_label_shows_counter_tail(self):
        kb = web_sessions_kb([_session(7, "Alena")])
        btn = kb.inline_keyboard[0][0]
        assert btn.text.endswith("(00000007)")
        # callback несёт полный 16-hex ID — закрытие сессии не ломается
        assert btn.callback_data == (
            "web:s:0000000000000007"
        )

    def test_idle_from_ms_not_overwritten(self):
        # Регрессия: idle_s из idle_ms перетирался d.get("idle_secs", 0)
        text = format_web_sessions({"sessions": [_session(1)], "total": 1})
        assert "idle=3с" in text
