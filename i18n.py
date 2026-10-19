"""
Мультиязычность бота: BOT_LANG=ru|en (по умолчанию ru).

Словари разбиты по модулям-источникам, чтобы не сваливать все ключи в
один файл: i18n_core (общие/меню команд), i18n_keyboards (кнопки),
i18n_handlers (тексты хендлеров), i18n_formatters (шапки ответов),
i18n_scheduler (алерты). Ключи глобально уникальны и имеют префикс
модуля: cmd.*, common.*, kb.*, h.*, fmt.*, sch.*.

Значение — словарь {"ru": "...", "en": "..."}. Параметризованные строки
используют {name}-плейсхолдеры и вызываются t("key", name=x).
"""

from __future__ import annotations

import logging

from i18n_core import CORE
from i18n_formatters import FORMATTERS
from i18n_handlers import HANDLERS
from i18n_keyboards import KEYBOARDS
from i18n_scheduler import SCHEDULER

logger = logging.getLogger(__name__)

_TABLES: tuple[dict[str, dict[str, str]], ...] = (
    CORE, KEYBOARDS, HANDLERS, FORMATTERS, SCHEDULER,
)

_LANG = "ru"
_warned_missing: set[str] = set()


def set_lang(lang: str) -> None:
    global _LANG
    lang = (lang or "ru").strip().lower()
    if lang not in ("ru", "en"):
        logger.warning("Неизвестный язык %r — остаёмся на ru", lang)
        lang = "ru"
    _LANG = lang


def get_lang() -> str:
    return _LANG


def t(key: str, **kw) -> str:
    """Перевод по ключу с фолбэком на ru и на сам ключ."""
    row = None
    for table in _TABLES:
        if key in table:
            row = table[key]
            break
    if row is None:
        if key not in _warned_missing:
            _warned_missing.add(key)
            logger.warning("i18n: неизвестный ключ %s", key)
        return key
    val = row.get(_LANG) or row.get("ru") or key
    if kw:
        return val.format(**kw)
    return val


def iter_keys():
    """Все известные ключи — для теста покрытия."""
    for table in _TABLES:
        yield from table.keys()
