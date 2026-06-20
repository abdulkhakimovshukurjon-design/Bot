"""
Admin uchun foydalanuvchini User ID yoki username orqali qidirish.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database import users as users_db
from bot.handlers.admin_main import is_admin
from bot.keyboards.reply import admin_panel_kb, cancel_kb
from bot.states import AdminSearchUser

router = Router(name="admin_search_user")


@router.message(F.text == "👤 User qidirish")
async def start_search_user(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🔍 Qidirish uchun User ID yoki @username kiriting:", reply_markup=cancel_kb()
    )
    await state.set_state(AdminSearchUser.waiting_query)


@router.message(AdminSearchUser.waiting_query)
async def process_search_query(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    await state.clear()

    user = await users_db.search_user(query)
    if not user:
        await message.answer("⚠️ Foydalanuvchi topilmadi.", reply_markup=admin_panel_kb())
        return

    is_premium = await users_db.is_premium(user["user_id"])
    referral_count = await users_db.get_referral_count(user["user_id"])
    status = "💎 Premium" if is_premium else "👤 Oddiy"
    banned = " 🚫 BANLANGAN" if user["is_banned"] else ""

    text = (
        f"👤 User ID: {user['user_id']}{banned}\n"
        f"📛 Username: @{user['username'] if user['username'] else '—'}\n"
        f"👤 Ism: {user['full_name'] or '—'}\n"
        f"🎂 Yosh: {user['age'] or '—'}\n"
        f"🆔 PUBG ID: {user['pubg_id'] or '—'}\n"
        f"🎮 Nickname: {user['pubg_nickname'] or '—'}\n"
        f"💰 Balans: {user['uc_balance']} UC\n"
        f"👥 Referallar: {referral_count}\n"
        f"💎 Status: {status}"
    )
    await message.answer(text, reply_markup=admin_panel_kb())
