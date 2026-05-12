"""
Генерация графиков трафика через matplotlib.
Без внешних сервисов — всё рендерится локально в BytesIO.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Optional

# matplotlib импортируем лениво — не все деплои имеют его
try:
    import matplotlib
    matplotlib.use("Agg")  # без GUI, рендер в файл
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import FuncFormatter
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


# ─── Тема ─────────────────────────────────────────────────────────────────────

_BG       = "#1e2029"
_FG       = "#e0e0e0"
_GRID     = "#2e3040"
_ACCENT   = "#4f9eff"
_ACCENT2  = "#ff6b6b"
_GREEN    = "#50fa7b"
_ORANGE   = "#ffb86c"


def _apply_theme(fig, ax):
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    ax.tick_params(colors=_FG, labelsize=8)
    ax.xaxis.label.set_color(_FG)
    ax.yaxis.label.set_color(_FG)
    ax.title.set_color(_FG)
    for spine in ax.spines.values():
        spine.set_color(_GRID)
    ax.grid(True, color=_GRID, linewidth=0.6, linestyle="--", alpha=0.7)


def _bytes_fmt(value: float, _pos=None) -> str:
    for unit, thr in [("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)]:
        if value >= thr:
            return f"{value / thr:.1f}{unit}"
    return f"{value:.0f}B"


# ─── График истории трафика одного клиента ────────────────────────────────────

def render_user_traffic(
    rows: list[dict],
    username: str,
    days: int,
    server_name: str = "",
) -> Optional[io.BytesIO]:
    """
    rows: список dict с ключами sampled_at (unix), octets, connections
    Возвращает BytesIO с PNG или None если matplotlib недоступен / мало данных.
    """
    if not HAS_MPL or len(rows) < 2:
        return None

    # Вычисляем дельты между снимками (реальный трафик за интервал)
    times, deltas, conns = [], [], []
    for i in range(1, len(rows)):
        dt = datetime.fromtimestamp(rows[i]["sampled_at"], tz=timezone.utc)
        d = max(0, rows[i]["octets"] - rows[i - 1]["octets"])
        times.append(dt)
        deltas.append(d)
        conns.append(rows[i]["connections"])

    total = sum(deltas)

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(9, 5),
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.35},
    )

    # ── Трафик (верхний график) ───────────────────────────────────────────────
    ax1.fill_between(times, deltas, alpha=0.25, color=_ACCENT)
    ax1.plot(times, deltas, color=_ACCENT, linewidth=1.4, marker=".", markersize=3)
    ax1.set_title(
        f"Трафик — {username}  ({days}д, всего {_bytes_fmt(total)})"
        + (f"  •  {server_name}" if server_name else ""),
        fontsize=10, pad=8,
    )
    ax1.yaxis.set_major_formatter(FuncFormatter(_bytes_fmt))
    _apply_theme(fig, ax1)

    # ── Соединения (нижний график) ────────────────────────────────────────────
    ax2.bar(times, conns, width=0.008, color=_GREEN, alpha=0.7)
    ax2.set_title("Соединения", fontsize=8, pad=4)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}"))
    _apply_theme(fig, ax2)

    # Форматируем ось X в зависимости от периода
    for ax in (ax1, ax2):
        if days <= 1:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        elif days <= 7:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=25, ha="right", fontsize=7)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    buf.seek(0)
    return buf


# ─── Сводный график топ-клиентов (traffic report) ────────────────────────────

def render_traffic_report(
    deltas: list[dict],
    days: int,
    server_name: str = "",
    top_n: int = 15,
) -> Optional[io.BytesIO]:
    """
    deltas: список dict с ключами username, delta_bytes
    Горизонтальная bar-chart топ клиентов по трафику за период.
    """
    if not HAS_MPL or not deltas:
        return None

    top = deltas[:top_n]
    names  = [d["username"] for d in reversed(top)]
    values = [d["delta_bytes"] for d in reversed(top)]

    fig, ax = plt.subplots(figsize=(9, max(4, len(names) * 0.42)))

    colors = [_ACCENT if v == max(values) else _ACCENT2 if v > max(values) * 0.5 else _GRID
              for v in values]
    bars = ax.barh(names, values, color=colors, edgecolor="none", height=0.6)

    # Подписи значений на барах
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2,
            _bytes_fmt(val), va="center", ha="left",
            fontsize=7.5, color=_FG,
        )

    ax.set_title(
        f"Топ клиентов по трафику — {days}д"
        + (f"  •  {server_name}" if server_name else ""),
        fontsize=10, pad=8,
    )
    ax.xaxis.set_major_formatter(FuncFormatter(_bytes_fmt))
    ax.set_xlim(0, max(values) * 1.20)
    _apply_theme(fig, ax)
    plt.setp(ax.xaxis.get_majorticklabels(), fontsize=7)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    buf.seek(0)
    return buf
