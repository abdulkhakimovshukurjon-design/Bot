"""
Bot va WebApp uchun umumiy konfiguratsiya.
Barcha maxfiy ma'lumotlar .env faylidan o'qiladi.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _parse_admin_ids(raw: str) -> list[int]:
    if not raw:
        return []
    result = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            result.append(int(part))
    return result


BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

DB_PATH: str = str(BASE_DIR / os.getenv("DB_PATH", "database/bot.db"))

# WebApp (admin panel) sozlamalari
WEBAPP_HOST: str = os.getenv("WEBAPP_HOST", "0.0.0.0")
_raw_port: str = os.getenv("WEBAPP_PORT", "8000")
try:
    WEBAPP_PORT: int = int(_raw_port)
except ValueError:
    WEBAPP_PORT: int = 8000
WEBAPP_SECRET_KEY: str = os.getenv("WEBAPP_SECRET_KEY", "dev_secret_key")
WEBAPP_ADMIN_USERNAME: str = os.getenv("WEBAPP_ADMIN_USERNAME", "admin")
WEBAPP_ADMIN_PASSWORD: str = os.getenv("WEBAPP_ADMIN_PASSWORD", "admin123")

# Biznes-logika konstantalari
REFERRAL_BONUS_NORMAL: int = 15
REFERRAL_BONUS_PREMIUM: int = 20

DAILY_BONUS_NORMAL: int = 10
DAILY_BONUS_PREMIUM: int = 20
DAILY_BONUS_COOLDOWN_HOURS: int = 24

PREMIUM_PRICES = {
    1: 9_900,
    3: 24_900,
    6: 44_900,
    12: 79_900,
}

# UC yechib olish sozlamalari
MIN_WITHDRAWAL_UC: int = 660
WITHDRAWAL_ADMIN_USERNAME: str = "w_wtff"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN .env faylida topilmadi! Iltimos .env faylini tekshiring.")

if not ADMIN_IDS:
    raise RuntimeError("ADMIN_IDS .env faylida topilmadi! Iltimos .env faylini tekshiring.")
