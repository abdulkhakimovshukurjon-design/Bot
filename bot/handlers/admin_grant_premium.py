"""
Admin uchun foydalanuvchiga Premium status berish.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import users as users_db
from bot.handlers.admin_main import is_admin
from bot.keyboards.inline import premium_duration_kb
from bot.keyboards.reply import admin_panel_kb, cancel_kb
from bot.states import AdminGrantPremium

logger = logging.getLogger(__name__)
router = Router(name="admin_grant_premium")


@router.message(F.text == "💎 Premium berish")
async def start_grant_premium(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("👤 Premium berish uchun foydalanuvchi User ID raqamini kiriting:", reply_markup=cancel_kb())
    await state.set_state(AdminGrantPremium.waiting_user_id)


@router.message(AdminGrantPremium.waiting_user_id)
async def process_grant_user_id(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam (User ID) kiriting:")
        return

    user_id = int(text)
    user = await users_db.get_user(user_id)
    if not user:
        await message.answer("⚠️ Bu User ID bo'yicha foydalanuvchi topilmadi. Qaytadan kiriting:")
        return

    await state.update_data(target_user_id=user_id)
    await message.answer("📅 Premium muddatini tanlang:", reply_markup=premium_duration_kb())
    await state.set_state(AdminGrantPremium.waiting_duration)


@router.callback_query(AdminGrantPremium.waiting_duration, F.data.startswith("grant_premium_"))
async def process_grant_duration(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    months = int(callback.data.split("_")[-1])
    data = await state.get_data()
    target_user_id = data["target_user_id"]
    await state.clear()

    expires_iso = await users_db.grant_premium(target_user_id, months, granted_by=callback.from_user.id)
    expires_date = expires_iso.split("T")[0]

    await callback.answer("✅ Premium berildi!")
    await callback.message.answer(
        f"✅ User {target_user_id} ga {months} oylik Premium berildi.\n📅 Tugash sanasi: {expires_date}",
        reply_markup=admin_panel_kb(),
    )

    try:
        await bot.send_message(
            target_user_id,
            f"🎉 Sizga {months} oylik Premium status berildi!\n📅 Tugash sanasi: {expires_date}\n\n💎 Endi siz Premium imkoniyatlardan foydalanishingiz mumkin!",
        )
    except Exception as e:
        logger.warning("Premium xabari yuborilmadi user=%s: %s", target_user_id, e)
