"""Покрытие i18n: каждый t()-ключ из кода определён; у каждого ключа есть ru+en;
значения проходят .format() с плейсхолдерами из call-sites."""

import ast
import os

from keyboards import ALERT_LABELS
import i18n
from i18n import iter_keys, _TABLES
from i18n import get_lang

CODE_MODULES = ("handlers.py", "keyboards.py", "formatters.py", "scheduler.py", "bot.py")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _call_sites():
    """Все статические t("ключ", ...) вызовы в исходниках бота."""
    for fname in CODE_MODULES:
        src = open(os.path.join(ROOT, fname), encoding="utf8").read()
        tree = ast.parse(src, filename=fname)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "t"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value != "fmt.common.no_links"
            ):
                yield fname, node.lineno, node.args[0].value, node


def _row(key):
    for table in _TABLES:
        if key in table:
            return table[key]
    return None


def test_all_defined_keys_have_both_languages():
    for key in iter_keys():
        row = _row(key)
        assert row is not None
        assert "ru" in row, f"{key}: нет ru"
        assert "en" in row, f"{key}: нет en"


def test_static_keys_are_defined():
    missing = [
        f"{fname}:{line}: {key!r}"
        for fname, line, key, _ in _call_sites()
        if key not in set(iter_keys())
    ]
    m = [x for x in missing]
    assert not m, "неопределённые ключи t():\n" + "\n".join(m)


def test_alert_labels_are_defined():
    known = set(iter_keys())
    bad = [k for k in ALERT_LABELS.values() if k not in known]
    assert not bad, f"ALERT_LABELS ссылается на несуществующие ключи: {bad}"


def test_placeholders_match_call_kwargs():
    for fname, line, key, node in _call_sites():
        row = _row(key)
        if row is None:
            continue
        kwargs = {kw.arg: "x" for kw in node.keywords}
        for lang, val in row.items():
            try:
                val.format(**kwargs)
            except (IndexError, KeyError, ValueError):
                # числовые плейсхолдеры ({pct:.0f}, {n:,}) не принимают str
                try:
                    val.format(**{k: 1 for k in kwargs})
                except (IndexError, KeyError, ValueError) as e:
                    raise AssertionError(f"{fname}:{line}: {key} [{lang}]=format упал: {e}")


def test_render_ru_and_en_smoke():
    """Локации переключаются; вернуть ru, чтобы не мешать другим тестам."""
    original = get_lang()
    try:
        for lang in ("ru", "en"):
            i18n.set_lang(lang)
            assert get_lang() == lang
            for key in ("cmd.menu", "h.users.header"):
                i18n.t(key)
    finally:
        i18n.set_lang(original)
