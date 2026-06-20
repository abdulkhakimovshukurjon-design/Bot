"""
Admin uchun foydalanuvchiga qo'lda UC balans berish yoki ayirish.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database import users as users_db
from bot.handlers.admin_main import is_admin
from bot.keyboards.reply import admin_panel_kb, cancel_kb
from bot.states import AdminDeductUC, AdminGrantUC

logger = logging.getLogger(__name__)
router = Router(name="admin_grant_uc")


# ---------------------------------------------------------------------------
# UC berish
# ---------------------------------------------------------------------------
@router.message(F.text == "💰 UC berish")
async def start_grant_uc(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "👤 UC berish uchun foydalanuvchi User ID raqamini kiriting:", reply_markup=cancel_kb()
    )
    await state.set_state(AdminGrantUC.waiting_user_id)


@router.message(AdminGrantUC.waiting_user_id)
async def process_grant_uc_user_id(message: Message, state: FSMContext) -> None:
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
    await message.answer(
        f"💰 {user['full_name'] or user_id} uchun necha UC berishni kiriting (faqat raqam):"
    )
    await state.set_state(AdminGrantUC.waiting_amount)


@router.message(AdminGrantUC.waiting_amount)
async def process_grant_uc_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("⚠️ Iltimos, musbat butun son kiriting (masalan: 100):")
        return

    amount = int(text)
    data = await state.get_data()
    target_user_id = data["target_user_id"]
    await state.clear()

    new_balance = await users_db.admin_adjust_balance(
        target_user_id, amount, admin_id=message.from_user.id, reason="admin_grant"
    )

    await message.answer(
        f"✅ User {target_user_id} ga {amount} UC berildi.\n💰 Yangi balans: {new_balance} UC",
        reply_markup=admin_panel_kb(),
    )

    try:
        await bot.send_message(
            target_user_id,
            f"🎉 Sizga admin tomonidan +{amount} UC qo'shildi!\n💰 Joriy balansingiz: {new_balance} UC",
        )
    except Exception as e:
        logger.warning("UC berish xabari yuborilmadi user=%s: %s", target_user_id, e)


# ---------------------------------------------------------------------------
# UC ayirish
# ---------------------------------------------------------------------------
@router.message(F.text == "➖ UC ayirish")
async def start_deduct_uc(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "👤 UC ayirish uchun foydalanuvchi User ID raqamini kiriting:", reply_markup=cancel_kb()
    )
    await state.set_state(AdminDeductUC.waiting_user_id)


@router.message(AdminDeductUC.waiting_user_id)
async def process_deduct_uc_user_id(message: Message, state: FSMContext) -> None:
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
    await message.answer(
        f"➖ {user['full_name'] or user_id} balansi: {user['uc_balance']} UC.\n"
        "Necha UC ayirishni kiriting (faqat raqam):"
    )
    await state.set_state(AdminDeductUC.waiting_amount)


@router.message(AdminDeductUC.waiting_amount)
async def process_deduct_uc_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("⚠️ Iltimos, musbat butun son kiriting (masalan: 50):")
        return

    amount = int(text)
    data = await state.get_data()
    target_user_id = data["target_user_id"]
    await state.clear()

    new_balance = await users_db.admin_adjust_balance(
        target_user_id, -amount, admin_id=message.from_user.id, reason="admin_deduct"
    )

    await message.answer(
        f"✅ User {target_user_id} dan {amount} UC ayirildi (balans 0 dan pastga tushmaydi).\n"
        f"💰 Yangi balans: {new_balance} UC",
        reply_markup=admin_panel_kb(),
    )

    try:
        await bot.send_message(
            target_user_id,
            f"⚠️ Balansingizdan {amount} UC ayirildi.\n💰 Joriy balansingiz: {new_balance} UC",
        )
    except Exception as e:
        logger.warning("UC ayirish xabari yuborilmadi user=%s: %s", target_user_id, e)
