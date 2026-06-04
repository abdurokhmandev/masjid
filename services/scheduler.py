import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import db

# Global scheduler instance
scheduler = AsyncIOScheduler()

async def send_daily_report(bot: Bot):
    """Send daily prayer times report to users with daily_report_enabled = 1"""
    users = await db.get_all_users()
    # In this simplified version we iterate over all users and send report if enabled
    for user_id in users:
        settings = await db.get_user_settings(user_id)
        if not settings.get("daily_report"):
            continue
        # Retrieve latest location for user
        loc = await db.get_user_location(user_id)
        if not loc:
            continue
        lat, lon = loc
        # Use cache or fetch fresh prayer times
        coord_key = f"{round(lat, 5)},{round(lon, 5)}"
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        cached = await db.get_prayer_cache(coord_key, today_str)
        if cached:
            timings = cached
        else:
            from handlers.location import get_prayer_times  # reuse function
            timings = get_prayer_times(lat, lon)
            await db.upsert_prayer_cache(coord_key, today_str, timings)
        # Build message
        msg = (
            "📅 <b>Bugungi namoz vaqtlari:</b>\n"
            f"🔹 Bomdod: <code>{timings.get('Fajr')}</code> | Quyosh: <code>{timings.get('Sunrise')}</code>\n"
            f"🔹 Peshin: <code>{timings.get('Dhuhr')}</code> | Asr: <code>{timings.get('Asr')}</code>\n"
            f"🔹 Shom: <code>{timings.get('Maghrib')}</code> | Xufton: <code>{timings.get('Isha')}</code>"
        )
        await bot.send_message(user_id, msg, parse_mode="HTML")

async def reminder_checker(bot: Bot):
    """Check upcoming prayer times 15 minutes ahead and send reminder if enabled"""
    now = datetime.utcnow()
    future = now + timedelta(minutes=15)
    # For each user, check if any prayer time matches future hour/minute
    users = await db.get_all_users()
    for user_id in users:
        settings = await db.get_user_settings(user_id)
        if not settings.get("notifications"):
            continue
        loc = await db.get_user_location(user_id)
        if not loc:
            continue
        lat, lon = loc
        coord_key = f"{round(lat, 5)},{round(lon, 5)}"
        today_str = now.strftime("%Y-%m-%d")
        cached = await db.get_prayer_cache(coord_key, today_str)
        if not cached:
            from handlers.location import get_prayer_times
            cached = get_prayer_times(lat, lon)
            await db.upsert_prayer_cache(coord_key, today_str, cached)
        # Compare times
        for prayer, time_str in cached.items():
            try:
                prayer_time = datetime.strptime(time_str, "%H:%M")
                prayer_dt = now.replace(hour=prayer_time.hour, minute=prayer_time.minute, second=0, microsecond=0)
                if now < prayer_dt <= future:
                    await bot.send_message(
                        user_id,
                        f"📢 15 daqiqadan so'ng {prayer} namoziga kiradi.",
                        parse_mode="HTML",
                    )
            except Exception:
                continue

def start_scheduler(bot: Bot):
    """Initialize scheduler jobs and start the background loop"""
    scheduler.add_job(send_daily_report, CronTrigger(hour=8, minute=0), args=[bot], id="daily_report")
    scheduler.add_job(reminder_checker, "interval", minutes=1, args=[bot], id="reminder_checker")
    scheduler.start()
    logging.info("Scheduler started with daily report and reminder checker.")
