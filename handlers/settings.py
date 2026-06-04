from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
import logging

router = Router()



# Helper to build settings keyboard
def settings_keyboard(notifications_enabled: bool, daily_report_enabled: bool):
    notif_text = "🔕 Eslatmalar o'chirilgan" if not notifications_enabled else "🔔 Eslatmalar yoqilgan"
    daily_text = "🕗 Ertalabki xabar o'chirilgan" if not daily_report_enabled else "🕗 Ertalabki xabar yoqilgan"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=notif_text, callback_data="toggle_notifications")],
        [InlineKeyboardButton(text=daily_text, callback_data="toggle_daily_report")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_settings")]
    ])

@router.message(F.text.strip() == "⚙ Sozlamalar")
async def open_settings(message: types.Message):
    logging.info("Sozlamalar tugmasi bosildi – user_id=%s", message.from_user.id)
    user_id = message.from_user.id
    settings = await db.get_user_settings(user_id)
    kb = settings_keyboard(settings["notifications"], settings["daily_report"])
    await message.answer("🛠 Sozlamalar:", reply_markup=kb)



@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: types.CallbackQuery):
    logging.info("toggle_notifications callback – user_id=%s", callback.from_user.id)
    user_id = callback.from_user.id
    settings = await db.get_user_settings(user_id)
    await db.set_notifications(user_id, not settings["notifications"])
    # Refresh keyboard
    new_settings = await db.get_user_settings(user_id)
    await callback.message.edit_reply_markup(reply_markup=settings_keyboard(new_settings["notifications"], new_settings["daily_report"]))
    await callback.answer("Eslatmalar holati o'zgartirildi")

@router.callback_query(F.data == "toggle_daily_report")
async def toggle_daily_report(callback: types.CallbackQuery):
    logging.info("toggle_daily_report callback – user_id=%s", callback.from_user.id)
    user_id = callback.from_user.id
    settings = await db.get_user_settings(user_id)
    await db.set_daily_report(user_id, not settings["daily_report"])
    new_settings = await db.get_user_settings(user_id)
    await callback.message.edit_reply_markup(reply_markup=settings_keyboard(new_settings["notifications"], new_settings["daily_report"]))
    await callback.answer("Ertalabki xabar holati o'zgartirildi")

@router.callback_query(F.data == "cancel_settings")
async def cancel_settings(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer("Sozlamalar yopildi")
