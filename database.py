import os
import aiosqlite

DB_PATH = "bot.db"
DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL is not None

if IS_POSTGRES:
    import asyncpg

# Global ulanishlar pooli
pool = None


async def init_pool():
    """PostgreSQL ulanishlar poolini yaratadi"""
    global pool
    if pool is None and IS_POSTGRES:
        clean_url = DATABASE_URL
        if "?" in clean_url:
            clean_url = clean_url.split("?", 1)[0]
        # Pool yaratish: minimal 1 ta, maksimal 10 ta ulanish ochiladi
        pool = await asyncpg.create_pool(
            clean_url,
            ssl='require',
            min_size=1,
            max_size=10,
            max_inactive_connection_lifetime=300.0
        )


def translate_query(query: str) -> str:
    """SQLite so'rovlarini PostgreSQL formatiga o'zgartiradi"""
    count = 1
    while "?" in query:
        query = query.replace("?", f"${count}", 1)
        count += 1
    
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
        await init_pool()
        async with pool.acquire() as conn:
            # Users table
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
            # Groups table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    group_id   BIGINT PRIMARY KEY,
                    group_name VARCHAR(255),
                    added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active  INTEGER DEFAULT 1
                )
            """)
            # Referrals table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id          SERIAL PRIMARY KEY,
                    referrer_id BIGINT NOT NULL,
                    referred_id BIGINT NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(referrer_id, referred_id)
                )
            """)
            # Settings table (global config)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key   VARCHAR(255) PRIMARY KEY,
                    value VARCHAR(255) NOT NULL
                )
            """)
            # Group specific settings table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS group_settings (
                    group_id      BIGINT PRIMARY KEY,
                    sub_check     INTEGER DEFAULT 1,
                    ref_check     INTEGER DEFAULT 1,
                    link_filter   INTEGER DEFAULT 1,
                    join_cleaner  INTEGER DEFAULT 1,
                    ref_count     INTEGER DEFAULT 5,
                    captcha       INTEGER DEFAULT 0,
                    antiflood     INTEGER DEFAULT 0
                )
            """)
            
            # Mavjud jadvalga yangi ustunlarni qo'shish (PostgreSQL)
            await conn.execute("ALTER TABLE group_settings ADD COLUMN IF NOT EXISTS captcha INTEGER DEFAULT 0")
            await conn.execute("ALTER TABLE group_settings ADD COLUMN IF NOT EXISTS antiflood INTEGER DEFAULT 0")

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
            # Group specific settings table for SQLite
            await db.execute("""
                CREATE TABLE IF NOT EXISTS group_settings (
                    group_id      INTEGER PRIMARY KEY,
                    sub_check     INTEGER DEFAULT 1,
                    ref_check     INTEGER DEFAULT 1,
                    link_filter   INTEGER DEFAULT 1,
                    join_cleaner  INTEGER DEFAULT 1,
                    ref_count     INTEGER DEFAULT 5,
                    captcha       INTEGER DEFAULT 0,
                    antiflood     INTEGER DEFAULT 0
                )
            """)
            
            try:
                await db.execute("ALTER TABLE group_settings ADD COLUMN captcha INTEGER DEFAULT 0")
            except Exception:
                pass
            try:
                await db.execute("ALTER TABLE group_settings ADD COLUMN antiflood INTEGER DEFAULT 0")
            except Exception:
                pass

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


# ─── GLOBAL SOZLAMALAR ───

async def get_setting(key: str) -> str:
    if IS_POSTGRES:
        await init_pool()
        val = await pool.fetchval("SELECT value FROM settings WHERE key = $1", key)
        return val if val else "0"
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cur:
                row = await cur.fetchone()
                return row[0] if row else "0"


async def set_setting(key: str, value: str):
    if IS_POSTGRES:
        await init_pool()
        await pool.execute(
            "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            key, value
        )
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
        await init_pool()
        rows = await pool.fetch("SELECT key, value FROM settings")
        return {r["key"]: r["value"] for r in rows}
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT key, value FROM settings") as cur:
                rows = await cur.fetchall()
                return {row[0]: row[1] for row in rows}


# ─── GURUHLARGA XOS SOZLAMALAR ───

