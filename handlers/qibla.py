import math
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db

router = Router()

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


# ──────────────────────────────────────────────
# Yo'nalish tavsifi (inson tilidda)
# ──────────────────────────────────────────────

def get_direction_info(bearing: float, lang: str) -> tuple[str, str, str]:
    """
    Burchak asosida:
    - compass emoji
    - yo'nalish nomi (inson tilida, gradussiz)
    - amaliy ko'rsatma
    """
    b = bearing % 360

    if lang == "ru":
        directions = [
            (337.5, 360,   "⬆️", "Север",       "Встаньте лицом к северу (в сторону полюса звезды)"),
            (0,    22.5,   "⬆️", "Север",       "Встаньте лицом к северу (в сторону полюса звезды)"),
            (22.5, 67.5,   "↗️", "Северо-восток","Встаньте лицом в сторону восхода солнца, немного правее"),
            (67.5, 112.5,  "➡️", "Восток",      "Встаньте лицом к восходу солнца (утренняя сторона)"),
            (112.5,157.5,  "↘️", "Юго-восток",  "Встаньте лицом к юго-востоку — правее полудня"),
            (157.5,202.5,  "⬇️", "Юг",          "Встаньте лицом к югу (в сторону полудневного солнца)"),
            (202.5,247.5,  "↙️", "Юго-запад",   "Встаньте лицом к юго-западу — левее запада"),
            (247.5,292.5,  "⬅️", "Запад",       "Встаньте лицом к закату солнца (вечерняя сторона)"),
            (292.5,337.5,  "↖️", "Северо-запад","Встаньте лицом к северо-западу — правее севера"),
        ]
    else:
        directions = [
            (337.5, 360,   "⬆️", "Shimol",      "Shimolga — Qutb yulduziga yuzlaning"),
            (0,    22.5,   "⬆️", "Shimol",      "Shimolga — Qutb yulduziga yuzlaning"),
            (22.5, 67.5,   "↗️", "Shimol-Sharq","Quyosh chiqadigan tarafga, biroz o'ngga yuzlaning"),
            (67.5, 112.5,  "➡️", "Sharq",       "Quyosh chiqadigan tomonga (ertalab tomonga) yuzlaning"),
            (112.5,157.5,  "↘️", "Janub-Sharq", "Janubdan biroz o'ngga — tushlik Quyoshdan o'ngga"),
            (157.5,202.5,  "⬇️", "Janub",       "Janubga — tushlik Quyosh tomonga yuzlaning"),
            (202.5,247.5,  "↙️", "Janub-G'arb", "G'arbdan biroz chapga — Quyosh botishidan chapga"),
            (247.5,292.5,  "⬅️", "G'arb",       "Quyosh botadigan tomonga (kechki tomonga) yuzlaning"),
            (292.5,337.5,  "↖️", "Shimol-G'arb","Shimoldan biroz chapga — Qutb yulduzidan chapga"),
        ]

    for start, end, arrow, name, hint in directions:
        if start <= b < end:
            return arrow, name, hint
    return "⬆️", "Shimol" if lang == "uz" else "Север", ""


def draw_compass(bearing: float) -> str:
    """8 nuqtali oddiy kompas — Ka'ba belgisi bilan."""
    markers = ["·"] * 8
    idx = round(bearing / 45) % 8
    markers[idx] = "🕋"
    n, ne, e, se, s, sw, w, nw = markers
    return (
        f"<code>"
        f"        {n}   ← Shimol\n"
        f"      {nw}   {ne}\n"
        f"   {w}    +    {e}\n"
        f"      {sw}   {se}\n"
        f"        {s}   ← Janub\n"
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
    user_id    = message.from_user.id
    lang       = await db.get_user_lang(user_id) or "uz"
    location   = await db.get_user_location(user_id)
    is_default = not bool(location)

    if is_default:
        lat, lon = 41.2995, 69.2401  # Toshkent (default)
    else:
        lat, lon = location

    bearing          = calculate_qibla(lat, lon)
    arrow, name, hint = get_direction_info(bearing, lang)
    compass          = draw_compass(bearing)

    if lang == "ru":
        # Точные практические инструкции без градусов
        text = (
            "🧭 <b>Направление Киблы</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🕋 Кибла находится в направлении: <b>{arrow} {name}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Как найти направление без компаса:</b>\n"
            f"  👉 {hint}\n\n"
            "🌤 <b>По солнцу:</b>\n"
            "  • Утром (восход слева) → Кибла чуть левее полудня\n"
            "  • Полдень (солнце на юге) → Кибла немного западнее юга\n"
            "  • Вечером (закат справа) → Кибла правее севера\n\n"
            "🌟 <b>По Полярной звезде (ночью):</b>\n"
            "  Найдите Полярную звезду (самая яркая на севере)\n"
            "  и повернитесь к Кибле согласно указанию выше.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{compass}\n"
            "🕋 — обозначает направление Каабы на компасе выше."
        )
    else:
        text = (
            "🧭 <b>Qibla Yo'nalishi</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🕋 Qibla yo'nalishi: <b>{arrow} {name}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Kompasiz qanday topasiz:</b>\n"
            f"  👉 {hint}\n\n"
            "☀️ <b>Quyosh orqali mo'ljal olish:</b>\n"
            "  • Ertalab (quyosh chiqayotganda) → Qibla peshin tomonga, biroz chapga\n"
            "  • Peshinda (quyosh janubda) → Qibla janubdan biroz g'arbga\n"
            "  • Kechqurun (quyosh botayotganda) → Qibla shimoldan biroz chapga\n\n"
            "🌟 <b>Qutb yulduzi orqali (kechasi):</b>\n"
            "  Qutb yulduzini (shimoldagi eng yorqin yulduz) toping,\n"
            "  keyin yuqoridagi ko'rsatmaga mos yuzlaning.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{compass}\n"
            "🕋 — yuqoridagi kompasda Ka'ba tomoni ko'rsatilgan."
        )

    # Default location handling – show informative message with button
    if is_default:
        # Message text with markdown formatting
        intro_text = (
            "✨ <b>Interaktiv Qibla Kompasi 🕋</b>\n\n"
            "Qayerda bo'lishingizdan qat'iy nazar, namoz vaqtlari va Qibla tomonni to'g'ri topish endi yanada qulay!\n\n"
            "👇 Pastdagi tugmani bosing va smartfoningizni tekis joyga qo'ying:"
        )
        button = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Qiblani aniqlash 🕋", url="https://masjidhtml.vercel.app/")]])
        await message.answer(intro_text, reply_markup=button, parse_mode="HTML")
    else:
        # Send the detailed Qibla direction text
        await message.answer(text)
    await db.update_last_active(user_id)
