"""
Admin panel: bosh menyu, statistika.
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.database import users as users_db
from bot.keyboards.reply import admin_panel_kb, main_menu_kb
from config import ADMIN_IDS

router = Router(name="admin_main")


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def open_admin_panel(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("⚙️ Admin panelga xush kelibsiz!", reply_markup=admin_panel_kb())


@router.message(F.text == "⬅️ Asosiy menyu")
async def back_to_main_menu(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("🏠 Asosiy menyu.", reply_markup=main_menu_kb())


@router.message(F.text == "📊 Statistika")
async def show_statistics(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return

    stats = await users_db.get_stats()
    text = (
        "📊 STATISTIKA\n\n"
        f"👥 Jami foydalanuvchilar: {stats['total_users']}\n"
        f"📈 Bugungi foydalanuvchilar: {stats['today_users']}\n"
        f"💎 Premium foydalanuvchilar: {stats['premium_users']}\n"
        f"👥 Jami referallar: {stats['total_referrals']}\n"
        f"💰 Hozirgi jami balans: {stats['total_uc']} UC\n"
        f"💸 Jami yechib olingan UC: {stats['total_withdrawn_uc']} UC\n"
        f"⏳ Kutilayotgan so'rovlar: {stats['pending_withdrawals']} ta\n"
        f"🎁 Admin tomonidan berilgan UC: {stats['total_admin_granted_uc']} UC"
    )
    await message.answer(text)
