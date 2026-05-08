"""
Telemt MTProxy Manager Bot
"""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeDefault,
    MenuButtonCommands,
)
import database as db
import scheduler as sched
from config import load_config
from handlers import router
from middlewares import AuthMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def setup_bot_menu(bot: Bot):
    """
    Устанавливает команды в кнопку Меню рядом со скрепкой —
    точно как на скриншоте 3x-ui бота
    """
    commands = [
        BotCommand(command="start", description="Показать главное меню"),
        BotCommand(command="help", description="Справка по боту"),
        BotCommand(command="status", description="Проверить статус бота"),
        BotCommand(command="alerts", description="Настройки алертов"),
        BotCommand(command="id", description="Показать ваш Telegram ID"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    logger.info("Меню бота установлено (%d команд)", len(commands))


async def main():
    config = load_config()
    await db.init_db()
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp["config"] = config
    dp.message.middleware(AuthMiddleware(config.allowed_users))
    dp.callback_query.middleware(AuthMiddleware(config.allowed_users))
    dp.include_router(router)
    await setup_bot_menu(bot)
    sched.setup(bot, config)
    logger.info("Бот запущен, серверов: %d", len(config.servers))
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        sched.stop()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
