"""
Reply (pastki) klaviaturalar.
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo

import config


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Mening profilim"), KeyboardButton(text="🔗 Referal linkim")],
            [KeyboardButton(text="🏆 Top 10"), KeyboardButton(text="🎁 Bonus")],
            [KeyboardButton(text="💎 Premium"), KeyboardButton(text="ℹ️ Axborot olish")],
            [KeyboardButton(text="💸 UC yechib olish"), KeyboardButton(text="📜 UC tarixi")],
            [KeyboardButton(text="🎮 O'yinlar", web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/games"))],
        ],
        resize_keyboard=True,
    )

def games_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎰 Baraban"), KeyboardButton(text="🧩 Plinko")],
            [KeyboardButton(text="⬆️ Upgrade"), KeyboardButton(text="⚔️ UC Battle")],
            [KeyboardButton(text="🎲 Dice"), KeyboardButton(text="⬅️ Orqaga")],
        ],
        resize_keyboard=True,
    )


def admin_panel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="💬 Userga xabar yuborish")],
            [KeyboardButton(text="💎 Premium berish"), KeyboardButton(text="💰 UC berish")],
            [KeyboardButton(text="➖ UC ayirish"), KeyboardButton(text="💸 Yechib olish so'rovlari")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👤 User qidirish")],
            [KeyboardButton(text="⚙️ Majburiy obuna")],
            [KeyboardButton(text="⬅️ Asosiy menyu")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
