"""
Работа с временными зонами.

Переменная окружения TZ задаёт локальное время бота.
Примеры: TZ=Europe/Moscow, TZ=Asia/Yekaterinburg, TZ=UTC

Если TZ не задана — используется системная зона сервера.
Стандартная переменная TZ подхватывается Python автоматически,
поэтому datetime.now().astimezone() всегда вернёт правильное время.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone, timedelta


def _local_tz() -> timezone:
    """Возвращает текущую локальную timezone как объект timezone."""
    offset = -time.timezone if time.daylight == 0 else -time.altzone
    return timezone(timedelta(seconds=offset))


def now_local() -> datetime:
    """Текущее время в локальной зоне (с учётом TZ из .env)."""
    return datetime.now(_local_tz())


def from_epoch(ts: int) -> datetime:
    """Unix timestamp → datetime в локальной зоне."""
    return datetime.fromtimestamp(ts, tz=_local_tz())


def now_str() -> str:
    """Строка вида '14:32:05 MSK' для подписи 'Обновлено:'."""
    dt = now_local()
    tz_name = os.environ.get("TZ", "").split("/")[-1] or _abbr()
    return dt.strftime(f"%H:%M:%S {tz_name}")


def fmt_dt(ts: int, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Форматирует unix timestamp для вывода пользователю."""
    return from_epoch(ts).strftime(fmt)


def fmt_date(ts: int) -> str:
    return from_epoch(ts).strftime("%Y-%m-%d")


def fmt_datetime(ts: int) -> str:
    return from_epoch(ts).strftime("%Y-%m-%d %H:%M")


def _abbr() -> str:
    """Короткое название зоны (MSK, EKT, UTC...)."""
    return time.strftime("%Z")
