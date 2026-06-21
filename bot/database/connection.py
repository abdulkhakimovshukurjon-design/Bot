"""
SQLite va PostgreSQL ikkalasini ham qo'llaydigan ulanish moduli.
DATABASE_URL muhit o'zgaruvchisi bo'lsa — PostgreSQL, aks holda — SQLite.
"""
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_connection = None
_is_postgres = False


class _PgCursor:
    def __init__(self, pg_conn, sql, params):
        self._c = pg_conn
        self._sql = self._fix_sql(sql)
        self._params = params or ()
        self._rows = None
        self._index = 0
        self._affected = None

    @staticmethod
    def _fix_sql(sql):
        sql = sql.replace("datetime('now')", "NOW()")
        sql = sql.replace("date('now')", "CURRENT_DATE")
        i = 1
        while "?" in sql:
            sql = sql.replace("?", f"${i}", 1)
            i += 1
        return sql

    async def _lazy_fetch(self):
        if self._rows is None:
            # Try execute as command (INSERT/UPDATE/DELETE) or fetch rows
            cmd = self._sql.strip().upper()
            if cmd.startswith("SELECT") or cmd.startswith("WITH") or cmd.startswith("PRAGMA"):
                self._rows = await self._c.fetch(self._sql, *self._params)
            elif cmd.startswith("INSERT") or cmd.startswith("UPDATE") or cmd.startswith("DELETE"):
                tag = await self._c.execute(self._sql, *self._params)
                self._rows = []
                m = re.search(r'(\d+)$', tag)
                self._affected = int(m.group(1)) if m else 0
            else:
                self._rows = []
            self._index = 0

    async def get_rowcount(self):
        await self._lazy_fetch()
        if self._affected is not None:
            return self._affected
        return len(self._rows)

    async def fetchone(self):
        await self._lazy_fetch()
        if self._index >= len(self._rows):
            return None
        row = self._rows[self._index]
        self._index += 1
        return row

    async def fetchall(self):
        await self._lazy_fetch()
        self._index = len(self._rows)
        return list(self._rows)


class _PgWrapper:
    def __init__(self, pg_conn):
        self._c = pg_conn

    async def execute(self, sql: str, params=None):
        if params is None:
            params = ()
        return _PgCursor(self._c, sql, params)

    async def executescript(self, script: str):
        script = script.replace("datetime('now')", "NOW()")
        script = script.replace("date('now')", "CURRENT_DATE")
        statements = [s.strip() for s in script.split(";") if s.strip()]
        for stmt in statements:
            if stmt:
                await self._c.execute(stmt)

    async def commit(self):
        pass

    async def close(self):
        await self._c.close()


class _SqliteWrapper:
    def __init__(self, sqlite_conn):
        self._c = sqlite_conn

    async def execute(self, sql: str, params=None):
        if params is None:
            params = ()
        return await self._c.execute(sql, params)

    async def executescript(self, script: str):
        return await self._c.executescript(script)

    async def commit(self):
        return await self._c.commit()

    async def close(self):
        return await self._c.close()


async def get_connection():
    global _connection, _is_postgres
    if _connection is None:
        raise RuntimeError("Database ulanishi ishga tushirilmagan. init_db() ni chaqiring.")
    return _connection


