"""
Inline klaviaturalar.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def subscription_kb(channels: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for ch in channels:
        username = ch["username"].lstrip("@")
        buttons.append(
            [InlineKeyboardButton(text=f"📢 {ch['title'] or username}", url=f"https://t.me/{username}")]
        )
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def edit_pubg_id_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ PUBG ID ni o'zgartirish", callback_data="edit_pubg_id")]
        ]
    )


def premium_duration_kb(prefix: str = "grant_premium") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 1 oy — 9 900 so'm", callback_data=f"{prefix}_1")],
            [InlineKeyboardButton(text="📅 3 oy — 24 900 so'm", callback_data=f"{prefix}_3")],
            [InlineKeyboardButton(text="📅 6 oy — 44 900 so'm", callback_data=f"{prefix}_6")],
            [InlineKeyboardButton(text="📅 12 oy — 79 900 so'm", callback_data=f"{prefix}_12")],
        ]
    )


def admin_channels_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="admin_add_channel")],
            [InlineKeyboardButton(text="➖ Kanal o'chirish", callback_data="admin_remove_channel")],
            [InlineKeyboardButton(text="📋 Kanallar ro'yxati", callback_data="admin_list_channels")],
        ]
    )


def channels_list_for_removal_kb(channels: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for ch in channels:
        label = ch["title"] or ch["username"]
        buttons.append(
            [InlineKeyboardButton(text=f"❌ {label}", callback_data=f"remove_channel_{ch['channel_id']}")]
        )
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back_channels")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_broadcast_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yuborish", callback_data="confirm_broadcast"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_broadcast"),
            ]
        ]
    )


def withdrawal_complete_kb(withdrawal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Bajarildi deb belgilash", callback_data=f"complete_withdrawal_{withdrawal_id}")]
        ]
    )
