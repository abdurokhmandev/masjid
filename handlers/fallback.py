from aiogram import Router, types
from database import db

router = Router()

@router.message()
async def unknown_message(message: types.Message):
    """Hech qanday boshqa handlerga mos kelmagan xabarlar."""
    lang = await db.get_user_lang(message.from_user.id) or "uz"

    if lang == "ru":
        text = (
            "🤷 Не удалось распознать команду.\n\n"
            "Используйте кнопки меню:\n"
            "📍 Найти ближайшие мечети\n"
            "🕌 Время намаза\n"
            "🧭 Направление Киблы\n"
            "⚙️ Настройки\n\n"
            "Или нажмите /start для перезапуска."
        )
    else:
        text = (
            "🤷 Buyruq aniqlanmadi.\n\n"
            "Quyidagi menyu tugmalaridan foydalaning:\n"
            "📍 Yaqin masjidlarni topish\n"
            "🕌 Namoz vaqtlari\n"
            "🧭 Qibla yo'nalishi\n"
            "⚙️ Sozlamalar\n\n"
            "Yoki /start bosing."
        )
    await message.answer(text)
