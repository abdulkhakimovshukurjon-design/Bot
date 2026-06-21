"""
Foydalanuvchilar bilan bog'liq barcha ma'lumotlar bazasi amallari.
"""
from datetime import datetime, timedelta
from typing import Any, Optional

from bot.database.connection import get_connection


async def get_user(user_id: int) -> Optional[dict[str, Any]]:
    conn = await get_connection()
    cursor = await conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def user_exists(user_id: int) -> bool:
    user = await get_user(user_id)
    return user is not None


async def create_user(user_id: int, username: str | None, invited_by: int | None = None) -> None:
    conn = await get_connection()
    await conn.execute(
        """
        INSERT OR IGNORE INTO users (user_id, username, invited_by, is_registered)
        VALUES (?, ?, ?, 0)
        """,
        (user_id, username, invited_by),
    )
    await conn.commit()


async def complete_registration(
    user_id: int, full_name: str, age: int, pubg_id: str, pubg_nickname: str
) -> None:
    conn = await get_connection()
    await conn.execute(
        """
        UPDATE users
        SET full_name = ?, age = ?, pubg_id = ?, pubg_nickname = ?, is_registered = 1
        WHERE user_id = ?
        """,
        (full_name, age, pubg_id, pubg_nickname, user_id),
    )
    await conn.commit()


async def update_pubg_id(user_id: int, pubg_id: str) -> None:
    conn = await get_connection()
    await conn.execute("UPDATE users SET pubg_id = ? WHERE user_id = ?", (pubg_id, user_id))
    await conn.commit()


async def update_username(user_id: int, username: str | None) -> None:
    conn = await get_connection()
    await conn.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    await conn.commit()


async def is_registered(user_id: int) -> bool:
    user = await get_user(user_id)
    return bool(user and user["is_registered"])


async def add_balance(user_id: int, amount: int) -> None:
    conn = await get_connection()
    await conn.execute(
        "UPDATE users SET uc_balance = uc_balance + ? WHERE user_id = ?", (amount, user_id)
    )
    await conn.commit()


async def withdraw_balance(user_id: int) -> dict[str, int]:
    """
    Foydalanuvchining butun UC balansini yechib oladi (0 ga tushiradi)
    va withdrawals jadvaliga yozadi. {'id': ..., 'amount': ...} qaytaradi.
    """
    conn = await get_connection()
    user = await get_user(user_id)
    amount = user["uc_balance"] if user else 0

    await conn.execute("UPDATE users SET uc_balance = 0 WHERE user_id = ?", (user_id,))
    cursor = await conn.execute(
        "INSERT INTO withdrawals (user_id, amount, status) VALUES (?, ?, 'pending')",
        (user_id, amount),
    )
    await conn.commit()
    return {"id": cursor.lastrowid, "amount": amount}


