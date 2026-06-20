"""
UC yechib olish bo'limi.

Qoidalar:
- Faqat Premium foydalanuvchilar UC yecha oladi.
- Minimal yechib olish miqdori MIN_WITHDRAWAL_UC (660 UC).
- Yechib olishda foydalanuvchining butun balansi 0 ga tushiriladi va
  withdrawals jadvaliga yoziladi. Real UC'ni admin botdan tashqarida
  qo'lda yuboradi — bot faqat so'rovni qabul qilib, adminga xabar beradi.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.types import Message

from bot.database import users as users_db
from bot.keyboards.inline import withdrawal_complete_kb
from config import ADMIN_IDS, MIN_WITHDRAWAL_UC, WITHDRAWAL_ADMIN_USERNAME

logger = logging.getLogger(__name__)
router = Router(name="withdraw")


@router.message(F.text == "💸 UC yechib olish")
async def withdraw_uc(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id
    user = await users_db.get_user(user_id)
    if not user:
        await message.answer("⚠️ Ma'lumot topilmadi. /start buyrug'ini bosing.")
        return

    is_premium = await users_db.is_premium(user_id)
    if not is_premium:
        await message.answer(
            "💎 UC yechib olish faqat Premium foydalanuvchilar uchun mavjud.\n\n"
            f"Premium olish uchun adminga murojaat qiling: @{WITHDRAWAL_ADMIN_USERNAME}"
        )
        return

    balance = user["uc_balance"]

    if balance < MIN_WITHDRAWAL_UC:
        await message.answer(
            "⚠️ Sizda hali mablag' yetarli emas.\n\n"
            f"📉 Minimal yechib olish miqdori: {MIN_WITHDRAWAL_UC} UC\n"
            f"💰 Sizning balansingiz: {balance} UC"
        )
        return

    result = await users_db.withdraw_balance(user_id)
    amount = result["amount"]
    withdrawal_id = result["id"]

    await message.answer(
        f"✅ Siz {amount} UC yechib oldingiz!\n\n"
        "Bu jarayon muvaffaqiyatli amalga oshirildi. "
        f"Admin (@{WITHDRAWAL_ADMIN_USERNAME}) tez orada siz bilan aloqaga chiqadi."
    )

    username_part = f"@{message.from_user.username}" if message.from_user.username else "username yo'q"
    admin_text = (
        "💸 YANGI UC YECHISH SO'ROVI\n\n"
        f"👤 Foydalanuvchi: {user['full_name']} ({username_part})\n"
        f"🆔 User ID: {user_id}\n"
        f"🎮 PUBG ID: {user['pubg_id']}\n"
        f"🎮 PUBG Nickname: {user['pubg_nickname']}\n"
        f"💰 Yechilgan miqdor: {amount} UC\n\n"
        "❗️ Iltimos, UC'ni qo'lda yuboring va tugma orqali bajarildi deb belgilang."
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=withdrawal_complete_kb(withdrawal_id))
        except Exception as e:
            logger.warning("Withdraw xabari adminga yuborilmadi admin=%s: %s", admin_id, e)
