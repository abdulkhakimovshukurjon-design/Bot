"""
Free UC Bot - asosiy ishga tushirish fayli.
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from bot.database.connection import close_db, init_db
from bot.handlers import (
    admin_broadcast,
    admin_channels,
    admin_grant_premium,
    admin_grant_uc,
    admin_main,
    admin_message_user,
    admin_search_user,
    admin_withdrawals,
    features,
    games,
    profile,
    start,
    withdraw,
)
from bot.middlewares.error_handler import ErrorHandlingMiddleware
from bot.middlewares.logging_throttle import LoggingThrottleMiddleware
from bot.middlewares.subscription import SubscriptionMiddleware
from bot.utils.scheduler import premium_expiry_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Bot ishga tushirilmoqda...")

    await init_db(config.DB_PATH)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Middlewarelar (tartib muhim: error handler eng tashqarida bo'lishi kerak)
    # OUTER middlewarelar — HAR BIR kiruvchi update uchun, filterlardan oldin,
    # hech qanday istisnosiz ishga tushadi. Majburiy obuna shu yerda bo'lishi shart,
    # aks holda "inner" middleware ba'zi hollarda chetlab o'tilishi mumkin.
    dp.message.outer_middleware(ErrorHandlingMiddleware())
    dp.callback_query.outer_middleware(ErrorHandlingMiddleware())

    dp.message.outer_middleware(SubscriptionMiddleware())
    dp.callback_query.outer_middleware(SubscriptionMiddleware())

    dp.message.middleware(LoggingThrottleMiddleware())
    dp.callback_query.middleware(LoggingThrottleMiddleware())

    # Routerlar (tartib muhim: admin routerlar va start avval bo'lishi kerak)
    dp.include_router(start.router)
    dp.include_router(admin_main.router)
    dp.include_router(admin_broadcast.router)
    dp.include_router(admin_message_user.router)
    dp.include_router(admin_grant_premium.router)
    dp.include_router(admin_grant_uc.router)
    dp.include_router(admin_search_user.router)
    dp.include_router(admin_channels.router)
    dp.include_router(admin_withdrawals.router)
    dp.include_router(profile.router)
    dp.include_router(features.router)
    dp.include_router(withdraw.router)
    dp.include_router(games.router)

    await bot.delete_webhook(drop_pending_updates=True)

    scheduler_task = asyncio.create_task(premium_expiry_scheduler())

    try:
        logger.info("Bot polling rejimida ishga tushdi.")
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await close_db()
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot foydalanuvchi tomonidan to'xtatildi.")
