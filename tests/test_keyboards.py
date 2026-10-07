"""Тесты клавиатур: наличие кнопок reload и лимит callback_data (64 байта)."""

from keyboards import ALERT_LABELS, alerts_kb, config_edit_after_kb, config_edit_fields_kb


def _buttons(kb):
    return [btn for row in kb.inline_keyboard for btn in row]


class TestConfigEditFieldsKb:
    def test_with_reload_buttons(self):
        kb = config_edit_fields_kb("censorship", ["tls_domain"], {}, supports_reload=True)
        texts = [b.text for b in _buttons(kb)]
        assert "💾 Применить" in texts
        assert "⚡ +instant" in texts
        assert "🌙 +drain" in texts
        assert "◀️ Назад" in texts
        assert "◀️ Меню" in texts

    def test_without_reload_buttons(self):
        kb = config_edit_fields_kb("censorship", ["tls_domain"], {}, supports_reload=False)
        texts = [b.text for b in _buttons(kb)]
        assert "💾 Применить" in texts
        assert "⚡ +instant" not in texts
        assert "🌙 +drain" not in texts

    def test_apply_reload_callback_shape(self):
        kb = config_edit_fields_kb("censorship", [], {}, supports_reload=True)
        data = {b.callback_data for b in _buttons(kb)}
        assert "configedit:apply:censorship" in data
        assert "configedit:apply:instant:censorship" in data
        assert "configedit:apply:drain:censorship" in data


class TestConfigEditAfterKb:
    def test_offers_reload_when_needed(self):
        kb = config_edit_after_kb("web", needs_reload=True)
        texts = [b.text for b in _buttons(kb)]
        assert "⚡ Reload instant" in texts
        assert "🌙 Reload drain" in texts
        assert "◀️ К секции" in texts

    def test_no_reload_buttons_when_not_needed(self):
        kb = config_edit_after_kb("web", needs_reload=False)
        texts = [b.text for b in _buttons(kb)]
        assert "⚡ Reload instant" not in texts
        assert "◀️ К секции" in texts


class TestAlertsKb:
    def test_toggle_for_every_alert_type(self):
        # Регрессия: типы алертов в keyboard и handlers разошлись —
        # тумблер not_ready рисовался, но состояние всегда было выключено
        kb = alerts_kb({})
        data = [b.callback_data for b in _buttons(kb)]
        for atype in ALERT_LABELS:
            assert f"alert:toggle:{atype}" in data

    def test_enabled_type_marked_with_check(self):
        kb = alerts_kb({"not_ready": True})
        for b in _buttons(kb):
            if b.callback_data == "alert:toggle:not_ready":
                assert b.text.startswith("✅")

    def test_disabled_type_marked_unchecked(self):
        kb = alerts_kb({})
        for b in _buttons(kb):
            if b.callback_data == "alert:toggle:not_ready":
                assert b.text.startswith("☑️")


class TestCallbackDataLimit:
    """Telegram ограничивает callback_data 64 байтами."""

    def test_all_config_edit_callbacks_within_limit(self):
        for section in ("censorship", "general", "timeouts", "upstreams", "web"):
            kbs = [
                config_edit_fields_kb(section, ["field"], {}, supports_reload=True),
                config_edit_after_kb(section, needs_reload=True),
                config_edit_after_kb(section, needs_reload=False),
            ]
            for kb in kbs:
                for btn in _buttons(kb):
                    assert len(btn.callback_data.encode()) <= 64, (
                        f"{btn.text!r}: {btn.callback_data!r}"
                    )
