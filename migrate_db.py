"""
SQLite -> PostgreSQL malumotlarni ko'chirish skripti.
"""
import sys
import sqlite3
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "bot.db"

if not DB_PATH.exists():
    print(f"SQLite fayl topilmadi: {DB_PATH}")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Ishlatish: python migrate_db.py <DATABASE_PUBLIC_URL>")
    sys.exit(1)

PG_URL = sys.argv[1]


def get_sqlite_data():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    data = {}
    tables = ["users", "admins", "channels", "referrals", "premium_users",
              "bonus_history", "broadcast_logs", "withdrawals", "balance_adjustments"]
    for table in tables:
        try:
            cursor = conn.execute(f"SELECT * FROM {table}")
            rows = [dict(r) for r in cursor.fetchall()]
            data[table] = rows
            print(f"  {table}: {len(rows)} ta")
        except Exception as e:
            print(f"  {table}: o'tkazib -> {e}")
            data[table] = []
    conn.close()
    return data


TABLE_DEFS = {
    "users": """CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY, username TEXT, full_name TEXT, age INTEGER,
        pubg_id TEXT, pubg_nickname TEXT, uc_balance INTEGER NOT NULL DEFAULT 0,
        is_premium INTEGER NOT NULL DEFAULT 0, premium_until TEXT, invited_by BIGINT,
        is_registered INTEGER NOT NULL DEFAULT 0, is_banned INTEGER NOT NULL DEFAULT 0,
        joined_at TEXT NOT NULL DEFAULT NOW(), last_bonus_at TEXT)""",
    "admins": """CREATE TABLE IF NOT EXISTS admins (
        user_id BIGINT PRIMARY KEY, added_at TEXT NOT NULL DEFAULT NOW())""",
    "channels": """CREATE TABLE IF NOT EXISTS channels (
        channel_id SERIAL PRIMARY KEY, chat_id TEXT NOT NULL UNIQUE,
        username TEXT NOT NULL, title TEXT, added_at TEXT NOT NULL DEFAULT NOW())""",
    "referrals": """CREATE TABLE IF NOT EXISTS referrals (
        referral_id SERIAL PRIMARY KEY, inviter_id BIGINT NOT NULL,
        invited_id BIGINT NOT NULL UNIQUE, bonus_amount INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT NOW(),
        FOREIGN KEY (inviter_id) REFERENCES users(user_id),
        FOREIGN KEY (invited_id) REFERENCES users(user_id))""",
    "premium_users": """CREATE TABLE IF NOT EXISTS premium_users (
        id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, months INTEGER NOT NULL,
        price INTEGER NOT NULL, granted_by BIGINT, started_at TEXT NOT NULL DEFAULT NOW(),
        expires_at TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users(user_id))""",
    "bonus_history": """CREATE TABLE IF NOT EXISTS bonus_history (
        id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, amount INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT NOW(),
        FOREIGN KEY (user_id) REFERENCES users(user_id))""",
    "broadcast_logs": """CREATE TABLE IF NOT EXISTS broadcast_logs (
        id SERIAL PRIMARY KEY, admin_id BIGINT NOT NULL,
        message_preview TEXT, sent_count INTEGER NOT NULL DEFAULT 0,
        failed_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT NOW())""",
    "withdrawals": """CREATE TABLE IF NOT EXISTS withdrawals (
        id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, amount INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL DEFAULT NOW(),
        completed_at TEXT, FOREIGN KEY (user_id) REFERENCES users(user_id))""",
    "balance_adjustments": """CREATE TABLE IF NOT EXISTS balance_adjustments (
        id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, amount INTEGER NOT NULL,
        reason TEXT, admin_id BIGINT, created_at TEXT NOT NULL DEFAULT NOW(),
        FOREIGN KEY (user_id) REFERENCES users(user_id))""",
}


async def migrate():
    import asyncpg

    print("\nSQLite dan o'qish...")
    data = get_sqlite_data()

    print("\nPostgreSQL ga ulanish...")
    pg = await asyncpg.connect(PG_URL)

    print("\nJadvallarni yaratish...")
    for name, ddl in TABLE_DEFS.items():
        try:
            await pg.execute(ddl)
            print(f"  {name}: OK")
        except Exception as e:
            print(f"  {name}: xato -> {e}")

    print("\nMalumotlarni ko'chirish...")
    for table, rows in data.items():
        if not rows:
            print(f"  {table}: 0 ta (o'tkazib yuborildi)")
            continue

        cols = list(rows[0].keys())
        placeholders = ", ".join(f"${i+1}" for i in range(len(cols)))
        col_names = ", ".join(cols)
        sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

        count = 0
        for row in rows:
            values = [row[c] for c in cols]
            # datetime('now') ni NOW() ga almashtirish
            values = [v if not isinstance(v, str) or "datetime(" not in v else v for v in values]
            try:
                await pg.execute(sql, *values)
                count += 1
            except Exception as e:
                print(f"  {table}: xatolik -> {e}")

        print(f"  {table}: {count}/{len(rows)} ta ko'chirildi")

    await pg.close()
    print("\n Migratsiya tugadi!")
    print("Endi Railway deploy tugashini kuting.")


if __name__ == "__main__":
    asyncio.run(migrate())
