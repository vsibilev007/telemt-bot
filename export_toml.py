"""
Бэкап telemt.toml — отправка файлом в чат
"""

from datetime import datetime

from aiogram import Router, F
from aiogram.types import BufferedInputFile, CallbackQuery

router = Router()

CONFIG_PATH = "/etc/telemt/telemt.toml"


@router.callback_query(F.data == "users:export_toml")
async def export_toml_callback(cq: CallbackQuery):
    await cq.answer("⏳ Готовлю бэкап...", show_alert=False)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            toml_content = f.read()
    except FileNotFoundError:
        await cq.message.answer(f"❌ Файл не найден: <code>{CONFIG_PATH}</code>")
        return
    except PermissionError:
        await cq.message.answer(f"❌ Нет прав на чтение: <code>{CONFIG_PATH}</code>")
        return
    except Exception as e:
        await cq.message.answer(f"❌ Ошибка чтения файла: {e}")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_bytes = BufferedInputFile(
        toml_content.encode("utf-8"),
        filename=f"telemt_backup_{ts}.toml",
    )

    from keyboards import export_toml_kb
    await cq.message.answer_document(
        document=file_bytes,
        caption=f"📦 <b>Бэкап telemt.toml</b>\n<i>{ts}</i>",
        reply_markup=export_toml_kb(),
    )
