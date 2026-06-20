"""
Majburiy obuna kanallari bilan bog'liq ma'lumotlar bazasi amallari.
"""
from typing import Any, Optional

from bot.database.connection import get_connection


async def add_channel(chat_id: str, username: str, title: str | None = None) -> bool:
    conn = await get_connection()
    try:
        await conn.execute(
            "INSERT INTO channels (chat_id, username, title) VALUES (?, ?, ?)",
            (chat_id, username, title),
        )
        await conn.commit()
        return True
    except Exception:
        return False


async def remove_channel(chat_id: str) -> bool:
    conn = await get_connection()
    cursor = await conn.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
    await conn.commit()
    return cursor.rowcount > 0


async def remove_channel_by_id(channel_id: int) -> bool:
    conn = await get_connection()
    cursor = await conn.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
    await conn.commit()
    return cursor.rowcount > 0


async def get_all_channels() -> list[dict[str, Any]]:
    conn = await get_connection()
    cursor = await conn.execute("SELECT * FROM channels ORDER BY added_at DESC")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_channel_by_username(username: str) -> Optional[dict[str, Any]]:
    conn = await get_connection()
    cursor = await conn.execute("SELECT * FROM channels WHERE username = ?", (username,))
    row = await cursor.fetchone()
    return dict(row) if row else None