async def get_pending_withdrawals(limit: int = 20) -> list[dict[str, Any]]:
    conn = await get_connection()
    cursor = await conn.execute(
        """
        SELECT w.*, u.full_name, u.username, u.pubg_id, u.pubg_nickname
        FROM withdrawals w
        LEFT JOIN users u ON u.user_id = w.user_id
        WHERE w.status = 'pending'
        ORDER BY w.created_at ASC
        LIMIT ?
        """,
        (limit,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_withdrawal(withdrawal_id: int) -> Optional[dict[str, Any]]:
    conn = await get_connection()
    cursor = await conn.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def complete_withdrawal(withdrawal_id: int) -> Optional[dict[str, Any]]:
    """So'rovni 'bajarildi' deb belgilaydi. Yopilgan yozuvni qaytaradi (yoki None)."""
    conn = await get_connection()
    withdrawal = await get_withdrawal(withdrawal_id)
    if not withdrawal or withdrawal["status"] != "pending":
        return None

    await conn.execute(
        "UPDATE withdrawals SET status = 'completed', completed_at = datetime('now') WHERE id = ?",
        (withdrawal_id,),
    )
    await conn.commit()
    withdrawal["status"] = "completed"
    return withdrawal


async def get_user_withdrawals(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    conn = await get_connection()
    cursor = await conn.execute(
        "SELECT * FROM withdrawals WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def admin_adjust_balance(
    user_id: int, amount: int, admin_id: int | None = None, reason: str | None = None
) -> int:
    """
    Admin tomonidan balansga UC qo'shish (musbat) yoki ayirish (manfiy).
    Balans hech qachon 0 dan pastga tushmaydi. Yangi balansni qaytaradi.
    """
    conn = await get_connection()
    user = await get_user(user_id)
    if not user:
        await create_user(user_id, None)
    current = user["uc_balance"] if user else 0

    new_balance = max(0, current + amount)
    applied_amount = new_balance - current

    await conn.execute("UPDATE users SET uc_balance = ? WHERE user_id = ?", (new_balance, user_id))
    await conn.execute(
        "INSERT INTO balance_adjustments (user_id, amount, reason, admin_id) VALUES (?, ?, ?, ?)",
        (user_id, applied_amount, reason, admin_id),
    )
    await conn.commit()
    return new_balance


async def get_user_balance_history(user_id: int, limit: int = 15) -> list[dict[str, Any]]:
    """
    Foydalanuvchining barcha balans o'zgarishlari tarixini birlashtirib qaytaradi:
    bonus, referal, admin tomonidan berilgan/ayirilgan, va yechib olingan UC.
    """
    conn = await get_connection()
    cursor = await conn.execute(
        """
        SELECT 'bonus' AS type, amount, created_at, NULL AS note
        FROM bonus_history WHERE user_id = ?

        UNION ALL
        SELECT 'referral' AS type, bonus_amount AS amount, created_at, NULL AS note
        FROM referrals WHERE inviter_id = ?

        UNION ALL
        SELECT 'withdrawal' AS type, -amount AS amount, created_at, status AS note
        FROM withdrawals WHERE user_id = ?

        UNION ALL
        SELECT 'admin_adjust' AS type, amount, created_at, reason AS note
        FROM balance_adjustments WHERE user_id = ?

        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, user_id, user_id, user_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def pubg_id_exists(pubg_id: str, exclude_user_id: int | None = None) -> bool:
    """Boshqa userda shu PUBG ID ro'yxatdan o'tganini tekshiradi (referal firibgarligiga qarshi)."""
    conn = await get_connection()
    if exclude_user_id is not None:
        cursor = await conn.execute(
            "SELECT 1 FROM users WHERE pubg_id = ? AND user_id != ? AND is_registered = 1",
            (pubg_id, exclude_user_id),
        )
    else:
        cursor = await conn.execute(
            "SELECT 1 FROM users WHERE pubg_id = ? AND is_registered = 1", (pubg_id,)
        )
    row = await cursor.fetchone()
    return row is not None


async def is_premium(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user or not user["is_premium"]:
        return False
    if user["premium_until"]:
        expires = datetime.fromisoformat(user["premium_until"])
        if expires < datetime.now():
            await downgrade_from_premium(user_id)
            return False
    return True


async def grant_premium(user_id: int, months: int, granted_by: int | None = None) -> str:
    """Premium beradi va tugash sanasini qaytaradi (ISO format)."""
    conn = await get_connection()
    user = await get_user(user_id)

    now = datetime.now()
    if user and user["is_premium"] and user["premium_until"]:
        current_expiry = datetime.fromisoformat(user["premium_until"])
        base = current_expiry if current_expiry > now else now
    else:
        base = now

    expires_at = base + timedelta(days=30 * months)
    expires_iso = expires_at.isoformat()

    await conn.execute(
        "UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?",
        (expires_iso, user_id),
    )

    from config import PREMIUM_PRICES

    price = PREMIUM_PRICES.get(months, 0)
    await conn.execute(
        """
        INSERT INTO premium_users (user_id, months, price, granted_by, expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, months, price, granted_by, expires_iso),
    )
    await conn.commit()
    return expires_iso


async def downgrade_from_premium(user_id: int) -> None:
    conn = await get_connection()
    await conn.execute(
        "UPDATE users SET is_premium = 0, premium_until = NULL WHERE user_id = ?", (user_id,)
    )
    await conn.commit()


async def get_referral_count(user_id: int) -> int:
    conn = await get_connection()
    cursor = await conn.execute(
        "SELECT COUNT(*) as cnt FROM referrals WHERE inviter_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return row["cnt"] if row else 0


async def get_referral_uc_sum(user_id: int) -> int:
    conn = await get_connection()
    cursor = await conn.execute(
        "SELECT COALESCE(SUM(bonus_amount), 0) as total FROM referrals WHERE inviter_id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    return row["total"] if row else 0


async def add_referral(inviter_id: int, invited_id: int, bonus_amount: int) -> bool:
    """Referalni qo'shadi. Agar allaqachon mavjud bo'lsa False qaytaradi."""
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO referrals (inviter_id, invited_id, bonus_amount)
            VALUES (?, ?, ?)
            """,
            (inviter_id, invited_id, bonus_amount),
        )
        await conn.commit()
        return True
    except Exception:
        return False


async def get_top_users(limit: int = 10) -> list[dict[str, Any]]:
    conn = await get_connection()
    cursor = await conn.execute(
        """
        SELECT user_id, username, full_name, uc_balance, is_premium
        FROM users
        WHERE is_registered = 1
        ORDER BY uc_balance DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def can_claim_bonus(user_id: int) -> tuple[bool, timedelta | None]:
    user = await get_user(user_id)
    if not user or not user["last_bonus_at"]:
        return True, None

    last_bonus = datetime.fromisoformat(user["last_bonus_at"])
    from config import DAILY_BONUS_COOLDOWN_HOURS

    next_available = last_bonus + timedelta(hours=DAILY_BONUS_COOLDOWN_HOURS)
    now = datetime.now()

    if now >= next_available:
        return True, None
    return False, next_available - now


async def claim_bonus(user_id: int, amount: int) -> None:
    conn = await get_connection()
    now_iso = datetime.now().isoformat()
    await conn.execute(
        "UPDATE users SET uc_balance = uc_balance + ?, last_bonus_at = ? WHERE user_id = ?",
        (amount, now_iso, user_id),
    )
    await conn.execute(
        "INSERT INTO bonus_history (user_id, amount) VALUES (?, ?)", (user_id, amount)
    )
    await conn.commit()


async def get_all_user_ids(only_active: bool = True) -> list[int]:
    conn = await get_connection()
    query = "SELECT user_id FROM users"
    if only_active:
        query += " WHERE is_banned = 0"
    cursor = await conn.execute(query)
    rows = await cursor.fetchall()
    return [r["user_id"] for r in rows]


async def get_stats() -> dict[str, Any]:
    conn = await get_connection()

    cursor = await conn.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = (await cursor.fetchone())["cnt"]

    cursor = await conn.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE date(joined_at) = date('now')"
    )
    today_users = (await cursor.fetchone())["cnt"]

    cursor = await conn.execute("SELECT COUNT(*) as cnt FROM users WHERE is_premium = 1")
    premium_users = (await cursor.fetchone())["cnt"]

    cursor = await conn.execute("SELECT COUNT(*) as cnt FROM referrals")
    total_referrals = (await cursor.fetchone())["cnt"]

    cursor = await conn.execute("SELECT COALESCE(SUM(uc_balance), 0) as total FROM users")
    total_uc = (await cursor.fetchone())["total"]

    cursor = await conn.execute("SELECT COALESCE(SUM(amount), 0) as total FROM withdrawals")
    total_withdrawn_uc = (await cursor.fetchone())["total"]

    cursor = await conn.execute(
        "SELECT COUNT(*) as cnt FROM withdrawals WHERE status = 'pending'"
    )
    pending_withdrawals = (await cursor.fetchone())["cnt"]

    cursor = await conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM balance_adjustments WHERE amount > 0"
    )
    total_admin_granted_uc = (await cursor.fetchone())["total"]

    return {
        "total_users": total_users,
        "today_users": today_users,
        "premium_users": premium_users,
        "total_referrals": total_referrals,
        "total_uc": total_uc,
        "total_withdrawn_uc": total_withdrawn_uc,
        "pending_withdrawals": pending_withdrawals,
        "total_admin_granted_uc": total_admin_granted_uc,
    }


async def search_user(query: str) -> Optional[dict[str, Any]]:
    """User ID yoki username orqali izlash."""
    conn = await get_connection()
    if query.isdigit():
        cursor = await conn.execute("SELECT * FROM users WHERE user_id = ?", (int(query),))
    else:
        clean = query.lstrip("@")
        cursor = await conn.execute("SELECT * FROM users WHERE username = ?", (clean,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def ban_user(user_id: int) -> None:
    conn = await get_connection()
    await conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    await conn.commit()


async def unban_user(user_id: int) -> None:
    conn = await get_connection()
    await conn.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    await conn.commit()


async def get_all_users_paginated(offset: int = 0, limit: int = 50) -> list[dict[str, Any]]:
    conn = await get_connection()
    cursor = await conn.execute(
        "SELECT * FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?", (limit, offset)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]
