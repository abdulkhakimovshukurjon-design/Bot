"""
Fonda ishlaydigan vazifa: Premium muddati tugagan foydalanuvchilarni
avtomatik ravishda Oddiy statusga qaytaradi.
"""
import asyncio
import logging
from datetime import datetime

from bot.database.connection import get_connection

logger = logging.getLogger(__name__)


async def check_expired_premiums() -> None:
    """Muddati tugagan barcha premiumlarni Oddiy statusga o'tkazadi."""
    conn = await get_connection()
    now_iso = datetime.now().isoformat()

    cursor = await conn.execute(
        "SELECT user_id FROM users WHERE is_premium = 1 AND premium_until < ?", (now_iso,)
    )
    expired_users = await cursor.fetchall()

    if expired_users:
        await conn.execute(
            "UPDATE users SET is_premium = 0, premium_until = NULL WHERE is_premium = 1 AND premium_until < ?",
            (now_iso,),
        )
        await conn.commit()
        logger.info("%d foydalanuvchining Premium statusi tugadi.", len(expired_users))


async def premium_expiry_scheduler(interval_seconds: int = 3600) -> None:
    """Har soatda premium muddatlarini tekshiruvchi doimiy loop."""
    while True:
        try:
            await check_expired_premiums()
        except Exception as e:
            logger.error("Premium tekshiruvida xato: %s", e)
        await asyncio.sleep(interval_seconds)
