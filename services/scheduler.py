import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import db

# ──────────────────────────────────────────────
# Global scheduler
# ──────────────────────────────────────────────

UZ_TZ = ZoneInfo("Asia/Tashkent")
scheduler = AsyncIOScheduler(timezone=UZ_TZ)

# ──────────────────────────────────────────────
# Yordamchi funksiyalar
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
# Namoz nomlari
# ──────────────────────────────────────────────

PRAYER_NAMES_UZ = {
    "Fajr":    "🌙 Bomdod",
    "Dhuhr":   "☀️ Peshin",
    "Asr":     "🌤 Asr",
    "Maghrib": "🌆 Shom",
    "Isha":    "🌃 Xufton",
}

PRAYER_NAMES_RU = {
    "Fajr":    "🌙 Фаджр",
    "Dhuhr":   "☀️ Зухр",
    "Asr":     "🌤 Аср",
    "Maghrib": "🌆 Магриб",
    "Isha":    "🌃 Иша",
}

def get_label(prayer_name: str, lang: str) -> str:
    if lang == "ru":
        return PRAYER_NAMES_RU.get(prayer_name, prayer_name)
    return PRAYER_NAMES_UZ.get(prayer_name, prayer_name)

# ──────────────────────────────────────────────
# Kunlik ertalabki hisobot (05:00 UTC = 10:00 UZB)
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
            utc_offset = await db.get_user_utc_offset(user_id)
            user_tz    = timezone(timedelta(hours=utc_offset))
            today_str  = datetime.now(user_tz).strftime("%Y-%m-%d")
            today_fmt  = datetime.now(user_tz).strftime("%d.%m.%Y")
            lang       = await db.get_user_lang(user_id) or "uz"
            region, _, _ = await db.get_user_region(user_id)

            cached = await db.get_prayer_cache(coord_key, today_str)
            if cached:
                timings = cached
            else:
                timings = await asyncio.to_thread(_fetch_prayer_times, lat, lon)
                if timings:
                    await db.upsert_prayer_cache(coord_key, today_str, timings)
                else:
                    continue

            if lang == "ru":
                msg = (
                    f"🌅 <b>Ассаляму алейкум!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📅 <b>Время намаза на {today_fmt}</b>\n"
                    f"📍 Регион: <b>{region}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🌙 Фаджр:      <b>{_clean_time(timings.get('Fajr', '—'))}</b>\n"
                    f"☀️  Зухр:       <b>{_clean_time(timings.get('Dhuhr', '—'))}</b>\n"
                    f"🌤 Аср:        <b>{_clean_time(timings.get('Asr', '—'))}</b>\n"
                    f"🌆 Магриб:     <b>{_clean_time(timings.get('Maghrib', '—'))}</b>\n"
                    f"🌃 Иша:        <b>{_clean_time(timings.get('Isha', '—'))}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🤲 <i>Да примет Аллах ваши молитвы!</i>"
                )
            else:
                msg = (
                    f"🌅 <b>Assalomu alaykum!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📅 <b>Bugungi namoz vaqtlari — {today_fmt}</b>\n"
                    f"📍 Hudud: <b>{region}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🌙 Bomdod:     <b>{_clean_time(timings.get('Fajr', '—'))}</b>\n"
                    f"☀️  Peshin:     <b>{_clean_time(timings.get('Dhuhr', '—'))}</b>\n"
                    f"🌤 Asr:        <b>{_clean_time(timings.get('Asr', '—'))}</b>\n"
                    f"🌆 Shom:       <b>{_clean_time(timings.get('Maghrib', '—'))}</b>\n"
                    f"🌃 Xufton:     <b>{_clean_time(timings.get('Isha', '—'))}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🤲 <i>Alloh namozlaringizni qabul qilsin!</i>"
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

# RAM keshi o'chirildi — endi DB ishlatiladi

async def reminder_checker(bot: Bot):
    """Har daqiqada:
    - Namoz vaqtiga 15 daqiqa qolganida eslatma.
    - Namoz vaqtidan 30 daqiqa o'tganda 'O'qidingizmi?' so'rovi.
    """
    users = await db.get_users_with_notifications()
    for user_id in users:
        try:
            lang = await db.get_user_lang(user_id) or "uz"

            loc = await db.get_user_location(user_id)
            if not loc:
                continue

            lat, lon = loc
            utc_offset = await db.get_user_utc_offset(user_id)
            user_tz    = timezone(timedelta(hours=utc_offset))
            now        = datetime.now(user_tz)
            today_str  = now.strftime("%Y-%m-%d")

            coord_key = f"{round(lat, 5)},{round(lon, 5)}"
            cached = await db.get_prayer_cache(coord_key, today_str)
            if not cached:
                cached = await asyncio.to_thread(_fetch_prayer_times, lat, lon)
                if cached:
                    await db.upsert_prayer_cache(coord_key, today_str, cached)
                else:
                    continue

            for prayer_key in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
                time_str = _clean_time(cached.get(prayer_key, ""))
                if not time_str or ":" not in time_str:
                    continue
                try:
                    h, m = map(int, time_str.split(":"))
                    prayer_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                except ValueError:
                    continue

                # Vaqt farqini aniq daqiqalarda hisoblash (soniyalarni olib tashlab)
                diff_minutes = (int(prayer_dt.timestamp()) - int(now.timestamp())) // 60

                label = get_label(prayer_key, lang)
                reminder_key = f"{user_id}_{today_str}_{prayer_key}_reminder"
                tracker_key  = f"{user_id}_{today_str}_{prayer_key}_tracker"

                # ─── 15 daqiqa oldin eslatma ───────────────────
                if 14 <= diff_minutes <= 15:
                    if not await db.is_notification_sent(reminder_key):
                        await db.mark_notification_sent(reminder_key)
                        mins = int(diff_minutes)
                        if lang == "ru":
                            text = (
                                f"🔔 <b>До намаза {label} осталось {mins} минут!</b>\n\n"
                                f"⏰ Время: <b>{time_str}</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n"
                                f"🤲 <i>Да примет Аллах!</i>"
                            )
                        else:
                            text = (
                                f"🔔 <b>{label} namoziga {mins} daqiqa qoldi!</b>\n\n"
                                f"⏰ Vaqti: <b>{time_str}</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n"
                                f"🤲 <i>Alloh qabul qilsin!</i>"
                            )
                        await bot.send_message(user_id, text, parse_mode="HTML")

                # ─── 30 daqiqa o'tgach so'rovnoma ───────────────
                elif -31 <= diff_minutes <= -29:
                    if not await db.is_notification_sent(tracker_key):
                        # Avval belgilanmagan bo'lsa so'rov yuborish
                        status = await db.get_prayer_status(user_id, today_str, prayer_key)
                        if status and status in ("prayed", "qaza"):
                            await db.mark_notification_sent(tracker_key)
                            continue

                        await db.mark_notification_sent(tracker_key)

                        from handlers.prayer_tracker import prayer_confirm_kb
                        if lang == "ru":
                            text = (
                                f"🕌 <b>Намаз {label} начался 30 минут назад.</b>\n\n"
                                f"Вы совершили намаз вовремя?"
                            )
                        else:
                            text = (
                                f"🕌 <b>{label} namoz vaqti 30 daqiqa oldin boshlangan edi.</b>\n\n"
                                f"Namozingizni o'z vaqtida o'qidingizmi?"
                            )
                        await bot.send_message(
                            user_id, text,
                            parse_mode="HTML",
                            reply_markup=prayer_confirm_kb(prayer_key, today_str, lang)
                        )

        except Exception as e:
            logging.warning(f"[scheduler] reminder {user_id}: {e}")

# ──────────────────────────────────────────────
# Soat 22:00 da eslatma (belgilanmagan namozlar)
# ──────────────────────────────────────────────

async def evening_summary(bot: Bot):
    """Har kuni soat 22:00 (O'zbekiston vaqti) da belgilanmagan namozlar haqida xabar."""
    users = await db.get_all_users()
    for user_id in users:
        try:
            settings = await db.get_user_settings(user_id)
            if not settings.get("notifications"):
                continue

            utc_offset = await db.get_user_utc_offset(user_id)
            user_tz    = timezone(timedelta(hours=utc_offset))
            today_str  = datetime.now(user_tz).strftime("%Y-%m-%d")
            today_fmt  = datetime.now(user_tz).strftime("%d.%m.%Y")
            lang       = await db.get_user_lang(user_id) or "uz"

            unanswered = await db.get_unanswered_prayers(user_id, today_str)
            if not unanswered:
                continue  # Hammasi belgilangan, xabar yuborish shart emas

            labels = [get_label(p, lang) for p in unanswered]

            from handlers.prayer_tracker import prayer_confirm_kb

            if lang == "ru":
                lines = "\n".join(f"  • {l}" for l in labels)
                text = (
                    f"🌙 <b>Добрый вечер! Итог дня {today_fmt}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📋 Следующие намазы не отмечены:\n{lines}\n\n"
                    f"Пожалуйста, отметьте их ниже:"
                )
            else:
                lines = "\n".join(f"  • {l}" for l in labels)
                text = (
                    f"🌙 <b>Xayrli kech! {today_fmt} kuni yakunlanmoqda</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📋 Quyidagi namozlar belgilanmagan:\n{lines}\n\n"
                    f"Iltimos, quyidagi tugmalar orqali belgilang:"
                )

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            buttons = []
            for p in unanswered:
                lbl = get_label(p, lang)
                # Standart holatda hali belgilanmagan (❌)
                btn_text = f"❌ {lbl}"
                buttons.append([
                    InlineKeyboardButton(text=btn_text, callback_data=f"tgl_{p}_{today_str}")
                ])
            
            # Saqlash tugmasi
            save_text = "💾 Сохранить" if lang == "ru" else "💾 Saqlash"
            buttons.append([
                InlineKeyboardButton(text=save_text, callback_data=f"save_evening_{today_str}")
            ])

            await bot.send_message(
                user_id, text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
            await asyncio.sleep(0.05)
        except Exception as e:
            logging.warning(f"[scheduler] evening_summary {user_id}: {e}")

# ──────────────────────────────────────────────
# Yarim tun: belgilanmaganlarni avtomatik qaza
# ──────────────────────────────────────────────

async def midnight_qaza_mark(bot: Bot):
    """Har kuni yarim tunda (23:59) hali belgilanmagan namozlarni qazo deb belgilash."""
    users = await db.get_all_users()
    for user_id in users:
        try:
            utc_offset = await db.get_user_utc_offset(user_id)
            user_tz    = timezone(timedelta(hours=utc_offset))
            today_str  = datetime.now(user_tz).strftime("%Y-%m-%d")
            await db.mark_remaining_qaza(user_id, today_str)
        except Exception as e:
            logging.warning(f"[scheduler] midnight_qaza {user_id}: {e}")

    # Eski eslatmalarni tozalash + kesh yangilash
    await db.clear_old_notifications(days=2)
    logging.info("[scheduler] Yarim tun: belgilanmagan namozlar qaza qilindi, eski eslatmalar tozalandi.")

# ──────────────────────────────────────────────
# Schedulerni ishga tushirish
# ──────────────────────────────────────────────

def start_scheduler(bot: Bot):
    """Fon vazifalarini ishga tushirish."""

    # Ertalabki namoz vaqtlari hisoboti (05:00 UZT)
    scheduler.add_job(
        send_daily_report,
        CronTrigger(hour=5, minute=0, timezone=UZ_TZ),
        args=[bot],
        id="daily_report",
        replace_existing=True,
    )

    # Har daqiqada: 15 min eslatma + 30 min so'rovnoma
    scheduler.add_job(
        reminder_checker,
        "interval",
        minutes=1,
        args=[bot],
        id="reminder_checker",
        replace_existing=True,
    )

    # Soat 22:00 UZT da kechki xulosa
    scheduler.add_job(
        evening_summary,
        CronTrigger(hour=22, minute=0, timezone=UZ_TZ),
        args=[bot],
        id="evening_summary",
        replace_existing=True,
    )

    # Yarim tun 23:59 UZT da avtomatik qaza belgilash
    scheduler.add_job(
        midnight_qaza_mark,
        CronTrigger(hour=23, minute=59, timezone=UZ_TZ),
        args=[bot],
        id="midnight_qaza",
        replace_existing=True,
    )

    scheduler.start()
    logging.info("✅ Scheduler ishga tushdi: daily_report | reminder_checker | evening_summary | midnight_qaza")
