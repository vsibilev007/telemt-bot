"""
Настройка логирования бота.

Возможности:
- Цветной вывод в stdout (ANSI, отключается через NO_COLOR=1)
- Ротация файла логов (LOG_FILE, по умолчанию выключено)
- Уровень логов через LOG_LEVEL (по умолчанию INFO)
- Подавление шумных библиотек (aiohttp, apscheduler)
- Читаемый формат: время | уровень | модуль | сообщение
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys


# ─── ANSI цвета ───────────────────────────────────────────────────────────────

_COLORS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
}
_RESET = "\033[0m"
_GREY  = "\033[90m"
_BOLD  = "\033[1m"


class ColorFormatter(logging.Formatter):
    """Форматтер с ANSI-цветами для stdout."""

    FMT = "{grey}{time}{reset} {color}{level:<8}{reset} {grey}{name}{reset}  {msg}"

    def __init__(self, use_color: bool = True):
        super().__init__()
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        # Укорачиваем имя модуля до последних 2 сегментов
        name_parts = record.name.split(".")
        short_name = ".".join(name_parts[-2:]) if len(name_parts) > 1 else record.name

        time_str = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        msg = record.getMessage()

        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)

        if self._use_color:
            color = _COLORS.get(record.levelname, "")
            return self.FMT.format(
                grey=_GREY, reset=_RESET, color=color,
                time=time_str,
                level=record.levelname,
                name=short_name,
                msg=msg,
            )
        return f"{time_str} [{record.levelname:<8}] {short_name}: {msg}"


class PlainFormatter(logging.Formatter):
    """Простой форматтер для файла (без ANSI)."""
    def format(self, record: logging.LogRecord) -> str:
        time_str = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        name_parts = record.name.split(".")
        short_name = ".".join(name_parts[-2:]) if len(name_parts) > 1 else record.name
        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)
        return f"{time_str} [{record.levelname:<8}] {short_name}: {msg}"


# ─── Настройка ────────────────────────────────────────────────────────────────

def setup_logging() -> None:
    """
    Вызывать один раз при старте бота (до создания Bot/Dispatcher).

    Переменные окружения:
      LOG_LEVEL   — DEBUG / INFO / WARNING / ERROR  (default: INFO)
      LOG_FILE    — путь к файлу логов              (default: выключено)
      LOG_MAX_MB  — макс. размер файла в МБ         (default: 10)
      LOG_BACKUPS — кол-во резервных файлов         (default: 3)
      NO_COLOR    — любое значение отключает цвета  (default: цвета включены)
    """
    def _clean(val: str) -> str:
        """'10  # comment' → '10'  (защита от скопированных строк из .env.example)"""
        return val.split("#")[0].strip()

    level_name = _clean(os.environ.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    use_color = not os.environ.get("NO_COLOR") and sys.stdout.isatty()
    log_file  = _clean(os.environ.get("LOG_FILE", ""))
    max_mb    = int(_clean(os.environ.get("LOG_MAX_MB", "10")) or "10")
    backups   = int(_clean(os.environ.get("LOG_BACKUPS", "3")) or "3")

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)   # root ловит всё, фильтрация — на хэндлерах

    # ── stdout handler ────────────────────────────────────────────────────────
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(ColorFormatter(use_color=use_color))
    root.addHandler(stdout_handler)

    # ── file handler (опционально) ────────────────────────────────────────────
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_mb * 1024 * 1024,
            backupCount=backups,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)   # в файл пишем всё
        file_handler.setFormatter(PlainFormatter())
        root.addHandler(file_handler)

    # ── Подавляем шумные библиотеки ───────────────────────────────────────────
    _quiet = {
        "aiohttp":              logging.WARNING,
        "aiohttp.access":       logging.ERROR,
        "apscheduler":          logging.WARNING,
        "apscheduler.scheduler":logging.WARNING,
        "aiogram":              logging.WARNING,
        "aiogram.event":        logging.ERROR,
        "asyncio":              logging.WARNING,
        "PIL":                  logging.WARNING,
        # Telethon — подавляем INFO/WARNING от MTProto подключений
        "telethon":             logging.ERROR,
        "telethon.network":     logging.ERROR,
        "telethon.crypto":      logging.ERROR,
        "telethon.client":      logging.ERROR,
    }
    for name, lvl in _quiet.items():
        logging.getLogger(name).setLevel(lvl)

    logger = logging.getLogger(__name__)
    logger.debug(
        "Логирование настроено: level=%s, color=%s, file=%s",
        level_name, use_color, log_file or "выключен",
    )
