"""
O'yinlar — Telegram WebApp orqali.
Faollashtirish: main_menu_kb da "🎮 O'yinlar" tugmasi WebApp ochadi.
"""
import logging

from aiogram import Router
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router(name="games")


@router.message(lambda m: m.web_app_data is not None)
async def handle_webapp_data(message: Message) -> None:
    data = message.web_app_data
    logger.info("WebApp data from user %s: payload=%s", message.from_user.id, data.payload)
    await message.answer("✅ O'yin natijasi qabul qilindi!")
