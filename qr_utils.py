"""
Генерация QR-кодов для ссылок подключения MTProxy
"""

from __future__ import annotations

import io
import qrcode
from qrcode.image.pil import PilImage


def make_qr_bytes(text: str, border: int = 2) -> bytes:
    """Генерирует QR-код и возвращает PNG в виде bytes"""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img: PilImage = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def link_short_label(link: str, index: int) -> str:
    """Человекочитаемая метка для ссылки"""
    if link.startswith("tg://proxy"):
        if "dd=" in link or "ee=" in link:
            kind = "Secure"
        elif "tls=" in link:
            kind = "TLS"
        else:
            kind = "Classic"
    else:
        kind = "Link"
    return f"{kind} #{index + 1}"
