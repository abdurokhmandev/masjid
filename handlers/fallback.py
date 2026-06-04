from aiogram import Router, types

router = Router()

@router.message()
async def unknown_message(message: types.Message):
    """Handle any text that doesn't match other handlers."""
    help_text = (
        "👋 Salom! Iltimos, quyidagi variantlardan birini tanlang:\n"
        "📍 Yaqin masjidlarni topish\n"
        "⚙ Sozlamalar\n"
        "🧭 Qibla yo'nalishi"
    )
    await message.answer(help_text, parse_mode="HTML")
