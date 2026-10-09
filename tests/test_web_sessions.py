"""Тесты отображения WEB-сессий: короткий ID, кнопки, карточка сессии."""

from formatters import format_web_session_detail, format_web_sessions
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


class TestSessionDetail:
    LONG_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )

    def _detail(self) -> dict:
        d = _session(1, "Alena")
        d.update(
            host="list.lympik.ru",
            attempt=3,
            client_class="browser",
            automatic=True,
            health_publication="published",
            websocket_active=False,
            pending_bytes=0,
            control_bytes=0,
            age_ms=2369 * 60 * 1000 + 12_000,  # «2369м 12с» из багрепорта
            idle_ms=500,
            peer_idle_ms=1500,
            reconnect_grace_ms=90_000,
            peer_deadline_remaining_ms=60_000,
            user_agent=self.LONG_UA,
            key_id="7a75a79bfedac30d",
            negotiation_remaining_ms=12_000,
        )
        return d

    def test_age_human_readable(self):
        # Регрессия: Age: 2369м 12с → 142152с = 1д 15ч 29м 12с
        text = format_web_session_detail(self._detail())
        assert "Age: 1д 15ч 29м 12с" in text

    def test_list_age_human_readable(self):
        # Регрессия: age=1754м в списке → 105240с = 1д 5ч 14м 0с
        text = format_web_sessions({"sessions": [_session(1)], "total": 1})
        assert "age=1д 5ч 14м 0с" in text
        assert "age=1754м" not in text

    def test_ua_not_truncated(self):
        text = format_web_session_detail(self._detail())
        assert self.LONG_UA in text
        assert "…" not in text

    def test_negotiation_field_name(self):
        # Регрессия: читалось несуществующее negotiation_time_remaining_secs
        text = format_web_session_detail(self._detail())
        assert "Negotiation left: 12с" in text

    def test_new_fields_shown(self):
        text = format_web_session_detail(self._detail())
        assert "health: published" in text
        assert "Class: browser" in text
        assert "(auto)" in text
        assert "Peer idle: 1с" in text
        assert "Reconnect grace: 1м 30с" in text
        assert "Peer deadline: 1м" in text

    def test_websocket_active_bool(self):
        # websocket_active в API — булево, а не счётчик
        d = self._detail()
        d["websocket_active"] = True
        text = format_web_session_detail(d)
        assert "WebSocket: активен" in text
        assert "WebSocket connections: True" not in text
