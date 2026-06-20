"""
Referal link, Top 10, Bonus, Premium va Axborot olish bo'limlari.
"""
from aiogram import Bot, F, Router
from aiogram.types import Message

from bot.database import users as users_db
from config import (
    ADMIN_IDS,
    DAILY_BONUS_NORMAL,
    DAILY_BONUS_PREMIUM,
    MIN_WITHDRAWAL_UC,
    WITHDRAWAL_ADMIN_USERNAME,
)
from bot.utils.validators import format_timedelta

router = Router(name="features")


@router.message(F.text == "🔗 Referal linkim")
async def show_referral_link(message: Message, bot: Bot) -> None:
    bot_info = await bot.get_me()
    user_id = message.from_user.id
    link = f"https://t.me/{bot_info.username}?start={user_id}"

    referral_count = await users_db.get_referral_count(user_id)
    referral_uc = await users_db.get_referral_uc_sum(user_id)

    text = (
        f"🔗 Referal havola:\n{link}\n\n"
        f"👥 Referallar soni: {referral_count}\n"
        f"💰 Referallardan yig'ilgan UC: {referral_uc} UC"
    )
    await message.answer(text)


@router.message(F.text == "🏆 Top 10")
async def show_top10(message: Message) -> None:
    top_users = await users_db.get_top_users(10)
    if not top_users:
        await message.answer("📊 Hozircha reyting bo'sh.")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 TOP 10 FOYDALANUVCHILAR\n"]
    for i, user in enumerate(top_users):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        name = user["full_name"] or user["username"] or f"ID{user['user_id']}"
        premium_mark = " 💎" if user["is_premium"] else ""
        lines.append(f"{prefix} {name}{premium_mark} — {user['uc_balance']} UC")

    await message.answer("\n".join(lines))


@router.message(F.text == "🎁 Bonus")
async def claim_daily_bonus(message: Message) -> None:
    user_id = message.from_user.id
    can_claim, remaining = await users_db.can_claim_bonus(user_id)

    if not can_claim:
        time_str = format_timedelta(remaining)
        await message.answer(f"⏳ Keyingi bonusgacha:\n{time_str}")
        return

    is_premium = await users_db.is_premium(user_id)
    amount = DAILY_BONUS_PREMIUM if is_premium else DAILY_BONUS_NORMAL

    await users_db.claim_bonus(user_id, amount)
    await message.answer(f"🎁 Tabriklaymiz! Sizga +{amount} UC bonus berildi!")


@router.message(F.text == "💎 Premium")
async def show_premium_info(message: Message) -> None:
    text = (
        "💎 PREMIUM\n\n"
        "Premium afzalliklari:\n"
        "✅ Har bir referal uchun 20 UC\n"
        "✅ Har 24 soatda 20 UC bonus\n"
        "✅ Maxsus aksiyalar\n"
        "✅ UC yechib olish imkoniyati\n\n"
        "📅 PREMIUM NARXLARI:\n"
        "📅 1 oy — 9 900 so'm\n"
        "📅 3 oy — 24 900 so'm\n"
        "📅 6 oy — 44 900 so'm\n"
        "📅 12 oy — 79 900 so'm\n\n"
        f"Premium olish uchun admin: @{WITHDRAWAL_ADMIN_USERNAME} ga murojaat qiling."
    )
    await message.answer(text)


@router.message(F.text == "ℹ️ Axborot olish")
async def show_info(message: Message) -> None:
    text = (
        "ℹ️ BOT HAQIDA MA'LUMOT\n\n"
        "🔗 Referal tizimi:\n"
        "Har bir do'stingizni taklif qilib UC yig'ing. Oddiy foydalanuvchi uchun +15 UC, "
        "Premium uchun +20 UC har bir referal uchun.\n\n"
        "💎 Premium tizimi:\n"
        "Premium foydalanuvchilar ko'proq bonus va imkoniyatlarga ega bo'ladi, "
        "shuningdek UC yechib olish faqat Premium foydalanuvchilarga ochiq.\n\n"
        "🎁 Bonus tizimi:\n"
        "Har 24 soatda bonus yig'ing: Oddiy +10 UC, Premium +20 UC.\n\n"
        f"💸 UC yechib olish:\n"
        f"Minimal yechib olish miqdori — {MIN_WITHDRAWAL_UC} UC. Premium foydalanuvchi "
        "\"💸 UC yechib olish\" tugmasini bossa, so'rov adminga yuboriladi va UC qo'lda yetkaziladi.\n\n"
        "📢 Majburiy obuna:\n"
        "Botdan foydalanish uchun barcha kanallarga obuna bo'lishingiz kerak.\n\n"
        "📜 UC yig'ish qoidalari:\n"
        "- O'z referal havolangiz orqali bonus ololmaysiz.\n"
        "- Har bir foydalanuvchi faqat bir marta referal hisoblanadi.\n\n"
        f"💬 Qo'llab-quvvatlash: @{WITHDRAWAL_ADMIN_USERNAME}"
    )
    await message.answer(text)


_HISTORY_LABELS = {
    "bonus": "🎁 Kunlik bonus",
    "referral": "🔗 Referal bonusi",
    "withdrawal": "💸 Yechib olindi",
    "admin_adjust": "⚙️ Admin tomonidan",
}


@router.message(F.text == "📜 UC tarixi")
async def show_uc_history(message: Message) -> None:
    user_id = message.from_user.id
    history = await users_db.get_user_balance_history(user_id, limit=15)

    if not history:
        await message.answer("📜 Hozircha balans tarixingiz bo'sh.")
        return

    lines = ["📜 OXIRGI BALANS O'ZGARISHLARI\n"]
    for h in history:
        label = _HISTORY_LABELS.get(h["type"], h["type"])
        amount = h["amount"]
        sign = "+" if amount >= 0 else ""
        date = (h["created_at"] or "")[:16]
        line = f"{label}: {sign}{amount} UC — {date}"
        if h["type"] == "withdrawal" and h.get("note"):
            status_label = "✅ bajarildi" if h["note"] == "completed" else "⏳ kutilmoqda"
            line += f" ({status_label})"
        lines.append(line)

    await message.answer("\n".join(lines))
