import os
import aiosqlite

DB_PATH = "bot.db"
DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL is not None

if IS_POSTGRES:
    import asyncpg


def translate_query(query: str) -> str:
    """SQLite so'rovlarini PostgreSQL formatiga o'zgartiradi"""
    # 1. ? belgilarini $1, $2, $3 ga almashtirish
    count = 1
    while "?" in query:
        query = query.replace("?", f"${count}", 1)
        count += 1
    
    # 2. SQLite ga xos kalit so'zlarni PG ga almashtirish
    if "INSERT OR IGNORE" in query:
        if "users" in query.lower():
            query = "INSERT INTO users (user_id, username, full_name, referred_by) VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO NOTHING"
        elif "settings" in query.lower():
            query = "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO NOTHING"
            
    elif "INSERT OR REPLACE" in query:
        if "settings" in query.lower():
            query = "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        elif "groups" in query.lower():
            query = "INSERT INTO groups (group_id, group_name, is_active) VALUES ($1, $2, 1) ON CONFLICT (group_id) DO UPDATE SET group_name = EXCLUDED.group_name, is_active = 1"
            
    return query


async def init_db():
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id        BIGINT PRIMARY KEY,
                    username       VARCHAR(255),
                    full_name      VARCHAR(255),
                    referral_count INTEGER DEFAULT 0,
                    referred_by    BIGINT DEFAULT NULL,
                    joined_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    group_id   BIGINT PRIMARY KEY,
                    group_name VARCHAR(255),
                    added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active  INTEGER DEFAULT 1
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id          SERIAL PRIMARY KEY,
                    referrer_id BIGINT NOT NULL,
                    referred_id BIGINT NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(referrer_id, referred_id)
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key   VARCHAR(255) PRIMARY KEY,
                    value VARCHAR(255) NOT NULL
                )
            """)
            defaults = [
                ("sub_check",      "1"),
                ("ref_check",      "1"),
                ("link_filter",    "1"),
                ("join_cleaner",   "1"),
                ("ref_count",      "5"),
            ]
            for key, val in defaults:
                await conn.execute(
                    "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO NOTHING",
                    key, val
                )
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id        INTEGER PRIMARY KEY,
                    username       TEXT,
                    full_name      TEXT,
                    referral_count INTEGER DEFAULT 0,
                    referred_by    INTEGER DEFAULT NULL,
                    joined_at      TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    group_id   INTEGER PRIMARY KEY,
                    group_name TEXT,
                    added_at   TEXT DEFAULT (datetime('now')),
                    is_active  INTEGER DEFAULT 1
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    created_at  TEXT DEFAULT (datetime('now')),
                    UNIQUE(referrer_id, referred_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            defaults = [
                ("sub_check",      "1"),
                ("ref_check",      "1"),
                ("link_filter",    "1"),
                ("join_cleaner",   "1"),
                ("ref_count",      "5"),
            ]
            for key, val in defaults:
                await db.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, val)
                )
            await db.commit()


# ─── SOZLAMALAR ───

async def get_setting(key: str) -> str:
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            val = await conn.fetchval("SELECT value FROM settings WHERE key = $1", key)
            return val if val else "0"
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cur:
                row = await cur.fetchone()
                return row[0] if row else "0"


async def set_setting(key: str, value: str):
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                key, value
            )
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            await db.commit()


async def toggle_setting(key: str) -> bool:
    current = await get_setting(key)
    new_val = "0" if current == "1" else "1"
    await set_setting(key, new_val)
    return new_val == "1"


async def get_all_settings() -> dict:
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch("SELECT key, value FROM settings")
            return {r["key"]: r["value"] for r in rows}
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT key, value FROM settings") as cur:
                rows = await cur.fetchall()
                return {row[0]: row[1] for row in rows}


# ─── FOYDALANUVCHILAR ───

async def get_user(user_id: int) -> dict | None:
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            return dict(row) if row else None
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None


async def add_user(user_id: int, username: str, full_name: str, referred_by: int = None):
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                "INSERT INTO users (user_id, username, full_name, referred_by) VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO NOTHING",
                user_id, username, full_name, referred_by
            )
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, full_name, referred_by) VALUES (?, ?, ?, ?)",
                (user_id, username, full_name, referred_by)
            )
            await db.commit()


async def get_referral_count(user_id: int) -> int:
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            val = await conn.fetchval("SELECT referral_count FROM users WHERE user_id = $1", user_id)
            return val if val is not None else 0
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT referral_count FROM users WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0


async def increment_referral(referrer_id: int, referred_id: int) -> bool:
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            async with conn.transaction():
                # Referalni qo'shish (agar avval qo'shilmagan bo'lsa)
                # Unique constraint xatolik bersa transaction orqaga qaytadi
                await conn.execute(
                    "INSERT INTO referrals (referrer_id, referred_id) VALUES ($1, $2)",
                    referrer_id, referred_id
                )
                await conn.execute(
                    "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = $1",
                    referrer_id
                )
                return True
        except asyncpg.UniqueViolationError:
            return False
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
                    (referrer_id, referred_id)
                )
                await db.execute(
                    "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
                    (referrer_id,)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False


async def get_all_users() -> list[dict]:
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch("SELECT * FROM users")
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users") as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]


# ─── GURUHLAR ───

async def add_group(group_id: int, group_name: str):
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                "INSERT INTO groups (group_id, group_name, is_active) VALUES ($1, $2, 1) ON CONFLICT (group_id) DO UPDATE SET group_name = EXCLUDED.group_name, is_active = 1",
                group_id, group_name
            )
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO groups (group_id, group_name, is_active) VALUES (?, ?, 1)", (group_id, group_name))
            await db.commit()


async def remove_group(group_id: int):
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute("UPDATE groups SET is_active = 0 WHERE group_id = $1", group_id)
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE groups SET is_active = 0 WHERE group_id = ?", (group_id,))
            await db.commit()


async def get_active_groups() -> list[dict]:
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch("SELECT * FROM groups WHERE is_active = 1")
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM groups WHERE is_active = 1") as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]


async def get_stats() -> dict:
    if IS_POSTGRES:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            users = await conn.fetchval("SELECT COUNT(*) FROM users")
            groups = await conn.fetchval("SELECT COUNT(*) FROM groups WHERE is_active = 1")
            refs = await conn.fetchval("SELECT COUNT(*) FROM referrals")
            return {"users": users, "groups": groups, "referrals": refs}
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as c:
                users = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM groups WHERE is_active=1") as c:
                groups = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM referrals") as c:
                refs = (await c.fetchone())[0]
            return {"users": users, "groups": groups, "referrals": refs}
