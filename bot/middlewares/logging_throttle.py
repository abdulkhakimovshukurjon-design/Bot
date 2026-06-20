"""
Har bir amalni log qiluvchi va spamdan himoya qiluvchi (throttling) middleware.
"""
import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger("bot.actions")

_last_action_time: dict[int, float] = {}
THROTTLE_SECONDS = 0.4


class LoggingThrottleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None:
            now = time.monotonic()
            last_time = _last_action_time.get(user.id, 0)
            if now - last_time < THROTTLE_SECONDS:
                if isinstance(event, CallbackQuery):
                    await event.answer()
                return None
            _last_action_time[user.id] = now

            if isinstance(event, Message):
                logger.info("user=%s action=message text=%r", user.id, (event.text or "")[:50])
            elif isinstance(event, CallbackQuery):
                logger.info("user=%s action=callback data=%r", user.id, event.data)

        return await handler(event, data)
