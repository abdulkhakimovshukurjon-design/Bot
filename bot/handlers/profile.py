"""
'Mening profilim' bo'limi handlerlari.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import config
from bot.database import users as users_db
from bot.keyboards.inline import edit_pubg_id_kb
from bot.keyboards.reply import cancel_kb, main_menu_kb
from bot.states import EditProfile
from bot.utils.validators import validate_pubg_id

router = Router(name="profile")


@router.message(F.text == "👤 Mening profilim")
async def show_profile(message: Message) -> None:
    user = await users_db.get_user(message.from_user.id)
    if not user:
        await message.answer("⚠️ Ma'lumot topilmadi. /start buyrug'ini bosing.")
        return

    is_premium = await users_db.is_premium(message.from_user.id)
    referral_count = await users_db.get_referral_count(message.from_user.id)
    status = "💎 Premium" if is_premium else "👤 Oddiy"

    text = (
        f"👤 Ism: {user['full_name']}\n"
        f"🎂 Yosh: {user['age']}\n"
        f"🆔 PUBG ID: {user['pubg_id']}\n"
        f"🎮 PUBG Nickname: {user['pubg_nickname']}\n"
        f"💰 UC Balansi: {user['uc_balance']} UC\n"
        f"👥 Referallar soni: {referral_count}\n"
        f"💎 Status: {status}\n\n"
        f"🔑 Telegram ID: <code>{message.from_user.id}</code>\n"
        f"🌐 <i>WebApp ga kirish uchun ID dan foydalaning: {config.WEBAPP_URL}/games?user_id={message.from_user.id}</i>"
    )
    await message.answer(text, reply_markup=edit_pubg_id_kb())


@router.callback_query(F.data == "edit_pubg_id")
async def edit_pubg_id_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.answer("🆔 Yangi PUBG ID raqamingizni kiriting:", reply_markup=cancel_kb())
    await state.set_state(EditProfile.waiting_new_pubg_id)


@router.message(EditProfile.waiting_new_pubg_id)
async def edit_pubg_id_process(message: Message, state: FSMContext) -> None:
    valid, error = validate_pubg_id(message.text or "")
    if not valid:
        await message.answer(f"⚠️ {error}")
        return

    new_pubg_id = message.text.strip()
    already_used = await users_db.pubg_id_exists(new_pubg_id, exclude_user_id=message.from_user.id)
    if already_used:
        await message.answer(
            "⚠️ Bu PUBG ID allaqachon boshqa foydalanuvchida ro'yxatdan o'tgan. Qaytadan kiriting:"
        )
        return

    await users_db.update_pubg_id(message.from_user.id, new_pubg_id)
    await state.clear()
    await message.answer("✅ PUBG ID muvaffaqiyatli yangilandi!", reply_markup=main_menu_kb())
