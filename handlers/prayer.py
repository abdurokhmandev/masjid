import asyncio
import logging
import requests
from datetime import datetime
from aiogram import Router, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database import db

router = Router()

# ──────────────────────────────────────────────
# Namoz nomlari (UZ / RU)
# ──────────────────────────────────────────────

PRAYER_LABELS = {
    "uz": {
        "Fajr":    "🌙 Bomdod",
        "Sunrise": "🌅 Quyosh chiqishi",
        "Dhuhr":   "☀️  Peshin",
        "Asr":     "🌤  Asr",
        "Maghrib": "🌆 Shom",
        "Isha":    "🌃 Xufton",
    },
    "ru": {
        "Fajr":    "🌙 Фаджр",
        "Sunrise": "🌅 Восход солнца",
        "Dhuhr":   "☀️  Зухр",
        "Asr":     "🌤  Аср",
        "Maghrib": "🌆 Магриб",
        "Isha":    "🌃 Иша",
    },
}

NO_LOC_TEXT = {
    "uz": (
        "📍 <b>Namoz vaqtlarini ko'rish uchun</b>\n\n"
        "Avval lokatsiyangizni yuboring:"
    ),
    "ru": (
        "📍 <b>Для получения времени намаза</b>\n\n"
        "Сначала отправьте свою геолокацию:"
    ),
}

LOC_BTN = {
    "uz": "📍 Lokatsiyamni yuborish",
    "ru": "📍 Отправить геолокацию",
}

# ──────────────────────────────────────────────
# API
# ──────────────────────────────────────────────

def _fetch_prayer_times(lat: float, lon: float) -> tuple[dict, dict]:
    """Aladhan API dan namoz vaqtlarini olish."""
    try:
        url = (
            f"https://api.aladhan.com/v1/timings"
            f"?latitude={lat}&longitude={lon}&method=3"
        )
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", {})
            return data.get("timings", {}), data.get("meta", {})
    except Exception as e:
        logging.error(f"[prayer] API xato: {e}")
    return {}, {}

def _clean_time(raw: str) -> str:
    """'05:12 (+05)' → '05:12'"""
    return raw.split()[0] if raw and " " in raw else (raw or "—")

def _format_prayer_msg(timings: dict, lang: str) -> str:
    labels = PRAYER_LABELS.get(lang, PRAYER_LABELS["uz"])
    today  = datetime.now().strftime("%d.%m.%Y")
    lines  = []
    for key, label in labels.items():
        time = _clean_time(timings.get(key, "—"))
        lines.append(f"  {label}: <b>{time}</b>")

    return (
        f"🕌 <b>Namoz vaqtlari — {today}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(lines) + "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📡 <i>Aladhan.com orqali hisoblangan</i>"
    )

# ──────────────────────────────────────────────
# Handler — UZ
# ──────────────────────────────────────────────

@router.message(F.text == "🕌 Namoz vaqtlari")
async def prayer_uz(message: types.Message):
    await _handle_prayer(message, "uz")

# ──────────────────────────────────────────────
# Handler — RU
# ──────────────────────────────────────────────

@router.message(F.text == "🕌 Время намаза")
async def prayer_ru(message: types.Message):
    await _handle_prayer(message, "ru")

# ──────────────────────────────────────────────
# Asosiy logika
# ──────────────────────────────────────────────

async def _handle_prayer(message: types.Message, fallback_lang: str):
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id) or fallback_lang

    location = await db.get_user_location(user_id)
    is_default = False
    if not location:
        # Default: Toshkent
        lat, lon = 41.2995, 69.2401
        is_default = True
    else:
        lat, lon = location

    wait_msg = await message.answer(
        "⏳ Namoz vaqtlari yuklanmoqda..." if lang == "uz" else "⏳ Загрузка времени намаза..."
    )

    # Keshdan tekshirish
    coord_key = f"{round(lat, 5)},{round(lon, 5)}"
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    cached = await db.get_prayer_cache(coord_key, today_str)

    if cached:
        timings = cached
    else:
        # API dan olish
        timings, meta = await asyncio.to_thread(_fetch_prayer_times, lat, lon)
        if not timings:
            await wait_msg.edit_text(
                "❌ Namoz vaqtlarini olishda xatolik yuz berdi.\nIltimos, qayta urinib ko'ring." if lang == "uz" else
                "❌ Произошла ошибка при получении времени намаза.\nПожалуйста, попробуйте еще раз."
            )
            return
        await db.upsert_prayer_cache(coord_key, today_str, timings)

        # UTC offset ni saqlash (faqat default bo'lmaganda)
        if not is_default:
            try:
                tz_str = meta.get("timezone", "")
                if tz_str:
                    import zoneinfo
                    from datetime import timezone
                    tz = zoneinfo.ZoneInfo(tz_str)
                    offset_seconds = datetime.now(tz).utcoffset().total_seconds()
                    offset_hours   = int(offset_seconds // 3600)
                    await db.set_utc_offset(user_id, offset_hours)
            except Exception:
                pass

    # Oxirgi faollikni yangilash
    await db.update_last_active(user_id)

    # Javob yuborish
    text = _format_prayer_msg(timings, lang)
    if is_default:
        if lang == "uz":
            text = (
                "⚠️ <b>Siz hali joylashuvingizni ulashmagansiz.</b>\n"
                "Toshkent shahri uchun namoz vaqtlari ko'rsatilmoqda.\n"
                "O'z joylashuvingizni yuborish uchun <b>📍 Yaqin masjidlarni topish</b> tugmasini bosing.\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n" + text
            )
        else:
            text = (
                "⚠️ <b>Вы еще не поделились геопозицией.</b>\n"
                "Показано время намаза для Ташкента.\n"
                "Чтобы отправить свою геопозицию, нажмите кнопку <b>📍 Найти ближайшие мечети</b>.\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n" + text
            )
    await wait_msg.edit_text(text)
