import asyncio
import logging
import requests
from aiogram import Router, types, F
from geopy.distance import geodesic
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db

router = Router()

LOC_TEXTS = {
    "uz": {
        "searching": "🔄 Atrofingizdan masjidlar va namoz vaqtlari qidirilmoqda...",
        "not_found": "⚠️ Afsuski, 5 km radius ichida masjid topilmadi.",
        "p_times": "📅 <b>Bugungi namoz vaqtlari:</b>",
        "mosques_title": "\n🕌 <b>Yaqin atrofdagi masjidlar:</b>\n",
        "distance": "Masofa:",
        "address": "Manzil:",
        "error": "❌ Qidiruvda xatolik yuz berdi. Qayta urinib ko'ring."
    },
    "ru": {
        "searching": "🔄 Ищу мечети и время намаза поблизости...",
        "not_found": "⚠️ К сожалению, в радиусе 5 км мечетей не найдено.",
        "p_times": "📅 <b>Время намаза на сегодня:</b>",
        "mosques_title": "\n🕌 <b>Ближайшие мечети:</b>\n",
        "distance": "Расстояние:",
        "address": "Адрес:",
        "error": "❌ Произошла ошибка при поиске. Попробуйте еще раз."
    }
}

# Namoz vaqtlarini olish funksiyasi
def get_prayer_times(lat: float, lon: float) -> dict:
    try:
        url = f"https://api.aladhan.com/v1/timings?latitude={lat}&longitude={lon}&method=3"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("data", {}).get("timings", {})
    except Exception as e:
        logging.error(f"Namoz vaqtlarini olishda xato: {e}")
    return {}

def search_mosques_osm(lat: float, lon: float, radius_meters: int = 5000) -> list:
    servers = ["https://overpass-api.de/api/interpreter", "https://lz4.overpass-api.de/api/interpreter"]
    query = (
        f"[out:json][timeout:15];"
        f"("
        f'node["amenity"="place_of_worship"]["religion"="muslim"](around:{radius_meters},{lat},{lon});'
        f'way["amenity"="place_of_worship"]["religion"="muslim"](around:{radius_meters},{lat},{lon});'
        f");"
        f"out center;"
    )
    for url in servers:
        try:
            r = requests.post(url, data={"data": query}, headers={"User-Agent": "MasjidFinderPro/3.0"}, timeout=12)
            if r.status_code == 200: return r.json().get("elements", [])
        except: pass
    return []

@router.message(F.location)
async def handle_location(message: types.Message):
    lang = await db.get_user_lang(message.from_user.id) or "uz"
    wait_msg = await message.answer(LOC_TEXTS[lang]["searching"])

    user_lat = message.location.latitude
    user_lon = message.location.longitude
    
    try:
        # Namoz vaqtlari va masjidlarni parallel ravishda chaqiramiz
        p_times, elements = await asyncio.gather(
            asyncio.to_thread(get_prayer_times, user_lat, user_lon),
            asyncio.to_thread(search_mosques_osm, user_lat, user_lon)
        )
        
        # 1. Namoz vaqtlarini formatlash
        response_text = ""
        if p_times:
            response_text += (
                f"{LOC_TEXTS[lang]['p_times']}\n"
                f"🔹 Bomdod: <code>{p_times.get('Fajr')}</code> | Quyosh: <code>{p_times.get('Sunrise')}</code>\n"
                f"🔹 Peshin: <code>{p_times.get('Dhuhr')}</code> | Asr: <code>{p_times.get('Asr')}</code>\n"
                f"🔹 Shom: <code>{p_times.get('Maghrib')}</code> | Xufton: <code>{p_times.get('Isha')}</code>\n"
                f"═══════════════════════\n"
            )

        if not elements:
            await wait_msg.edit_text(response_text + LOC_TEXTS[lang]["not_found"])
            return

        # 2. Masjidlarni saralash
        mosques = []
        seen_coordinates = set()
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get(f"name:{lang}") or tags.get("name") or tags.get("name:uz") or "Masjid"
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            
            if not lat or not lon: continue
            coord_key = (round(lat, 5), round(lon, 5))
            if coord_key in seen_coordinates: continue
            seen_coordinates.add(coord_key)

            addr_parts = [tags.get("addr:city"), tags.get("addr:street"), tags.get("addr:housenumber")]
            address = ", ".join(filter(None, addr_parts))

            dist = geodesic((user_lat, user_lon), (lat, lon)).km
            dist_str = f"{int(dist * 1000)} m" if dist < 1.0 else f"{dist:.2f} km"

            mosques.append({"name": name, "address": address, "lat": lat, "lon": lon, "dist": dist, "dist_str": dist_str})

        sorted_mosques = sorted(mosques, key=lambda x: x["dist"])[:3]

        # 3. Bloklarni birlashtirish
        response_text += LOC_TEXTS[lang]["mosques_title"]
        response_text += "──────────────────\n"
        
        inline_keyboard = []
        emojis = ["1️⃣", "2️⃣", "3️⃣"]

        for i, mosque in enumerate(sorted_mosques):
            response_text += f"\n{emojis[i]} <b>{mosque['name']}</b>\n"
            response_text += f"└ 📏 {LOC_TEXTS[lang]['distance']} <b>{mosque['dist_str']}</b>\n"
            if mosque['address']:
                response_text += f"└ 📍 {LOC_TEXTS[lang]['address']} <code>{mosque['address']}</code>\n"
            response_text += "──────────────────\n"
            
            google_maps_url = f"https://www.google.com/maps/dir/?api=1&origin={user_lat},{user_lon}&destination={mosque['lat']},{mosque['lon']}&travelmode=walking"
            inline_keyboard.append([InlineKeyboardButton(text=f"🗺 {emojis[i]} {mosque['name']}", url=google_maps_url)])

        await wait_msg.delete()
        await message.answer(response_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard), disable_web_page_preview=True)

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await wait_msg.edit_text(LOC_TEXTS[lang]["error"])