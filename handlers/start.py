from aiogram import Router, types, F
from aiogram.filters import CommandStart
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
        "welcome": (
            "🕌 <b>Masjid Finder Botga xush kelibsiz!</b>\n\n"
            "Atrofingizdagi eng yaqin masjidlarni topish,\n"
            "namoz vaqtlarini bilish va Qibla yo'nalishini\n"
            "aniqlash uchun pastdagi tugmalardan foydalaning. 👇"
        ),
        "btn_loc":    "📍 Yaqin masjidlarni topish",
        "btn_prayer": "🕌 Namoz vaqtlari",
        "btn_qibla":  "🧭 Qibla yo'nalishi",
        "btn_sett":   "⚙️ Sozlamalar",
    },
    "ru": {
        "welcome": (
            "🕌 <b>Добро пожаловать в Masjid Finder Bot!</b>\n\n"
            "Используйте кнопки ниже, чтобы найти мечети,\n"
            "узнать время намаза и определить направление Киблы. 👇"
        ),
        "btn_loc":    "📍 Найти ближайшие мечети",
        "btn_prayer": "🕌 Время намаза",
        "btn_qibla":  "🧭 Направление Киблы",
        "btn_sett":   "⚙️ Настройки",
    },
}

# ──────────────────────────────────────────────
# Klaviatura
# ──────────────────────────────────────────────

def main_menu(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS.get(lang, TEXTS["uz"])
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["btn_loc"], request_location=True)],
            [KeyboardButton(text=t["btn_prayer"]), KeyboardButton(text=t["btn_qibla"])],
            [KeyboardButton(text=t["btn_sett"])],
        ],
        resize_keyboard=True,
    )

# ──────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    lang    = await db.get_user_lang(user_id)

    if lang:
        # Til tanlangan → menyuni ko'rsatish
        await db.update_last_active(user_id)
        await message.answer(TEXTS[lang]["welcome"], reply_markup=main_menu(lang))
    else:
        # Yangi foydalanuvchi → bazaga qo'shib til so'rash
        await db.add_user(user_id, message.from_user.username, message.from_user.full_name)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский",   callback_data="lang_ru"),
        ]])
        await message.answer(
            "🌐 Iltimos, tilni tanlang:\n🌐 Пожалуйста, выберите язык:",
            reply_markup=kb
        )

# ──────────────────────────────────────────────
# Til tanlash callback
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("lang_"))
async def select_lang(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]   # "uz" yoki "ru"
    user_id = callback.from_user.id
    await db.set_language(user_id, lang)
    await db.update_last_active(user_id)
    await callback.message.delete()
    await callback.message.answer(
        TEXTS[lang]["welcome"],
        reply_markup=main_menu(lang)
    )
    await callback.answer()