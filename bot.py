#!/usr/bin/env python3
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

from config import load_config
from handlers import router
from logging_setup import setup_logging
from middlewares import AuthMiddleware
import database as db
import scheduler as sched

setup_logging()
logger = logging.getLogger(__name__)


async def setup_bot_menu(bot: Bot):
    """Устанавливает команды в кнопку Меню."""
    commands = [
        BotCommand(command="menu",      description="Главное меню"),
        BotCommand(command="help",      description="Справка по боту"),
        BotCommand(command="adduser",   description="Быстро создать клиента"),
        BotCommand(command="find",      description="Поиск клиента по имени"),
        BotCommand(command="alerts",    description="Настройки алертов"),
        BotCommand(command="alert_log", description="История последних алертов"),
        BotCommand(command="id",        description="Ваш Telegram ID"),
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

    logger.info(
        "Бот запущен | серверов: %d | юзеров: %d",
        len(config.servers),
        len(config.allowed_users),
    )

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        sched.stop()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
