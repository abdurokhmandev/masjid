import asyncio
import logging
import requests
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from geopy.distance import geodesic
from database import db

router = Router()

# ──────────────────────────────────────────────
# Matnlar
# ──────────────────────────────────────────────

LOC_TEXTS = {
    "uz": {
        "searching":     "🔄 Atrofingizdan masjidlar qidirilmoqda...",
        "not_found":     (
            "🕌 <b>Afsuski, 5 km radius ichida masjid topilmadi.</b>\n\n"
            "💡 <i>Iltimos, ochiq joydagi masjid bo'lmagan hududlarda radius katta bo'lishi mumkin. "
            "Qo'lda qidirish uchun Google Maps'da \"mosque\" deb qidiring.</i>"
        ),
        "mosques_title": "🕌 <b>Yaqin atrofdagi masjidlar:</b>",
        "route_btn":     "🗺 Yo'l ko'rsatish",
        "error":         "❌ Qidiruvda xatolik yuz berdi. Qayta urinib ko'ring.",
        "saved_loc":     "✅ Joylashuvingiz saqlandi!",
        "distance":      "Masofa",
        "address":       "Manzil",
        "open_hours":    "Ish vaqti",
        "phone":         "Tel",
    },
    "ru": {
        "searching":     "🔄 Ищу ближайшие мечети...",
        "not_found":     (
            "🕌 <b>К сожалению, в радиусе 5 км мечетей не найдено.</b>\n\n"
            "💡 <i>Попробуйте поискать вручную в Google Maps — введите \"мечеть\".</i>"
        ),
        "mosques_title": "🕌 <b>Ближайшие мечети:</b>",
        "route_btn":     "🗺 Маршрут",
        "error":         "❌ Произошла ошибка при поиске. Попробуйте ещё раз.",
        "saved_loc":     "✅ Геолокация сохранена!",
        "distance":      "Расстояние",
        "address":       "Адрес",
        "open_hours":    "Часы работы",
        "phone":         "Тел",
    },
}

# ──────────────────────────────────────────────
# API — Overpass (OpenStreetMap)
# ──────────────────────────────────────────────

def _search_mosques(lat: float, lon: float, radius: int = 5000) -> list:
    """OpenStreetMap Overpass API orqali masjidlarni izlash."""
    servers = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
    ]
    query = (
        f"[out:json][timeout:15];"
        f"("
        f'node["amenity"="place_of_worship"]["religion"="muslim"](around:{radius},{lat},{lon});'
        f'way["amenity"="place_of_worship"]["religion"="muslim"](around:{radius},{lat},{lon});'
        f");"
        f"out center;"
    )
    for url in servers:
        try:
            r = requests.post(
                url,
                data={"data": query},
                headers={"User-Agent": "MasjidgachaBot/1.0"},
                timeout=12,
            )
            if r.status_code == 200:
                return r.json().get("elements", [])
        except Exception as e:
            logging.warning(f"[location] Overpass xato: {e}")
    return []

# ──────────────────────────────────────────────
# Location handler
# ──────────────────────────────────────────────

@router.message(F.location)
async def handle_location(message: types.Message):
    user_id  = message.from_user.id
    lang     = await db.get_user_lang(user_id) or "uz"
    T        = LOC_TEXTS[lang]
    user_lat = message.location.latitude
    user_lon = message.location.longitude

    # Lokatsiyani saqlash
    await db.update_user_location(user_id, user_lat, user_lon)
    await db.update_last_active(user_id)

    wait_msg = await message.answer(T["searching"])

    try:
        elements = await asyncio.to_thread(_search_mosques, user_lat, user_lon)

        if not elements:
            await wait_msg.edit_text(T["not_found"])
            return

        # ── Masjidlarni saralash va tozalash ──────────
        mosques, seen = [], set()
        for el in elements:
            tags = el.get("tags", {})

            # Masjid nomini olish (til bo'yicha)
            name = (
                tags.get(f"name:{lang}")
                or tags.get("name:uz")
                or tags.get("name")
                or ("Masjid" if lang == "uz" else "Мечеть")
            )

            # Koordinatalar
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if not (lat and lon):
                continue

            key = (round(lat, 4), round(lon, 4))
            if key in seen:
                continue
            seen.add(key)

            # Masofa
            dist_km  = geodesic((user_lat, user_lon), (lat, lon)).km
            dist_str = (
                f"{int(dist_km * 1000)} m"
                if dist_km < 1.0
                else f"{dist_km:.2f} km"
            )

            # Manzil
            addr_parts = list(filter(None, [
                tags.get("addr:city"),
                tags.get("addr:street"),
                tags.get("addr:housenumber"),
            ]))
            address = ", ".join(addr_parts)

            # Qo'shimcha ma'lumotlar
            phone      = tags.get("contact:phone") or tags.get("phone", "")
            open_hours = tags.get("opening_hours", "")
            website    = tags.get("website") or tags.get("contact:website", "")

            mosques.append({
                "name": name, "lat": lat, "lon": lon,
                "dist": dist_km, "dist_str": dist_str,
                "address": address,
                "phone": phone,
                "open_hours": open_hours,
                "website": website,
            })

        top3 = sorted(mosques, key=lambda x: x["dist"])[:3]

        if not top3:
            await wait_msg.edit_text(T["not_found"])
            return

        # ── Javob matni va tugmalar ─────────────────
        emojis  = ["1️⃣", "2️⃣", "3️⃣"]
        text    = T["mosques_title"] + "\n━━━━━━━━━━━━━━━━━━━━\n"
        buttons = []

        for i, m in enumerate(top3):
            text += f"\n{emojis[i]} <b>{m['name']}</b>\n"
            text += f"   📏 {T['distance']}: <b>{m['dist_str']}</b>\n"

            if m["address"]:
                text += f"   📍 {T['address']}: <code>{m['address']}</code>\n"
            if m["phone"]:
                text += f"   📞 {T['phone']}: <code>{m['phone']}</code>\n"
            if m["open_hours"]:
                text += f"   🕐 {T['open_hours']}: <i>{m['open_hours']}</i>\n"

            text += "──────────────────\n"

            gmaps = (
                f"https://www.google.com/maps/dir/?api=1"
                f"&origin={user_lat},{user_lon}"
                f"&destination={m['lat']},{m['lon']}"
                f"&travelmode=walking"
            )
            btn_label = f"{T['route_btn']} {emojis[i]} {m['name'][:18]}"
            row = [InlineKeyboardButton(text=btn_label, url=gmaps)]

            # Agar veb sayt bo'lsa
            if m["website"]:
                row.append(InlineKeyboardButton(text="🌐", url=m["website"]))

            buttons.append(row)

        await wait_msg.delete()
        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            disable_web_page_preview=True,
        )

    except Exception as e:
        logging.error(f"[location] Xatolik: {e}")
        await wait_msg.edit_text(T["error"])