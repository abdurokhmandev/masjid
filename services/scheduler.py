import asyncio
import logging
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import db

# ──────────────────────────────────────────────
# Global scheduler
# ──────────────────────────────────────────────

scheduler = AsyncIOScheduler()

# ──────────────────────────────────────────────
# Namoz vaqtlarini olish (qayta ishlatish)
# ──────────────────────────────────────────────

def _fetch_prayer_times(lat: float, lon: float) -> dict:
    import requests
    try:
        url = f"https://api.aladhan.com/v1/timings?latitude={lat}&longitude={lon}&method=3"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("data", {}).get("timings", {})
    except Exception as e:
        logging.error(f"[scheduler] API xato: {e}")
    return {}

def _clean_time(raw: str) -> str:
    return raw.split()[0] if raw and " " in raw else (raw or "—")

# ──────────────────────────────────────────────
# Kunlik hisobot
# ──────────────────────────────────────────────

async def send_daily_report(bot: Bot):
    """Faqat daily_report_enabled=1 bo'lgan foydalanuvchilarga ertalabki namoz vaqtlarini yuborish."""
    users = await db.get_all_users()
    sent, errors = 0, 0
    for user_id in users:
        try:
            settings = await db.get_user_settings(user_id)
            if not settings.get("daily_report"):
                continue

            loc = await db.get_user_location(user_id)
            if not loc:
                continue

            lat, lon = loc
            coord_key = f"{round(lat, 5)},{round(lon, 5)}"

            # UTC offset asosida foydalanuvchining bugungi sanasi
            utc_offset = await db.get_user_utc_offset(user_id)
            user_tz    = timezone(timedelta(hours=utc_offset))
            today_str  = datetime.now(user_tz).strftime("%Y-%m-%d")

            # Keshdan tekshirish
            cached = await db.get_prayer_cache(coord_key, today_str)
            if cached:
                timings = cached
            else:
                timings = await asyncio.to_thread(_fetch_prayer_times, lat, lon)
                if timings:
                    await db.upsert_prayer_cache(coord_key, today_str, timings)
                else:
                    continue

            msg = (
                "🌅 <b>Assalomu alaykum!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 Bugungi namoz vaqtlari ({today_str}):\n\n"
                f"🌙 Bomdod:           <b>{_clean_time(timings.get('Fajr'))}</b>\n"
                f"🌅 Quyosh chiqishi:  <b>{_clean_time(timings.get('Sunrise'))}</b>\n"
                f"☀️  Peshin:            <b>{_clean_time(timings.get('Dhuhr'))}</b>\n"
                f"🌤  Asr:               <b>{_clean_time(timings.get('Asr'))}</b>\n"
                f"🌆 Shom:             <b>{_clean_time(timings.get('Maghrib'))}</b>\n"
                f"🌃 Xufton:           <b>{_clean_time(timings.get('Isha'))}</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📡 <i>Masjid Finder Bot</i>"
            )
            await bot.send_message(user_id, msg, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            errors += 1
            logging.warning(f"[scheduler] daily_report {user_id}: {e}")

    logging.info(f"[scheduler] Kunlik hisobot: {sent} yuborildi, {errors} xatolik")

# ──────────────────────────────────────────────
# Namoz vaqti eslatmasi (15 daqiqa oldin)
# ──────────────────────────────────────────────

PRAYER_NAMES = {
    "Fajr": "🌙 Bomdod",
    "Dhuhr": "☀️ Peshin",
    "Asr": "🌤 Asr",
    "Maghrib": "🌆 Shom",
    "Isha": "🌃 Xufton",
}

async def reminder_checker(bot: Bot):
    """Har daqiqada: har bir foydalanuvchining namoz vaqtiga 15 daqiqa qolganini tekshirish."""
    users = await db.get_all_users()
    for user_id in users:
        try:
            settings = await db.get_user_settings(user_id)
            if not settings.get("notifications"):
                continue

            loc = await db.get_user_location(user_id)
            if not loc:
                continue

            lat, lon = loc

            # Foydalanuvchining hozirgi vaqti
            utc_offset = await db.get_user_utc_offset(user_id)
            user_tz = timezone(timedelta(hours=utc_offset))
            now     = datetime.now(user_tz)
            future  = now + timedelta(minutes=15)

            coord_key = f"{round(lat, 5)},{round(lon, 5)}"
            today_str = now.strftime("%Y-%m-%d")

            cached = await db.get_prayer_cache(coord_key, today_str)
            if not cached:
                cached = await asyncio.to_thread(_fetch_prayer_times, lat, lon)
                if cached:
                    await db.upsert_prayer_cache(coord_key, today_str, cached)
                else:
                    continue

            # Har bir namoz vaqtini tekshirish
            for key, label in PRAYER_NAMES.items():
                time_str = cached.get(key)
                if not time_str:
                    continue
                time_str = _clean_time(time_str)
                try:
                    h, m = map(int, time_str.split(":"))
                    prayer_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                    if now < prayer_dt <= future:
                        mins_left = int((prayer_dt - now).total_seconds() // 60)
                        await bot.send_message(
                            user_id,
                            f"🔔 <b>{label} namoziga {mins_left} daqiqa qoldi!</b>\n\n"
                            f"⏰ Vaqti: <b>{time_str}</b>\n"
                            "━━━━━━━━━━━━━━━━━━━━\n"
                            "🤲 <i>Alloh qabul qilsin!</i>",
                            parse_mode="HTML",
                        )
                except Exception:
                    continue
        except Exception as e:
            logging.warning(f"[scheduler] reminder {user_id}: {e}")

# ──────────────────────────────────────────────
# Schedulerni ishga tushirish
# ──────────────────────────────────────────────

def start_scheduler(bot: Bot):
    """Fon vazifalarini ishga tushirish."""
    # Ertalab soat 05:00 UTC (O'zbekiston 10:00) da kunlik hisobot
    scheduler.add_job(
        send_daily_report,
        CronTrigger(hour=5, minute=0),
        args=[bot],
        id="daily_report",
        replace_existing=True,
    )
    # Har daqiqada eslatma tekshiruvi
    scheduler.add_job(
        reminder_checker,
        "interval",
        minutes=1,
        args=[bot],
        id="reminder_checker",
        replace_existing=True,
    )
    scheduler.start()
    logging.info("✅ Scheduler ishga tushdi (daily_report + reminder_checker)")
