"""
/start buyrug'i, registratsiya jarayoni va obuna tekshirish handlerlari.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import users as users_db
from bot.keyboards.reply import cancel_kb, main_menu_kb
from bot.states import Registration
from bot.utils.subscription import check_user_subscription
from bot.utils.validators import (
    generate_captcha,
    validate_age,
    validate_full_name,
    validate_pubg_id,
    validate_pubg_nickname,
)

logger = logging.getLogger(__name__)
router = Router(name="start")


async def _start_registration_with_captcha(message: Message, state: FSMContext) -> None:
    """Captcha bilan ro'yxatdan o'tishni boshlaydi (bot/spam akkauntlarga qarshi)."""
    question, answer = generate_captcha()
    await state.update_data(captcha_answer=answer)
    await message.answer(
        f"👋 Botga xush kelibsiz!\n\n{question}\n\n(Javobni raqamda yuboring)",
        reply_markup=cancel_kb(),
    )
    await state.set_state(Registration.waiting_captcha)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username

    invited_by: int | None = None
    if command.args and command.args.isdigit():
        potential_inviter = int(command.args)
        if potential_inviter != user_id:
            invited_by = potential_inviter

    exists = await users_db.user_exists(user_id)
    if not exists:
        await users_db.create_user(user_id, username, invited_by)
    else:
        await users_db.update_username(user_id, username)

    registered = await users_db.is_registered(user_id)
    if registered:
        await message.answer(
            "👋 Xush kelibsiz! Asosiy menyudan foydalaning:",
            reply_markup=main_menu_kb(),
        )
        return

    await _start_registration_with_captcha(message, state)


@router.message(F.text == "❌ Bekor qilish")
async def cancel_any_state(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    registered = await users_db.is_registered(message.from_user.id)
    if registered:
        await message.answer("❌ Amal bekor qilindi.", reply_markup=main_menu_kb())
    else:
        await message.answer(
            "❌ Ro'yxatdan o'tish bekor qilindi.\nQaytadan boshlash uchun /start buyrug'ini yuboring."
        )


@router.message(Registration.waiting_captcha)
async def process_captcha(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    expected = data.get("captcha_answer")
    text = (message.text or "").strip()

    if not text.lstrip("-").isdigit() or int(text) != expected:
        question, answer = generate_captcha()
        await state.update_data(captcha_answer=answer)
        await message.answer(f"⚠️ Noto'g'ri javob. Qaytadan urinib ko'ring.\n\n{question}")
        return

    await message.answer(
        "✅ Tasdiqlandi!\n\n"
        "Ro'yxatdan o'tish uchun ma'lumotlaringizni kiriting.\n\n"
        "1️⃣ Ism va familiyangizni kiriting:"
    )
    await state.set_state(Registration.waiting_full_name)


@router.message(Registration.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext) -> None:
    valid, error = validate_full_name(message.text or "")
    if not valid:
        await message.answer(f"⚠️ {error}")
        return

    await state.update_data(full_name=message.text.strip())
    await message.answer("2️⃣ Yoshingizni kiriting:")
    await state.set_state(Registration.waiting_age)


@router.message(Registration.waiting_age)
async def process_age(message: Message, state: FSMContext) -> None:
    valid, error, age = validate_age(message.text or "")
    if not valid:
        await message.answer(f"⚠️ {error}")
        return

    await state.update_data(age=age)
    await message.answer("3️⃣ PUBG ID raqamingizni kiriting:")
    await state.set_state(Registration.waiting_pubg_id)


@router.message(Registration.waiting_pubg_id)
async def process_pubg_id(message: Message, state: FSMContext) -> None:
    valid, error = validate_pubg_id(message.text or "")
    if not valid:
        await message.answer(f"⚠️ {error}")
        return

    pubg_id = message.text.strip()
    already_used = await users_db.pubg_id_exists(pubg_id)
    if already_used:
        await message.answer(
            "⚠️ Bu PUBG ID allaqachon boshqa foydalanuvchi tomonidan ro'yxatdan o'tkazilgan. "
            "Iltimos, o'zingizning haqiqiy PUBG ID raqamingizni kiriting:"
        )
        return

    await state.update_data(pubg_id=pubg_id)
    await message.answer("4️⃣ PUBG Nickname (o'yindagi ismingizni) kiriting:")
    await state.set_state(Registration.waiting_pubg_nickname)


@router.message(Registration.waiting_pubg_nickname)
async def process_pubg_nickname(message: Message, state: FSMContext, bot: Bot) -> None:
    valid, error = validate_pubg_nickname(message.text or "")
    if not valid:
        await message.answer(f"⚠️ {error}")
        return

    data = await state.get_data()
    user_id = message.from_user.id
    pubg_nickname = message.text.strip()

    await users_db.complete_registration(
        user_id=user_id,
        full_name=data["full_name"],
        age=data["age"],
        pubg_id=data["pubg_id"],
        pubg_nickname=pubg_nickname,
    )
    await state.clear()

    await message.answer(
        "✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!\n\n"
        f"👤 Ism: {data['full_name']}\n"
        f"🎂 Yosh: {data['age']}\n"
        f"🆔 PUBG ID: {data['pubg_id']}\n"
        f"🎮 Nickname: {pubg_nickname}",
        reply_markup=main_menu_kb(),
    )

    # Referal bonusini hisoblash
    user = await users_db.get_user(user_id)
    inviter_id = user.get("invited_by") if user else None
    if inviter_id:
        await _try_credit_referral(bot, inviter_id, user_id)


async def _try_credit_referral(bot: Bot, inviter_id: int, invited_id: int) -> None:
    """Taklif qilingan odam ro'yxatdan o'tib, obuna bo'lganda referal bonus beradi."""
    from config import REFERRAL_BONUS_NORMAL, REFERRAL_BONUS_PREMIUM

    inviter = await users_db.get_user(inviter_id)
    if not inviter:
        return

    is_subscribed, _ = await check_user_subscription(bot, invited_id)
    if not is_subscribed:
        return

    inviter_is_premium = await users_db.is_premium(inviter_id)
    bonus = REFERRAL_BONUS_PREMIUM if inviter_is_premium else REFERRAL_BONUS_NORMAL

    success = await users_db.add_referral(inviter_id, invited_id, bonus)
    if not success:
        return

    await users_db.add_balance(inviter_id, bonus)

    try:
        await bot.send_message(
            inviter_id,
            f"🎉 Yangi referal qo'shildi!\n💰 Balansingizga +{bonus} UC qo'shildi.",
        )
    except Exception as e:
        logger.warning("Inviter %s ga xabar yuborilmadi: %s", inviter_id, e)


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    user_id = callback.from_user.id
    is_subscribed, not_subscribed = await check_user_subscription(bot, user_id)

    if not is_subscribed:
        from bot.keyboards.inline import subscription_kb

        await callback.answer("❌ Hali ham barcha kanallarga obuna bo'lmagansiz!", show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=subscription_kb(not_subscribed))
        except Exception:
            pass
        return

    await callback.answer("✅ Obuna tasdiqlandi!")

    registered = await users_db.is_registered(user_id)
    if registered:
        await callback.message.answer("✅ Rahmat! Endi botdan to'liq foydalanishingiz mumkin.", reply_markup=main_menu_kb())

        user = await users_db.get_user(user_id)
        inviter_id = user.get("invited_by") if user else None
        if inviter_id:
            await _try_credit_referral(bot, inviter_id, user_id)
    else:
        question, answer = generate_captcha()
        await state.update_data(captcha_answer=answer)
        await callback.message.answer(
            f"✅ Obuna tasdiqlandi!\n\n{question}\n\n(Javobni raqamda yuboring)",
            reply_markup=cancel_kb(),
        )
        await state.set_state(Registration.waiting_captcha)
