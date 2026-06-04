from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
import math

router = Router()

def calculate_qibla_bearing(lat: float, lon: float) -> float:
    # Qibla (Kaaba) coordinates
    kaaba_lat, kaaba_lon = 21.4225, 39.8262
    # Convert to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    kaaba_lat_rad = math.radians(kaaba_lat)
    kaaba_lon_rad = math.radians(kaaba_lon)
    d_lon = kaaba_lon_rad - lon_rad
    x = math.sin(d_lon)
    y = math.cos(lat_rad) * math.tan(kaaba_lat_rad) - math.sin(lat_rad) * math.cos(d_lon)
    bearing = math.degrees(math.atan2(x, y))
    bearing = (bearing + 360) % 360
    return bearing

@router.message(F.text == "🧭 Qibla yo'nalishi")
async def qibla_handler(message: types.Message):
    user_id = message.from_user.id
    location = await db.get_user_location(user_id)
    if not location:
        await message.answer("📍 Iltimos, avval lokatsiyani yuboring.")
        return
    lat, lon = location
    bearing = calculate_qibla_bearing(lat, lon)
    await message.answer(f"🧭 Qibla yo'nalishi: {bearing:.1f}°");
