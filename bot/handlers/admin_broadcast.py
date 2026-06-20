"""
Admin uchun barcha foydalanuvchilarga xabar yuborish (Broadcast).
"""
import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import users as users_db
from bot.database.connection import get_connection
from bot.handlers.admin_main import is_admin
from bot.keyboards.inline import confirm_broadcast_kb
from bot.keyboards.reply import admin_panel_kb, cancel_kb
from bot.states import AdminBroadcast

logger = logging.getLogger(__name__)
router = Router(name="admin_broadcast")


@router.message(F.text == "📢 Broadcast")
async def start_broadcast(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "📢 Barcha foydalanuvchilarga yuborilishi kerak bo'lgan xabarni yuboring:",
        reply_markup=cancel_kb(),
    )
    await state.set_state(AdminBroadcast.waiting_message)


@router.message(AdminBroadcast.waiting_message)
async def broadcast_preview(message: Message, state: FSMContext) -> None:
    await state.update_data(broadcast_message_id=message.message_id, broadcast_chat_id=message.chat.id)
    await message.answer(
        "⬆️ Yuqoridagi xabar barcha foydalanuvchilarga yuboriladi. Tasdiqlaysizmi?",
        reply_markup=confirm_broadcast_kb(),
    )
    await state.set_state(AdminBroadcast.waiting_confirm)


@router.callback_query(AdminBroadcast.waiting_confirm, F.data == "cancel_broadcast")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("❌ Bekor qilindi")
    await callback.message.answer("❌ Broadcast bekor qilindi.", reply_markup=admin_panel_kb())


@router.callback_query(AdminBroadcast.waiting_confirm, F.data == "confirm_broadcast")
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    await state.clear()
    await callback.answer("📤 Yuborilmoqda...")

    src_chat_id = data["broadcast_chat_id"]
    src_message_id = data["broadcast_message_id"]

    user_ids = await users_db.get_all_user_ids(only_active=True)

    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=src_chat_id, message_id=src_message_id)
            sent += 1
        except Exception as e:
            failed += 1
            logger.debug("Broadcast yuborilmadi user=%s: %s", uid, e)
        await asyncio.sleep(0.05)  # spamdan himoya / rate-limitga moslashish

    conn = await get_connection()
    await conn.execute(
        "INSERT INTO broadcast_logs (admin_id, message_preview, sent_count, failed_count) VALUES (?, ?, ?, ?)",
        (callback.from_user.id, "broadcast", sent, failed),
    )
    await conn.commit()

    await callback.message.answer(
        f"✅ Yuborildi: {sent}\n❌ Yuborilmadi: {failed}", reply_markup=admin_panel_kb()
    )
