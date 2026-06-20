"""
Admin uchun bitta foydalanuvchiga shaxsiy xabar yuborish.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database import users as users_db
from bot.handlers.admin_main import is_admin
from bot.keyboards.reply import admin_panel_kb, cancel_kb
from bot.states import AdminMessageUser

logger = logging.getLogger(__name__)
router = Router(name="admin_message_user")


@router.message(F.text == "💬 Userga xabar yuborish")
async def start_message_user(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("👤 Xabar yuborish uchun foydalanuvchi User ID raqamini kiriting:", reply_markup=cancel_kb())
    await state.set_state(AdminMessageUser.waiting_user_id)


@router.message(AdminMessageUser.waiting_user_id)
async def process_user_id(message: Message, state: FSMContext) -> None:
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
    await message.answer("✍️ Endi yubormoqchi bo'lgan xabar matnini kiriting:")
    await state.set_state(AdminMessageUser.waiting_message_text)


@router.message(AdminMessageUser.waiting_message_text)
async def process_message_text(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    target_user_id = data["target_user_id"]
    await state.clear()

    try:
        await bot.send_message(target_user_id, f"📩 Admin xabari:\n\n{message.text}")
        await message.answer("✅ Xabar muvaffaqiyatli yuborildi.", reply_markup=admin_panel_kb())
    except Exception as e:
        logger.warning("Admin xabari yuborilmadi user=%s: %s", target_user_id, e)
        await message.answer(
            "❌ Xabar yuborilmadi. Foydalanuvchi botni bloklagan bo'lishi mumkin.",
            reply_markup=admin_panel_kb(),
        )
