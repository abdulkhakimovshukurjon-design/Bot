"""
Admin uchun UC yechib olish so'rovlarini ko'rish va bajarildi deb belgilash.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

from bot.database import users as users_db
from bot.handlers.admin_main import is_admin
from bot.keyboards.inline import withdrawal_complete_kb

logger = logging.getLogger(__name__)
router = Router(name="admin_withdrawals")


@router.message(F.text == "💸 Yechib olish so'rovlari")
async def list_pending_withdrawals(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return

    pending = await users_db.get_pending_withdrawals()
    if not pending:
        await message.answer("✅ Hozircha kutilayotgan yechib olish so'rovlari yo'q.")
        return

    await message.answer(f"💸 Kutilayotgan so'rovlar: {len(pending)} ta")

    for w in pending:
        username_part = f"@{w['username']}" if w.get("username") else "username yo'q"
        text = (
            "💸 YECHIB OLISH SO'ROVI\n\n"
            f"👤 {w['full_name'] or '—'} ({username_part})\n"
            f"🆔 User ID: {w['user_id']}\n"
            f"🎮 PUBG ID: {w['pubg_id'] or '—'}\n"
            f"🎮 Nickname: {w['pubg_nickname'] or '—'}\n"
            f"💰 Miqdor: {w['amount']} UC\n"
            f"🕒 So'rov sanasi: {w['created_at']}"
        )
        await message.answer(text, reply_markup=withdrawal_complete_kb(w["id"]))


@router.callback_query(F.data.startswith("complete_withdrawal_"))
async def complete_withdrawal_callback(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    withdrawal_id = int(callback.data.split("_")[-1])
    withdrawal = await users_db.complete_withdrawal(withdrawal_id)

    if not withdrawal:
        await callback.answer("⚠️ Bu so'rov topilmadi yoki allaqachon bajarilgan.", show_alert=True)
        return

    await callback.answer("✅ Bajarildi deb belgilandi!")
    try:
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ BAJARILDI",
        )
    except Exception:
        pass

    try:
        await bot.send_message(
            withdrawal["user_id"],
            f"✅ Sizning {withdrawal['amount']} UC miqdoridagi yechib olish so'rovingiz "
            "admin tomonidan bajarildi. UC tez orada hisobingizga tushadi!",
        )
    except Exception as e:
        logger.warning("Withdrawal tasdiqlash xabari yuborilmadi user=%s: %s", withdrawal["user_id"], e)
