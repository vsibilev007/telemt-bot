"""
Middleware авторизации — пропускает только пользователей из списка ALLOWED_USERS
"""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject


class AuthMiddleware(BaseMiddleware):
    def __init__(self, allowed_users: list[int]):
        self.allowed_users = set(allowed_users)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return

        if user.id not in self.allowed_users:
            if isinstance(event, Message):
                await event.answer("⛔ Доступ запрещён.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ запрещён.", show_alert=True)
            return

        return await handler(event, data)
