import aiosqlite
from datetime import datetime

DB_PATH = "database.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Asosiy users jadvalini yaratish
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                lang TEXT DEFAULT NULL,
                latitude REAL,
                longitude REAL,
                notifications_enabled INTEGER DEFAULT 1,
                daily_report_enabled INTEGER DEFAULT 1,
                is_banned INTEGER DEFAULT 0,
                last_active TEXT,
                utc_offset INTEGER DEFAULT 5
            )
        """)
        # Migration: eski DB larga yangi ustunlar qo'shish
        migrations = [
            ("is_banned",    "INTEGER DEFAULT 0"),
            ("last_active",  "TEXT"),
            ("utc_offset",   "INTEGER DEFAULT 5"),
        ]
        for col, definition in migrations:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            except Exception:
                pass  # Ustun allaqachon mavjud

        # Namoz vaqtlari keshi jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS prayer_cache (
                coord_key TEXT PRIMARY KEY,
                date_str  TEXT,
                fajr      TEXT,
                dhuhr     TEXT,
                asr       TEXT,
                maghrib   TEXT,
                isha      TEXT
            )
        """)
        await db.commit()

# ──────────────────────────────────────────────
# Foydalanuvchi CRUD
# ──────────────────────────────────────────────

async def add_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )
        await db.commit()

async def update_last_active(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_active = ? WHERE user_id = ?",
            (datetime.utcnow().strftime("%Y-%m-%d %H:%M"), user_id)
        )
        await db.commit()

async def set_language(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()

async def get_user_lang(user_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row and row[0] else None

# ──────────────────────────────────────────────
# Lokatsiya
# ──────────────────────────────────────────────

async def update_user_location(user_id: int, lat: float, lon: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET latitude = ?, longitude = ? WHERE user_id = ?",
            (lat, lon, user_id)
        )
        await db.commit()

async def get_user_location(user_id: int) -> tuple | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT latitude, longitude FROM users "
            "WHERE user_id = ? AND latitude IS NOT NULL AND longitude IS NOT NULL",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return (row[0], row[1]) if row else None

# ──────────────────────────────────────────────
# Vaqt mintaqasi
# ──────────────────────────────────────────────

async def set_utc_offset(user_id: int, offset: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET utc_offset = ? WHERE user_id = ?", (offset, user_id)
        )
        await db.commit()

async def get_user_utc_offset(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT utc_offset FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row and row[0] is not None else 5

# ──────────────────────────────────────────────
# Sozlamalar
# ──────────────────────────────────────────────

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

async def get_user_settings(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT notifications_enabled, daily_report_enabled FROM users WHERE user_id = ?",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                return {"notifications": bool(row[0]), "daily_report": bool(row[1])}
            return {"notifications": True, "daily_report": True}

# ──────────────────────────────────────────────
# Statistika
# ──────────────────────────────────────────────

async def get_users_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def get_active_users_count() -> int:
    """Lokatsiyasi bor va ban qilinmagan foydalanuvchilar."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE latitude IS NOT NULL AND is_banned = 0"
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def get_banned_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE is_banned = 1"
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

# ──────────────────────────────────────────────
# Foydalanuvchilar ro'yxati
# ──────────────────────────────────────────────

async def get_all_users() -> list[int]:
    """Broadcast uchun — ban qilinmaganlar."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM users WHERE is_banned = 0"
        ) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]

async def get_all_users_with_info() -> list:
    """Admin panel uchun — oxirgi 50 ta foydalanuvchi."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, full_name, latitude, longitude, is_banned, last_active "
            "FROM users ORDER BY rowid DESC LIMIT 50"
        ) as cur:
            return list(await cur.fetchall())

async def ban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

# ──────────────────────────────────────────────
# Namoz vaqtlari keshi
# ──────────────────────────────────────────────

async def upsert_prayer_cache(coord_key: str, date_str: str, timings: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO prayer_cache (coord_key, date_str, fajr, dhuhr, asr, maghrib, isha)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(coord_key) DO UPDATE SET
                date_str = excluded.date_str,
                fajr     = excluded.fajr,
                dhuhr    = excluded.dhuhr,
                asr      = excluded.asr,
                maghrib  = excluded.maghrib,
                isha     = excluded.isha
        """, (
            coord_key, date_str,
            timings.get("Fajr"), timings.get("Dhuhr"), timings.get("Asr"),
            timings.get("Maghrib"), timings.get("Isha"),
        ))
        await db.commit()

async def get_prayer_cache(coord_key: str, date_str: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT fajr, dhuhr, asr, maghrib, isha FROM prayer_cache "
            "WHERE coord_key = ? AND date_str = ?",
            (coord_key, date_str)
        ) as cur:
            row = await cur.fetchone()
            if row:
                return {
                    "Fajr": row[0], "Dhuhr": row[1], "Asr": row[2],
                    "Maghrib": row[3], "Isha": row[4],
                }
            return None