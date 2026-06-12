import asyncio
import logging
import requests
import math
from datetime import datetime, timezone, timedelta
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

# ──────────────────────────────────────────────
# Viloyatlar (sozlamalar bilan mos kelishi uchun)
# ──────────────────────────────────────────────

REGIONS = [
    ("Toshkent",    41.2995, 69.2401),
    ("Samarqand",   39.6542, 66.9597),
    ("Buxoro",      39.7680, 64.4220),
    ("Andijon",     40.7821, 72.3441),
    ("Namangan",    41.0011, 71.6726),
    ("Farg'ona",    40.3864, 71.7864),
    ("Qashqadaryo", 38.8600, 65.7900),
    ("Surxondaryo", 37.9400, 67.5700),
    ("Xorazm",      41.5500, 60.6300),
    ("Navoiy",      40.0840, 65.3792),
    ("Jizzax",      40.1158, 67.8422),
    ("Sirdaryo",    40.7497, 68.6540),
    ("Qoraqalpog'iston", 43.7682, 59.4024),
]

# ──────────────────────────────────────────────
# API
# ──────────────────────────────────────────────

REGION_API_MAP = {
    "Toshkent": "toshkent",
    "Samarqand": "samarqand",
    "Buxoro": "buxoro",
    "Andijon": "andijon",
    "Namangan": "namangan",
    "Farg'ona": "fargona",
    "Qashqadaryo": "qarshi",
    "Surxondaryo": "termiz",
    "Xorazm": "xiva",
    "Navoiy": "navoiy",
    "Jizzax": "jizzax",
    "Sirdaryo": "guliston",
    "Qoraqalpog'iston": "nukus",
}

def get_nearest_region(lat: float, lon: float) -> str:
    best_region = "Toshkent"
    min_dist = float('inf')
    for name, r_lat, r_lon in REGIONS:
        dist = math.hypot(lat - r_lat, lon - r_lon)
        if dist < min_dist:
            min_dist = dist
            best_region = name
    return best_region

def _fetch_prayer_times(region_name: str) -> tuple[dict, dict]:
    """NamozAPI dan namoz vaqtlarini olish."""
    api_id = REGION_API_MAP.get(region_name, "toshkent")
    try:
        url = f"https://namozapi.uz/namoz/{api_id}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            timings = {
                "Fajr": data.get("bomdod"),
                "Sunrise": data.get("quyosh"),
                "Dhuhr": data.get("peshin"),
                "Asr": data.get("asr"),
                "Maghrib": data.get("shom"),
                "Isha": data.get("xufton"),
            }
            meta = {"timezone": "Asia/Tashkent"}
            return timings, meta
    except Exception as e:
        logging.error(f"[prayer] API xato: {e}")
    return {}, {}

def _clean_time(raw: str) -> str:
    """'05:12 (+05)' → '05:12'"""
    return raw.split()[0] if raw and " " in raw else (raw or "—")

def _format_prayer_msg(timings: dict, lang: str, region: str, source: str) -> str:
    labels = PRAYER_LABELS.get(lang, PRAYER_LABELS["uz"])
    today  = datetime.now().strftime("%d.%m.%Y")
    lines  = []
    for key, label in labels.items():
        time = _clean_time(timings.get(key, "—"))
        lines.append(f"  {label}: <b>{time}</b>")

    if lang == "ru":
        header = (
            f"🕌 <b>Время намаза — {today}</b>\n"
            f"📍 Регион: <b>{region}</b>\n"
            f"({source})\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
        )
    else:
        header = (
            f"🕌 <b>Namoz vaqtlari — {today}</b>\n"
            f"📍 Hudud: <b>{region}</b>\n"
            f"({source})\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
        )

    return (
        header
        + "\n".join(lines) + "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤲 <i>Alloh qabul qilsin!</i>" if lang == "uz" else
        header + "\n".join(lines) + "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤲 <i>Да примет Аллах!</i>"
    )

def _change_region_kb(lang: str) -> InlineKeyboardMarkup:
    """Hududni o'zgartirish tugmasi."""
    text = "📍 Hududni o'zgartirish" if lang == "uz" else "📍 Изменить регион"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, callback_data="prayer_select_region")
    ]])

