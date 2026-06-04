from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
import logging

router = Router()

# ──────────────────────────────────────────────
# Sozlamalar klaviaturasi
# ──────────────────────────────────────────────

def _settings_kb(notif: bool, daily: bool, lang: str) -> InlineKeyboardMarkup:
    if lang == "ru":
        n_text = "🔔 Уведомления: ВКЛ" if notif else "🔕 Уведомления: ВЫКЛ"
        d_text = "🕗 Утренний отчёт: ВКЛ" if daily else "🕗 Утренний отчёт: ВЫКЛ"
        lang_text = "🌐 Язык: 🇷🇺 Русский"
        close_text = "❌ Закрыть"
    else:
        n_text = "🔔 Eslatmalar: YOQILGAN" if notif else "🔕 Eslatmalar: O'CHIRILGAN"
        d_text = "🕗 Ertalabki xabar: YOQILGAN" if daily else "🕗 Ertalabki xabar: O'CHIRILGAN"
        lang_text = "🌐 Til: 🇺🇿 O'zbekcha"
        close_text = "❌ Yopish"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=n_text, callback_data="toggle_notifications")],
        [InlineKeyboardButton(text=d_text, callback_data="toggle_daily_report")],
        [InlineKeyboardButton(text=lang_text, callback_data="change_lang")],
        [InlineKeyboardButton(text=close_text, callback_data="cancel_settings")],
    ])

def _settings_title(lang: str) -> str:
    if lang == "ru":
        return (
            "⚙️ <b>Настройки</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Нажмите кнопку, чтобы изменить:"
        )
    return (
        "⚙️ <b>Sozlamalar</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "O'zgartirish uchun tugmani bosing:"
    )

# ──────────────────────────────────────────────
# UZ va RU menyulari
# ──────────────────────────────────────────────

@router.message(F.text.in_({"⚙️ Sozlamalar", "⚙ Sozlamalar", "⚙️ Настройки"}))
async def open_settings(message: types.Message):
    user_id  = message.from_user.id
    lang     = await db.get_user_lang(user_id) or "uz"
    settings = await db.get_user_settings(user_id)
    await db.update_last_active(user_id)
    await message.answer(
        _settings_title(lang),
        reply_markup=_settings_kb(settings["notifications"], settings["daily_report"], lang),
    )

# ──────────────────────────────────────────────
# Eslatmalarni yoqish / o'chirish
# ──────────────────────────────────────────────

@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: types.CallbackQuery):
    user_id  = callback.from_user.id
    lang     = await db.get_user_lang(user_id) or "uz"
    settings = await db.get_user_settings(user_id)
    new_val  = not settings["notifications"]
    await db.set_notifications(user_id, new_val)
    new_settings = await db.get_user_settings(user_id)
    await callback.message.edit_reply_markup(
        reply_markup=_settings_kb(new_settings["notifications"], new_settings["daily_report"], lang)
    )
    msg = ("Eslatmalar " + ("yoqildi ✅" if new_val else "o'chirildi 🔕")) if lang == "uz" else \
          ("Уведомления " + ("включены ✅" if new_val else "выключены 🔕"))
    await callback.answer(msg)

# ──────────────────────────────────────────────
# Ertalabki xabar
# ──────────────────────────────────────────────

@router.callback_query(F.data == "toggle_daily_report")
async def toggle_daily_report(callback: types.CallbackQuery):
    user_id  = callback.from_user.id
    lang     = await db.get_user_lang(user_id) or "uz"
    settings = await db.get_user_settings(user_id)
    new_val  = not settings["daily_report"]
    await db.set_daily_report(user_id, new_val)
    new_settings = await db.get_user_settings(user_id)
    await callback.message.edit_reply_markup(
        reply_markup=_settings_kb(new_settings["notifications"], new_settings["daily_report"], lang)
    )
    msg = ("Ertalabki xabar " + ("yoqildi ✅" if new_val else "o'chirildi 🔕")) if lang == "uz" else \
          ("Утренний отчёт " + ("включен ✅" if new_val else "выключен 🔕"))
    await callback.answer(msg)

# ──────────────────────────────────────────────
# Tilni almashtirish
# ──────────────────────────────────────────────

@router.callback_query(F.data == "change_lang")
async def change_lang(callback: types.CallbackQuery):
    user_id  = callback.from_user.id
    cur_lang = await db.get_user_lang(user_id) or "uz"
    new_lang = "ru" if cur_lang == "uz" else "uz"
    await db.set_language(user_id, new_lang)
    settings = await db.get_user_settings(user_id)

    await callback.message.edit_text(
        _settings_title(new_lang),
        reply_markup=_settings_kb(settings["notifications"], settings["daily_report"], new_lang),
    )
    # Asosiy menyuni ham yangilash
    from handlers.start import main_menu, TEXTS
    await callback.message.answer(
        TEXTS[new_lang]["welcome"],
        reply_markup=main_menu(new_lang),
    )
    msg = "Til o'zgartirildi: O'zbekcha 🇺🇿" if new_lang == "uz" else "Язык изменён: Русский 🇷🇺"
    await callback.answer(msg)

# ──────────────────────────────────────────────
# Yopish
# ──────────────────────────────────────────────

@router.callback_query(F.data == "cancel_settings")
async def cancel_settings(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer("✅")
