from aiogram import Router, types, F
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from database import db

router = Router()

# ──────────────────────────────────────────────
# Matnlar
# ──────────────────────────────────────────────

TEXTS = {
    "uz": {
        "btn_loc":        "📍 Yaqin masjidlarni topish",
        "choose":         (
            "🕌 <b>Yaqin masjidlarni qanday topmoqchisiz?</b>\n\n"
            "Quyidagi ikki usuldan birini tanlang:"
        ),
        "btn_gmaps":      "🗺 Google Maps'da ochish",
        "btn_send_loc":   "📍 Lokatsiya yuborish",
        "ask_location":   (
            "📍 <b>Joylashuvingizni yuboring</b>\n\n"
            "Quyidagi tugmani bosib, joylashuvingizni ulashing:"
        ),
        "send_location":  "📍 Joylashuvimni yuborish",
    },
    "ru": {
        "btn_loc":        "📍 Найти ближайшие мечети",
        "choose":         (
            "🕌 <b>Как вы хотите найти ближайшие мечети?</b>\n\n"
            "Выберите один из двух вариантов:"
        ),
        "btn_gmaps":      "🗺 Открыть в Google Maps",
        "btn_send_loc":   "📍 Отправить геолокацию",
        "ask_location":   (
            "📍 <b>Отправьте вашу геолокацию</b>\n\n"
            "Нажмите кнопку ниже, чтобы поделиться местоположением:"
        ),
        "send_location":  "📍 Отправить моё местоположение",
    },
}

# Google Maps — masjidlar filtri bilan (GPS orqali o'zi topadi)
GMAPS_MOSQUE_URL = "https://www.google.com/maps/search/masjid+yaqin/"

# ──────────────────────────────────────────────
# "Yaqin masjid" tugmasi — 2 ta variant taklif
# ──────────────────────────────────────────────

@router.message(
    F.text.in_(["📍 Yaqin masjidlarni topish", "📍 Найти ближайшие мечети"])
)
async def nearest_mosque_menu(message: types.Message):
    user_id = message.from_user.id
    lang    = await db.get_user_lang(user_id) or "uz"
    T       = TEXTS[lang]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=T["btn_gmaps"],
                url=GMAPS_MOSQUE_URL,
            )
        ],
        [
            InlineKeyboardButton(
                text=T["btn_send_loc"],
                callback_data="send_my_location",
            )
        ],
    ])

    await message.answer(T["choose"], reply_markup=keyboard)


# ──────────────────────────────────────────────
# "📍 Lokatsiya yuborish" callback
# ──────────────────────────────────────────────

from handlers.start import main_menu

@router.message(F.text.in_(["⬅️ Orqaga", "⬅️ Назад"]))
async def back_to_main(message: types.Message):
    user_id = message.from_user.id
    lang    = await db.get_user_lang(user_id) or "uz"
    await message.answer("Bosh menyu:", reply_markup=main_menu(lang))


@router.callback_query(F.data == "send_my_location")
async def ask_for_location(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang    = await db.get_user_lang(user_id) or "uz"
    T       = TEXTS[lang]

    # Foydalanuvchiga lokatsiya so'raydigan reply keyboard chiqarish
    back_btn = "⬅️ Orqaga" if lang == "uz" else "⬅️ Назад"
    location_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=T["send_location"], request_location=True)],
            [KeyboardButton(text=back_btn)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await callback.message.answer(T["ask_location"], reply_markup=location_kb)
    await callback.answer()
