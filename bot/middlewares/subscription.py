"""
Har bir xabar va callback uchun majburiy obunani tekshiruvchi middleware.
"""
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.database.channels import get_all_channels
from bot.keyboards.inline import subscription_kb
from bot.utils.subscription import check_user_subscription

logger = logging.getLogger(__name__)

# Bu callbacklarga obuna tekshirilmasdan ham ruxsat beriladi
ALLOWED_CALLBACKS_WITHOUT_CHECK = {"check_subscription"}


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        if isinstance(event, CallbackQuery) and event.data in ALLOWED_CALLBACKS_WITHOUT_CHECK:
            return await handler(event, data)

        channels = await get_all_channels()
        if not channels:
            return await handler(event, data)

        bot = data["bot"]
        is_subscribed, not_subscribed = await check_user_subscription(bot, user.id)

        if is_subscribed:
            return await handler(event, data)

        text = (
            "❌ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:\n\n"
            "Obuna bo'lgach, ✅ Tekshirish tugmasini bosing."
        )
        kb = subscription_kb(not_subscribed)

        if isinstance(event, Message):
            await event.answer(text, reply_markup=kb)
        elif isinstance(event, CallbackQuery):
            await event.answer("❌ Avval kanallarga obuna bo'ling!", show_alert=True)
            try:
                await event.message.answer(text, reply_markup=kb)
            except Exception:
                pass

        return None
