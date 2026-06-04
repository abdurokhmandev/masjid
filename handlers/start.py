from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database import db

router = Router()

TEXTS = {
    "uz": {
        "welcome": "🕌 <b>Masjid Finder Botiga xush kelibsiz!</b>\n\nAtrofingizdagi eng yaqin masjidlarni topish uchun lokatsiyangizni yuboring.",
        "btn_loc": "📍 Yaqin masjidlarni topish",
    },
    "ru": {
        "welcome": "🕌 <b>Добро пожаловать в Masjid Finder Bot!</b>\n\nЧтобы найти ближайшие мечети, отправьте свою геолокацию.",
        "btn_loc": "📍 Найти ближайшие мечети",
    }
}

def main_menu_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=TEXTS[lang]["btn_loc"], request_location=True)]],
        resize_keyboard=True
    )

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    # Avval bazadan tilni tekshiramiz
    lang = await db.get_user_lang(message.from_user.id)
    
    if lang:
        # Agar til tanlangan bo'lsa, srazu menyuni chiqaramiz
        await message.answer(
            TEXTS[lang]["welcome"],
            reply_markup=main_menu_keyboard(lang)
        )
    else:
        # Agar mutlaqo yangi user bo'lsa, bazaga qo'shib tilni so'raymiz
        await db.add_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
            ]
        ])
        await message.answer("🇺🇿 Iltimos, tilni tanlang / 🇷🇺 Пожалуйста, выберите язык:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("lang_"))
async def select_lang(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    await db.set_language(callback.from_user.id, lang)
    
    await callback.message.delete()
    await callback.message.answer(
        TEXTS[lang]["welcome"],
        reply_markup=main_menu_keyboard(lang)
    )