import aiosqlite

DB_PATH = "database.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Create users table if not exists
        await db.execute(
            """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    lang TEXT DEFAULT NULL,
                    latitude REAL,
                    longitude REAL,
                    notifications_enabled INTEGER DEFAULT 1,
                    daily_report_enabled INTEGER DEFAULT 1
                )
            """
        )
        # Create prayer cache table
        await db.execute(
            """
                CREATE TABLE IF NOT EXISTS prayer_cache (
                    coord_key TEXT PRIMARY KEY,
                    date_str TEXT,
                    fajr TEXT,
                    dhuhr TEXT,
                    asr TEXT,
                    maghrib TEXT,
                    isha TEXT
                )
            """
        )
        await db.commit()

async def add_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )
        await db.commit()

async def set_language(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()

# Location handling
async def update_user_location(user_id: int, lat: float, lon: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET latitude = ?, longitude = ? WHERE user_id = ?",
            (lat, lon, user_id)
        )
        await db.commit()

# Notification settings
async def set_notifications(user_id: int, enabled: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET notifications_enabled = ? WHERE user_id = ?",
            (1 if enabled else 0, user_id)
        )
        await db.commit()

async def set_daily_report(user_id: int, enabled: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET daily_report_enabled = ? WHERE user_id = ?",
            (1 if enabled else 0, user_id)
        )
        await db.commit()

async def get_user_settings(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT notifications_enabled, daily_report_enabled FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"notifications": bool(row[0]), "daily_report": bool(row[1])}
            return {"notifications": True, "daily_report": True}

async def get_user_location(user_id: int) -> tuple | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT latitude, longitude FROM users WHERE user_id = ? AND latitude IS NOT NULL AND longitude IS NOT NULL",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return (row[0], row[1])
            return None
async def upsert_prayer_cache(coord_key: str, date_str: str, timings: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
                INSERT INTO prayer_cache (coord_key, date_str, fajr, dhuhr, asr, maghrib, isha)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(coord_key) DO UPDATE SET
                    date_str = excluded.date_str,
                    fajr = excluded.fajr,
                    dhuhr = excluded.dhuhr,
                    asr = excluded.asr,
                    maghrib = excluded.maghrib,
                    isha = excluded.isha;
            """,
            (
                coord_key,
                date_str,
                timings.get('Fajr'),
                timings.get('Dhuhr'),
                timings.get('Asr'),
                timings.get('Maghrib'),
                timings.get('Isha'),
            ),
        )
        await db.commit()

async def get_prayer_cache(coord_key: str, date_str: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT fajr, dhuhr, asr, maghrib, isha FROM prayer_cache WHERE coord_key = ? AND date_str = ?",
            (coord_key, date_str)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "Fajr": row[0],
                    "Dhuhr": row[1],
                    "Asr": row[2],
                    "Maghrib": row[3],
                    "Isha": row[4],
                }
            return None

async def get_user_lang(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

async def get_users_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_all_users() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]