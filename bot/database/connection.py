"""
SQLite ulanishini boshqaruvchi modul.
Butun bot davomida bitta aiosqlite connection pool orqali ishlaymiz.
"""
import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

_connection: aiosqlite.Connection | None = None


async def get_connection() -> aiosqlite.Connection:
    global _connection
    if _connection is None:
        raise RuntimeError("Database ulanishi ishga tushirilmagan. init_db() ni chaqiring.")
    return _connection


async def init_db(db_path: str) -> None:
    """Bazaga ulanish ochiladi va jadvallar yaratiladi."""
    global _connection

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _connection = await aiosqlite.connect(db_path)
    _connection.row_factory = aiosqlite.Row
    await _connection.execute("PRAGMA foreign_keys = ON;")
    await _connection.execute("PRAGMA journal_mode = WAL;")

    await _create_tables(_connection)
    await _run_migrations(_connection)
    logger.info("Ma'lumotlar bazasi muvaffaqiyatli ishga tushirildi: %s", db_path)


async def close_db() -> None:
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
        logger.info("Ma'lumotlar bazasi ulanishi yopildi.")


async def _create_tables(conn: aiosqlite.Connection) -> None:
    await conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            age INTEGER,
            pubg_id TEXT,
            pubg_nickname TEXT,
            uc_balance INTEGER NOT NULL DEFAULT 0,
            is_premium INTEGER NOT NULL DEFAULT 0,
            premium_until TEXT,
            invited_by INTEGER,
            is_registered INTEGER NOT NULL DEFAULT 0,
            is_banned INTEGER NOT NULL DEFAULT 0,
            joined_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_bonus_at TEXT
        );

        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS channels (
            channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            title TEXT,
            added_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS referrals (
            referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id INTEGER NOT NULL,
            invited_id INTEGER NOT NULL UNIQUE,
            bonus_amount INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (inviter_id) REFERENCES users(user_id),
            FOREIGN KEY (invited_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS premium_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            months INTEGER NOT NULL,
            price INTEGER NOT NULL,
            granted_by INTEGER,
            started_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS bonus_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS broadcast_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            message_preview TEXT,
            sent_count INTEGER NOT NULL DEFAULT 0,
            failed_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS balance_adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            reason TEXT,
            admin_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_users_balance ON users(uc_balance DESC);
        CREATE INDEX IF NOT EXISTS idx_users_invited_by ON users(invited_by);
        CREATE INDEX IF NOT EXISTS idx_referrals_inviter ON referrals(inviter_id);
        """
    )
    await conn.commit()


async def _run_migrations(conn: aiosqlite.Connection) -> None:
    """Eski bazalarni yangi ustunlar bilan moslashtirish (xavfsiz, idempotent)."""
    cursor = await conn.execute("PRAGMA table_info(withdrawals)")
    columns = {row["name"] for row in await cursor.fetchall()}
    if "completed_at" not in columns:
        await conn.execute("ALTER TABLE withdrawals ADD COLUMN completed_at TEXT")
        await conn.commit()
        logger.info("Migratsiya: withdrawals.completed_at ustuni qo'shildi.")
