"""
Barcha handlerlar uchun umumiy xatoliklarni ushlovchi middleware.
Bot hech qachon to'liq yiqilib qolmasligi uchun himoya qatlami.
"""
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            logger.exception("Handlerda kutilmagan xatolik: %s", e)
            try:
                if hasattr(event, "answer"):
                    await event.answer("⚠️ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
            except Exception:
                pass
            return None
