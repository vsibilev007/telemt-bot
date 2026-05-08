from datetime import datetime
from aiogram import Router, types
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()
CONFIG_PATH = "/etc/telemt/telemt.toml"


def export_toml_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(lambda c: c.data == "users:export_toml")
async def export_toml_callback(callback_query: types.CallbackQuery):
    await callback_query.answer("Готовлю бэкап конфигурации... ⏳", show_alert=False)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            toml_content = f.read()
    except Exception as e:
        await callback_query.message.reply(f"Ошибка чтения файла: {e}")
        return
    file_bytes = BufferedInputFile(
        toml_content.encode("utf-8"),
        filename=f"telemt_config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.toml",
    )
    await callback_query.message.reply_document(
        document=file_bytes,
        caption="Бэкап config.toml TeleMT 📦",
        reply_markup=export_toml_kb(),
    )


@router.callback_query(lambda c: c.data == "toml:back_to_menu")
async def toml_back_to_menu(callback_query: types.CallbackQuery, config):
    from keyboards import main_menu_kb
    from session import get_client, get_server_index

    uid = callback_query.from_user.id
    idx = get_server_index(uid, config)
    srv = config.servers[idx]
    try:
        client = get_client(uid, config)
        conns = sum(u.get("current_connections", 0) for u in await client.list_users())
        status = "ok"
    except Exception:
        conns = 0
        status = "unknown"
    await callback_query.answer()
    await callback_query.message.answer(
        f"<b>Telemt Manager</b> — <code>{srv.name}</code>",
        reply_markup=main_menu_kb(config.servers, idx, conns, status),
    )