def _regions_kb_prayer(lang: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for name, lat, lon in REGIONS:
        row.append(InlineKeyboardButton(
            text=name,
            callback_data=f"prayerregion_{name}_{lat}_{lon}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    back_text = "⬅️ Orqaga" if lang == "uz" else "⬅️ Назад"
    buttons.append([InlineKeyboardButton(text=back_text, callback_data="prayer_region_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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
    lang    = await db.get_user_lang(user_id) or fallback_lang

    # Foydalanuvchi lokatsiyasi OR tanlangan viloyat
    location = await db.get_user_location(user_id)
    region, reg_lat, reg_lon = await db.get_user_region(user_id)

    if location:
        lat, lon = location
        source = "📍 Joylashuvingiz asosida" if lang == "uz" else "📍 По вашей геолокации"
        calc_region = get_nearest_region(lat, lon)
    else:
        lat, lon = reg_lat, reg_lon
        source = f"🗺 {region} hududi asosida" if lang == "uz" else f"🗺 По региону {region}"
        calc_region = region

    wait_msg = await message.answer(
        "⏳ Namoz vaqtlari yuklanmoqda..." if lang == "uz" else "⏳ Загрузка времени намаза..."
    )

    coord_key = calc_region
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    cached    = await db.get_prayer_cache(coord_key, today_str)

    if cached:
        timings = cached
    else:
        timings, meta = await asyncio.to_thread(_fetch_prayer_times, calc_region)
        if not timings:
            await wait_msg.edit_text(
                "❌ Namoz vaqtlarini olishda xatolik yuz berdi.\nIltimos, qayta urinib ko'ring." if lang == "uz" else
                "❌ Произошла ошибка при получении времени намаза.\nПожалуйста, попробуйте еще раз."
            )
            return
        await db.upsert_prayer_cache(coord_key, today_str, timings)

        # UTC offset ni saqlash
        if location:
            try:
                import zoneinfo
                tz = zoneinfo.ZoneInfo("Asia/Tashkent")
                offset_seconds = datetime.now(tz).utcoffset().total_seconds()
                offset_hours   = int(offset_seconds // 3600)
                await db.set_utc_offset(user_id, offset_hours)
            except Exception:
                pass

    await db.update_last_active(user_id)

    text = _format_prayer_msg(timings, lang, region if not location else ("Joylashuvingiz" if lang == "uz" else "Ваша геолокация"), source)
    await wait_msg.edit_text(text, reply_markup=_change_region_kb(lang))

# ──────────────────────────────────────────────
# Viloyat tanlash (namoz bo'limidan)
# ──────────────────────────────────────────────

@router.callback_query(F.data == "prayer_select_region")
async def prayer_select_region(callback: types.CallbackQuery):
    lang = await db.get_user_lang(callback.from_user.id) or "uz"
    title = (
        "📍 <b>Viloyatingizni tanlang:</b>\n\n"
        "<i>Tanlangan viloyat bo'yicha namoz vaqtlari hisoblanadi.</i>"
        if lang == "uz" else
        "📍 <b>Выберите ваш регион:</b>\n\n"
        "<i>По выбранному региону будет рассчитано время намаза.</i>"
    )
    await callback.message.edit_text(title, reply_markup=_regions_kb_prayer(lang))
    await callback.answer()


@router.callback_query(F.data.startswith("prayerregion_"))
async def set_prayer_region(callback: types.CallbackQuery):
    parts = callback.data.split("_", 3)
    if len(parts) < 4:
        await callback.answer("❌ Xatolik")
        return
    _, name, lat_str, lon_str = parts
    try:
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError:
        await callback.answer("❌ Koordinata xatolik")
        return

    user_id = callback.from_user.id
    lang    = await db.get_user_lang(user_id) or "uz"
    await db.set_user_region(user_id, name, lat, lon)

    # Yangi vaqtlarni yuklash
    loading = "⏳ Vaqtlar yuklanmoqda..." if lang == "uz" else "⏳ Загрузка времени..."
    await callback.message.edit_text(loading)

    coord_key = name
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    cached    = await db.get_prayer_cache(coord_key, today_str)

    if cached:
        timings = cached
    else:
        timings, _ = await asyncio.to_thread(_fetch_prayer_times, name)
        if timings:
            await db.upsert_prayer_cache(coord_key, today_str, timings)

    if timings:
        source = f"🗺 {name} hududi asosida" if lang == "uz" else f"🗺 По региону {name}"
        text = _format_prayer_msg(timings, lang, name, source)
        await callback.message.edit_text(text, reply_markup=_change_region_kb(lang))
    else:
        err = "❌ Vaqtlarni yuklab bo'lmadi." if lang == "uz" else "❌ Не удалось загрузить время."
        await callback.message.edit_text(err, reply_markup=_change_region_kb(lang))

    msg = f"✅ Hudud: {name}" if lang == "uz" else f"✅ Регион: {name}"
    await callback.answer(msg)


@router.callback_query(F.data == "prayer_region_back")
async def prayer_region_back(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang    = await db.get_user_lang(user_id) or "uz"
    location = await db.get_user_location(user_id)
    region, reg_lat, reg_lon = await db.get_user_region(user_id)

    if location:
        lat, lon = location
        source   = "📍 Joylashuvingiz asosida" if lang == "uz" else "📍 По вашей геолокации"
        show_region = "Joylashuvingiz" if lang == "uz" else "Ваша геолокация"
        calc_region = get_nearest_region(lat, lon)
    else:
        lat, lon   = reg_lat, reg_lon
        source     = f"🗺 {region} hududi asosida" if lang == "uz" else f"🗺 По региону {region}"
        show_region = region
        calc_region = region

    coord_key = calc_region
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    cached    = await db.get_prayer_cache(coord_key, today_str)
    if not cached:
        timings, _ = await asyncio.to_thread(_fetch_prayer_times, calc_region)
        if timings:
            await db.upsert_prayer_cache(coord_key, today_str, timings)
        else:
            timings = {}
    else:
        timings = cached

    text = _format_prayer_msg(timings, lang, show_region, source)
    await callback.message.edit_text(text, reply_markup=_change_region_kb(lang))
    await callback.answer()
