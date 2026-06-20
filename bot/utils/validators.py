"""
Foydalanuvchi kiritgan ma'lumotlarni tekshirish (validatsiya) funksiyalari.
"""
import re


def validate_full_name(text: str) -> tuple[bool, str]:
    text = text.strip()
    if len(text) < 2:
        return False, "Ism va familiya juda qisqa. Qaytadan kiriting:"
    if len(text) > 60:
        return False, "Ism va familiya juda uzun. Qaytadan kiriting:"
    if not re.match(r"^[A-Za-zА-Яа-яЎўҚқҲҳҒғ\s\'\-]+$", text):
        return False, "Faqat harflardan foydalaning. Qaytadan kiriting:"
    return True, ""


def validate_age(text: str) -> tuple[bool, str, int | None]:
    text = text.strip()
    if not text.isdigit():
        return False, "Yoshni faqat raqamlarda kiriting (masalan: 18):", None
    age = int(text)
    if age < 5 or age > 100:
        return False, "Yosh noto'g'ri kiritildi. Qaytadan kiriting:", None
    return True, "", age


def validate_pubg_id(text: str) -> tuple[bool, str]:
    text = text.strip()
    if not text.isdigit():
        return False, "PUBG ID faqat raqamlardan iborat bo'lishi kerak. Qaytadan kiriting:"
    if len(text) < 5 or len(text) > 15:
        return False, "PUBG ID noto'g'ri uzunlikda. Qaytadan kiriting:"
    return True, ""


def validate_pubg_nickname(text: str) -> tuple[bool, str]:
    text = text.strip()
    if len(text) < 2 or len(text) > 30:
        return False, "Nickname uzunligi 2-30 belgi orasida bo'lishi kerak. Qaytadan kiriting:"
    return True, ""


def format_timedelta(td) -> str:
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours} soat {minutes} minut"


def generate_captcha() -> tuple[str, int]:
    """Oddiy matematik captcha yaratadi: (savol matni, to'g'ri javob)."""
    import random

    a = random.randint(2, 9)
    b = random.randint(2, 9)
    op = random.choice(["+", "-"])
    if op == "-" and a < b:
        a, b = b, a
    answer = a + b if op == "+" else a - b
    question = f"🤖 Botmasligingizni tasdiqlang: {a} {op} {b} = ?"
    return question, answer