async def init_db(db_path: str = None) -> None:
    global _connection, _is_postgres

    import os
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        _is_postgres = True
        import asyncpg
        pg_conn = await asyncpg.connect(database_url)
        _connection = _PgWrapper(pg_conn)
        logger.info("PostgreSQL ga ulandi: %s", database_url.split("@")[-1] if "@" in database_url else database_url)
    else:
        _is_postgres = False
        import aiosqlite
        db_path = db_path or os.getenv("DB_PATH", "database/bot.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        sqlite_conn = await aiosqlite.connect(db_path)
        sqlite_conn.row_factory = aiosqlite.Row
        await sqlite_conn.execute("PRAGMA foreign_keys = ON;")
        await sqlite_conn.execute("PRAGMA journal_mode = WAL;")
        _connection = _SqliteWrapper(sqlite_conn)
        logger.info("SQLite ga ulandi: %s", db_path)

    await _create_tables(_connection)
    if not _is_postgres:
        await _run_migrations(_connection)

    logger.info("Ma'lumotlar bazasi ishga tushirildi.")


async def close_db() -> None:
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
        logger.info("Ma'lumotlar bazasi ulanishi yopildi.")


async def _create_tables(conn) -> None:
    now_func = "NOW()" if _is_postgres else "datetime('now')"
    bigint_type = "BIGSERIAL" if _is_postgres else "INTEGER"
    await conn.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            age INTEGER,
            pubg_id TEXT,
            pubg_nickname TEXT,
            uc_balance INTEGER NOT NULL DEFAULT 0,
            is_premium INTEGER NOT NULL DEFAULT 0,
            premium_until TEXT,
            invited_by BIGINT,
            is_registered INTEGER NOT NULL DEFAULT 0,
            is_banned INTEGER NOT NULL DEFAULT 0,
            joined_at TEXT NOT NULL DEFAULT ({now_func}),
            last_bonus_at TEXT
        );

        CREATE TABLE IF NOT EXISTS admins (
            user_id BIGINT PRIMARY KEY,
            added_at TEXT NOT NULL DEFAULT ({now_func})
        );

        CREATE TABLE IF NOT EXISTS channels (
            channel_id {bigint_type} PRIMARY KEY,
            chat_id TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            title TEXT,
            added_at TEXT NOT NULL DEFAULT ({now_func})
        );

        CREATE TABLE IF NOT EXISTS referrals (
            referral_id {bigint_type} PRIMARY KEY,
            inviter_id BIGINT NOT NULL,
            invited_id BIGINT NOT NULL UNIQUE,
            bonus_amount INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT ({now_func}),
            FOREIGN KEY (inviter_id) REFERENCES users(user_id),
            FOREIGN KEY (invited_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS premium_users (
            id {bigint_type} PRIMARY KEY,
            user_id BIGINT NOT NULL,
            months INTEGER NOT NULL,
            price INTEGER NOT NULL,
            granted_by BIGINT,
            started_at TEXT NOT NULL DEFAULT ({now_func}),
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS bonus_history (
            id {bigint_type} PRIMARY KEY,
            user_id BIGINT NOT NULL,
            amount INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT ({now_func}),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS broadcast_logs (
            id {bigint_type} PRIMARY KEY,
            admin_id BIGINT NOT NULL,
            message_preview TEXT,
            sent_count INTEGER NOT NULL DEFAULT 0,
            failed_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT ({now_func})
        );

        CREATE TABLE IF NOT EXISTS withdrawals (
            id {bigint_type} PRIMARY KEY,
            user_id BIGINT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT ({now_func}),
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS balance_adjustments (
            id {bigint_type} PRIMARY KEY,
            user_id BIGINT NOT NULL,
            amount INTEGER NOT NULL,
            reason TEXT,
            admin_id BIGINT,
            created_at TEXT NOT NULL DEFAULT ({now_func}),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_users_balance ON users(uc_balance DESC);
        CREATE INDEX IF NOT EXISTS idx_users_invited_by ON users(invited_by);
        CREATE INDEX IF NOT EXISTS idx_referrals_inviter ON referrals(inviter_id);
        """
    )
    await conn.commit()


async def _run_migrations(conn) -> None:
    cursor = await conn.execute("PRAGMA table_info(withdrawals)")
    columns = {row["name"] for row in await cursor.fetchall()}
    if "completed_at" not in columns:
        await conn.execute("ALTER TABLE withdrawals ADD COLUMN completed_at TEXT")
        await conn.commit()
        logger.info("Migratsiya: withdrawals.completed_at ustuni qo'shildi.")


def is_postgres() -> bool:
    return _is_postgres


async def execute_insert(conn, sql: str, params: tuple, return_col: str = "id") -> int:
    """INSERT bajaradi va yangi ID qaytaradi (PostgreSQL va SQLite ikkalasi uchun)."""
    if _is_postgres:
        sql = sql.replace("datetime('now')", "NOW()")
        i = 1
        while "?" in sql:
            sql = sql.replace("?", f"${i}", 1)
            i += 1
        row = await conn._c.fetchrow(sql + f" RETURNING {return_col}", *params)
        return row[return_col]
    else:
        cursor = await conn.execute(sql, params)
        return cursor.lastrowid
