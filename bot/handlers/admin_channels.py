"""
Admin uchun majburiy obuna kanallarini boshqarish (qo'shish, o'chirish, ro'yxat).
"""
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import channels as channels_db
from bot.handlers.admin_main import is_admin
from bot.keyboards.inline import admin_channels_kb, channels_list_for_removal_kb
from bot.keyboards.reply import admin_panel_kb, cancel_kb
from bot.states import AdminAddChannel

logger = logging.getLogger(__name__)
router = Router(name="admin_channels")


@router.message(F.text == "⚙️ Majburiy obuna")
async def open_channels_menu(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("⚙️ Majburiy obuna kanallarini boshqarish:", reply_markup=admin_channels_kb())


@router.callback_query(F.data == "admin_back_channels")
async def back_to_channels_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text("⚙️ Majburiy obuna kanallarini boshqarish:", reply_markup=admin_channels_kb())


@router.callback_query(F.data == "admin_list_channels")
async def list_channels(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    channels = await channels_db.get_all_channels()
    await callback.answer()

    if not channels:
        await callback.message.answer("📋 Hozircha kanallar qo'shilmagan.")
        return

    lines = ["📋 MAJBURIY OBUNA KANALLARI:\n"]
    for ch in channels:
        lines.append(f"• {ch['title'] or ch['username']} ({ch['username']})")
    await callback.message.answer("\n".join(lines))


@router.callback_query(F.data == "admin_add_channel")
async def start_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    await callback.answer()
    await callback.message.answer(
        "➕ Kanal username'ini kiriting (masalan: @FreeUC_Uz).\n\n"
        "⚠️ Diqqat: Bot kanalga administrator qilib qo'shilgan bo'lishi shart!",
        reply_markup=cancel_kb(),
    )
    await state.set_state(AdminAddChannel.waiting_channel)


@router.message(AdminAddChannel.waiting_channel)
async def process_add_channel(message: Message, state: FSMContext, bot: Bot) -> None:
    username = (message.text or "").strip()
    await state.clear()

    if not username.startswith("@"):
        await message.answer("⚠️ Username @ belgisi bilan boshlanishi kerak. Masalan: @FreeUC_Uz", reply_markup=admin_panel_kb())
        return

    try:
        chat = await bot.get_chat(username)
    except Exception as e:
        logger.warning("Kanal topilmadi %s: %s", username, e)
        await message.answer(
            "❌ Kanal topilmadi. Username to'g'riligini va botning kanalda admin ekanligini tekshiring.",
            reply_markup=admin_panel_kb(),
        )
        return

    try:
        bot_member = await bot.get_chat_member(chat.id, (await bot.get_me()).id)
        if bot_member.status not in ("administrator", "creator"):
            await message.answer(
                "❌ Bot ushbu kanalda administrator emas. Avval botni admin qiling, keyin qaytadan urinib ko'ring.",
                reply_markup=admin_panel_kb(),
            )
            return
    except Exception as e:
        logger.warning("Bot statusi tekshirilmadi %s: %s", username, e)
        await message.answer("❌ Botning kanaldagi statusini tekshirib bo'lmadi.", reply_markup=admin_panel_kb())
        return

    success = await channels_db.add_channel(str(chat.id), username, chat.title)
    if success:
        await message.answer(f"✅ Kanal qo'shildi: {chat.title or username}", reply_markup=admin_panel_kb())
    else:
        await message.answer("⚠️ Bu kanal allaqachon ro'yxatda mavjud.", reply_markup=admin_panel_kb())


@router.callback_query(F.data == "admin_remove_channel")
async def start_remove_channel(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    channels = await channels_db.get_all_channels()
    await callback.answer()

    if not channels:
        await callback.message.answer("📋 Hozircha kanallar qo'shilmagan.")
        return

    await callback.message.answer(
        "➖ O'chirish uchun kanalni tanlang:", reply_markup=channels_list_for_removal_kb(channels)
    )


@router.callback_query(F.data.startswith("remove_channel_"))
async def process_remove_channel(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    channel_id = int(callback.data.split("_")[-1])
    success = await channels_db.remove_channel_by_id(channel_id)

    if success:
        await callback.answer("✅ Kanal o'chirildi!")
        await callback.message.answer("✅ Kanal muvaffaqiyatli o'chirildi.")
    else:
        await callback.answer("⚠️ Kanal topilmadi.", show_alert=True)