async def get_group_setting(group_id: int, key: str) -> str:
    valid_keys = {"sub_check", "ref_check", "link_filter", "join_cleaner", "ref_count", "captcha", "antiflood"}
    if key not in valid_keys:
        return "0"

    if IS_POSTGRES:
        await init_pool()
        # Guruh sozlamalarini xavfsiz yaratish
        await pool.execute(
            "INSERT INTO group_settings (group_id) VALUES ($1) ON CONFLICT (group_id) DO NOTHING",
            group_id
        )
        val = await pool.fetchval(f"SELECT {key} FROM group_settings WHERE group_id = $1", group_id)
        return str(val) if val is not None else ("0" if key in {"captcha", "antiflood"} else ("5" if key == "ref_count" else "1"))
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO group_settings (group_id) VALUES (?)", (group_id,))
            await db.commit()
            async with db.execute(f"SELECT {key} FROM group_settings WHERE group_id = ?", (group_id,)) as cur:
                row = await cur.fetchone()
                return str(row[0]) if row else ("0" if key in {"captcha", "antiflood"} else ("5" if key == "ref_count" else "1"))


async def set_group_setting(group_id: int, key: str, value: str):
    valid_keys = {"sub_check", "ref_check", "link_filter", "join_cleaner", "ref_count", "captcha", "antiflood"}
    if key not in valid_keys:
        return
    val_int = int(value)

    if IS_POSTGRES:
        await init_pool()
        await pool.execute(
            f"UPDATE group_settings SET {key} = $1 WHERE group_id = $2",
            val_int, group_id
        )
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(f"UPDATE group_settings SET {key} = ? WHERE group_id = ?", (val_int, group_id))
            await db.commit()


async def toggle_group_setting(group_id: int, key: str) -> bool:
    current = await get_group_setting(group_id, key)
    new_val = "0" if current == "1" else "1"
    await set_group_setting(group_id, key, new_val)
    return new_val == "1"


# ─── FOYDALANUVCHILAR ───

async def get_user(user_id: int) -> dict | None:
    if IS_POSTGRES:
        await init_pool()
        row = await pool.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        return dict(row) if row else None
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None


async def add_user(user_id: int, username: str, full_name: str, referred_by: int = None):
    if IS_POSTGRES:
        await init_pool()
        await pool.execute(
            "INSERT INTO users (user_id, username, full_name, referred_by) VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO NOTHING",
            user_id, username, full_name, referred_by
        )
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, full_name, referred_by) VALUES (?, ?, ?, ?)",
                (user_id, username, full_name, referred_by)
            )
            await db.commit()


async def get_referral_count(user_id: int) -> int:
    if IS_POSTGRES:
        await init_pool()
        val = await pool.fetchval("SELECT referral_count FROM users WHERE user_id = $1", user_id)
        return val if val is not None else 0
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT referral_count FROM users WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0


async def increment_referral(referrer_id: int, referred_id: int) -> bool:
    if IS_POSTGRES:
        await init_pool()
        try:
            # asyncpg pool yordamida tranzaksiya ochish
            async with pool.acquire() as conn:
                async with conn.transaction():
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
        await init_pool()
        rows = await pool.fetch("SELECT * FROM users")
        return [dict(r) for r in rows]
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users") as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]


# ─── GURUHLAR ───

async def add_group(group_id: int, group_name: str):
    if IS_POSTGRES:
        await init_pool()
        await pool.execute(
            "INSERT INTO groups (group_id, group_name, is_active) VALUES ($1, $2, 1) ON CONFLICT (group_id) DO UPDATE SET group_name = EXCLUDED.group_name, is_active = 1",
            group_id, group_name
        )
        await pool.execute(
            "INSERT INTO group_settings (group_id) VALUES ($1) ON CONFLICT (group_id) DO NOTHING",
            group_id
        )
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO groups (group_id, group_name, is_active) VALUES (?, ?, 1)", (group_id, group_name))
            await db.execute("INSERT OR IGNORE INTO group_settings (group_id) VALUES (?)", (group_id,))
            await db.commit()


async def remove_group(group_id: int):
    if IS_POSTGRES:
        await init_pool()
        await pool.execute("UPDATE groups SET is_active = 0 WHERE group_id = $1", group_id)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE groups SET is_active = 0 WHERE group_id = ?", (group_id,))
            await db.commit()


async def get_active_groups() -> list[dict]:
    if IS_POSTGRES:
        await init_pool()
        rows = await pool.fetch("SELECT * FROM groups WHERE is_active = 1")
        return [dict(r) for r in rows]
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM groups WHERE is_active = 1") as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]


async def get_stats() -> dict:
    if IS_POSTGRES:
        await init_pool()
        users = await pool.fetchval("SELECT COUNT(*) FROM users")
        groups = await pool.fetchval("SELECT COUNT(*) FROM groups WHERE is_active = 1")
        refs = await pool.fetchval("SELECT COUNT(*) FROM referrals")
        return {"users": users, "groups": groups, "referrals": refs}
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as c:
                users = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM groups WHERE is_active=1") as c:
                groups = (await c.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM referrals") as c:
                refs = (await c.fetchone())[0]
            return {"users": users, "groups": groups, "referrals": refs}
