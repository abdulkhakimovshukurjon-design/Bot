"""
Majburiy obuna tekshiruvi uchun yordamchi funksiyalar.
"""
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from bot.database.channels import get_all_channels

logger = logging.getLogger(__name__)


async def check_user_subscription(bot: Bot, user_id: int) -> tuple[bool, list[dict]]:
    """
    Foydalanuvchi barcha majburiy kanallarga obuna bo'lganini tekshiradi.
    Qaytaradi: (hammasiga_obuna_bolgan, obuna_bolmagan_kanallar_royxati)
    """
    channels = await get_all_channels()
    if not channels:
        return True, []

    not_subscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status in ("left", "kicked"):
                not_subscribed.append(ch)
        except TelegramBadRequest as e:
            logger.warning("Kanal %s tekshirilmadi: %s", ch["chat_id"], e)
            not_subscribed.append(ch)
        except Exception as e:
            logger.error("Obuna tekshirishda kutilmagan xato: %s", e)
            not_subscribed.append(ch)

    return len(not_subscribed) == 0, not_subscribed
