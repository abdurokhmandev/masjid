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
            "🕌 <b>«Masjidgacha» botining bosh sahifasiga xush kelibsiz!</b>\n\n"
            "Ushbu bot sizga ibodatlaringizni tartibli va vaqtida bajarishda ko'makchi bo'ladi.\n"
            "Quyidagi tugmalardan foydalanib kerakli bo'limga o'ting: 👇"
        ),
        "btn_loc":    "📍 Yaqin masjidlarni topish",
        "btn_prayer": "🕌 Namoz vaqtlari",
        "btn_qibla":  "🧭 Qibla yo'nalishi",
        "btn_sett":   "⚙️ Sozlamalar",
    },
    "ru": {
        "welcome": (
            "🕌 <b>Добро пожаловать на главную страницу бота «Masjidgacha»!</b>\n\n"
            "Этот бот поможет вам организованно и своевременно совершать поклонения.\n"
            "Используйте кнопки ниже для перехода в нужный раздел: 👇"
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
        # Til tanlangan → menyuni ko'rsatish, til tanlashni qayta ko'rsatmaslik
        await db.update_last_active(user_id)
        await message.answer(TEXTS[lang]["welcome"], reply_markup=main_menu(lang))
    else:
        # Yangi foydalanuvchi → bazaga qo'shib til so'rash (juda chiroyli va taklif qiluvchi matn)
        await db.add_user(user_id, message.from_user.username, message.from_user.full_name)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский",   callback_data="lang_ru"),
        ]])
        
        intro_text = (
            "✨ <b>Assalomu alaykum va rohmatullohi va barokatuh!</b> ✨\n\n"
            "Barchamizni ibodatlarimizda sobitqadam qilgan Alloh taologa hamdlar bo'lsin.\n\n"
            "<b>«Masjidgacha»</b> botiga xush kelibsiz! Ushbu bot yordamida siz:\n"
            "  📍 Eng yaqin masjidlarni va masofani aniqlashingiz;\n"
            "  🕌 O'z hududingizga mos aniq namoz vaqtlarini kuzatishingiz;\n"
            "  🎯 Namozlaringizni o'z vaqtida belgilab, qazo daftaringizni yuritishingiz;\n"
            "  🧭 Qibla yo'nalishini juda oson va aniq topishingiz mumkin.\n\n"
            "<i>Iltimos, botdan foydalanish uchun o'zingizga qulay tilni tanlang:</i>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✨ <b>Ассаляму алейкум ва рахматуллахи ва баракатух!</b> ✨\n\n"
            "Приветствуем вас в боте <b>«Masjidgacha»</b>! С помощью этого бота вы сможете:\n"
            "  📍 Находить ближайшие мечети и расстояние до них;\n"
            "  🕌 Следить за точным временем намаза для вашего региона;\n"
            "  🎯 Отмечать прочитанные намазы и вести учет пропущенных (казо);\n"
            "  🧭 Легко и точно определять направление Киблы.\n\n"
            "<i>Пожалуйста, выберите удобный для вас язык общения:</i>"
        )
        await message.answer(intro_text, reply_markup=kb)

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