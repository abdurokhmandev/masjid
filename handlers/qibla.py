import math
from aiogram import Router, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database import db

router = Router()

# ──────────────────────────────────────────────
# Kompas yo'nalishlari
# ──────────────────────────────────────────────

DIRECTIONS = [
    ("⬆️", "Shimol",         "N"),
    ("↗️", "Shimol-Sharq",   "NE"),
    ("➡️", "Sharq",          "E"),
    ("↘️", "Janub-Sharq",    "SE"),
    ("⬇️", "Janub",          "S"),
    ("↙️", "Janub-G'arb",    "SW"),
    ("⬅️", "G'arb",          "W"),
    ("↖️", "Shimol-G'arb",   "NW"),
]

# ──────────────────────────────────────────────
# Hisoblash
# ──────────────────────────────────────────────

def calculate_qibla(lat: float, lon: float) -> float:
    """Ka'ba tomon burchakni hisoblaydi (0–360°)."""
    kaaba_lat = math.radians(21.4225)
    kaaba_lon = math.radians(39.8262)
    lat_r     = math.radians(lat)
    lon_r     = math.radians(lon)
    d_lon     = kaaba_lon - lon_r
    x         = math.sin(d_lon)
    y         = math.cos(lat_r) * math.tan(kaaba_lat) - math.sin(lat_r) * math.cos(d_lon)
    bearing   = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360

def bearing_info(bearing: float) -> tuple[str, str, str]:
    """Burchak → (emoji arrow, uzbek nomi, short code)."""
    idx = round(bearing / 45) % 8
    return DIRECTIONS[idx]

def draw_compass(bearing: float) -> str:
    """
    8 nuqtali ASCII kompas.
    Qibla yo'nalishi [🕋] bilan belgilanadi.
    """
    # Kompas nuqtalari tartibida: N NE E SE S SW W NW
    markers = ["·"] * 8
    idx = round(bearing / 45) % 8
    markers[idx] = "🕋"

    n, ne, e, se, s, sw, w, nw = markers
    return (
        f"<code>"
        f"        {n}  ← Shimol (N)\n"
        f"      {nw}   {ne}\n"
        f"   {w}    +    {e}\n"
        f"      {sw}   {se}\n"
        f"        {s}  ← Janub (S)\n"
        f"</code>"
    )

# ──────────────────────────────────────────────
# Handlerlar
# ──────────────────────────────────────────────

@router.message(F.text == "🧭 Qibla yo'nalishi")
async def qibla_uz(message: types.Message):
    await _handle_qibla(message)

@router.message(F.text == "🧭 Направление Киблы")
async def qibla_ru(message: types.Message):
    await _handle_qibla(message)

async def _handle_qibla(message: types.Message):
    user_id  = message.from_user.id
    lang     = await db.get_user_lang(user_id) or "uz"
    location = await db.get_user_location(user_id)

    if not location:
        loc_text = (
            "📍 <b>Qibla yo'nalishini topish uchun</b>\n\nAvval lokatsiyangizni yuboring:"
            if lang == "uz" else
            "📍 <b>Для определения направления Киблы</b>\n\nСначала отправьте геолокацию:"
        )
        btn_text = "📍 Lokatsiyamni yuborish" if lang == "uz" else "📍 Отправить геолокацию"
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=btn_text, request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await message.answer(loc_text, reply_markup=kb)
        return

    lat, lon = location
    bearing  = calculate_qibla(lat, lon)
    arrow, name_uz, short = bearing_info(bearing)
    compass  = draw_compass(bearing)

    text = (
        "🧭 <b>Qibla Yo'nalishi</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📐 Burchak:    <b>{bearing:.1f}°</b>\n"
        f"🗺  Yo'nalish:  <b>{arrow} {name_uz} ({short})</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🧭 <b>Kompas:</b>\n\n"
        f"{compass}\n"
        f"<b>{arrow} 🕋 Ka'ba tomonga yuzlaning: {name_uz}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📡 <i>Makka Mukarrama koordinatalari\n"
        "    (21.4225°N, 39.8262°E) asosida</i>"
    )
    await message.answer(text)
    await db.update_last_active(user_id)
