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


async def setup_bot_menu(bot: Bot, config=None):
    """Устанавливает команды в кнопку Меню."""
    lite = config.lite_mode if config else False
    commands = [
        BotCommand(command="menu",    description="Главное меню"),
        BotCommand(command="help",    description="Справка по боту"),
        BotCommand(command="adduser", description="Быстро создать клиента"),
        BotCommand(command="find",    description="Поиск клиента по имени"),
        BotCommand(command="id",      description="Ваш Telegram ID"),
    ]
    if not lite:
        commands += [
            BotCommand(command="alerts",    description="Настройки алертов"),
            BotCommand(command="alert_log", description="История последних 20 алертов"),
            BotCommand(command="check",     description="Диагностика узла по прокси-ссылке"),
        ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    logger.info("Меню бота установлено (%d команд)%s", len(commands), " [lite]" if lite else "")


async def main():
    config = load_config()

    await db.init_db()

    # Настраиваем прокси для подключения к Telegram API (если задан)
    bot_kwargs = dict(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    if config.tg_proxy_url:
        from aiohttp_socks import ProxyConnector
        if config.tg_proxy_url.startswith("socks"):
            from aiohttp import ClientSession
            connector = ProxyConnector.from_url(config.tg_proxy_url)
            session = ClientSession(connector=connector)
            bot_kwargs["session"] = session
            bot_kwargs["_custom_connector"] = connector
        else:
            from aiogram.client.session.aiohttp import AiohttpSession
            session = AiohttpSession(proxy=config.tg_proxy_url)
            bot_kwargs["session"] = session
        logger.info("Telegram прокси: %s", config.tg_proxy_url.split("@")[-1])

    bot = Bot(**bot_kwargs)
    dp = Dispatcher(storage=MemoryStorage())
    dp["config"] = config

    dp.message.middleware(AuthMiddleware(config.allowed_users))
    dp.callback_query.middleware(AuthMiddleware(config.allowed_users))

    dp.include_router(router)

    await setup_bot_menu(bot, config)
    if not config.lite_mode:
        sched.setup(bot, config)
    else:
        logger.info("Lite mode — scheduler и алерты отключены")

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
        custom_connector = bot_kwargs.get("_custom_connector")
        if custom_connector:
            await custom_connector.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
