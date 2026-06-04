from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timezone, timedelta
from database import db

router = Router()

# ──────────────────────────────────────────────
# Namoz nomlari (chiroyli ko'rinish uchun)
# ──────────────────────────────────────────────

PRAYER_LABELS = {
    "Fajr":    "🌙 Bomdod",
    "Dhuhr":   "☀️ Peshin",
    "Asr":     "🌤 Asr",
    "Maghrib": "🌆 Shom",
    "Isha":    "🌃 Xufton",
}

PRAYER_LABELS_RU = {
    "Fajr":    "🌙 Фаджр",
    "Dhuhr":   "☀️ Зухр",
    "Asr":     "🌤 Аср",
    "Maghrib": "🌆 Магриб",
    "Isha":    "🌃 Иша",
}


def get_label(prayer_name: str, lang: str) -> str:
    if lang == "ru":
        return PRAYER_LABELS_RU.get(prayer_name, prayer_name)
    return PRAYER_LABELS.get(prayer_name, prayer_name)


# ──────────────────────────────────────────────
# "O'qidim" callback
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("prayed_"))
async def cb_prayed(callback: types.CallbackQuery):
    """Callback: prayed_{prayer_name}_{date_str}"""
    parts = callback.data.split("_", 2)
    if len(parts) < 3:
        await callback.answer("❌ Xatolik yuz berdi.")
        return

    prayer_name = parts[1]
    date_str    = parts[2]
    user_id     = callback.from_user.id
    lang        = await db.get_user_lang(user_id) or "uz"
    label       = get_label(prayer_name, lang)

    await db.log_prayer(user_id, date_str, prayer_name, "prayed")

    if lang == "ru":
        confirm = (
            f"✅ <b>{label}</b> намаз отмечен как прочитанный!\n\n"
            "🤲 <i>Да примет Аллах. Аминь!</i>"
        )
    else:
        confirm = (
            f"✅ <b>{label}</b> namozi o'qildi deb belgilandi!\n\n"
            "🤲 <i>Alloh qabul qilsin. Omin!</i>"
        )

    try:
        await callback.message.edit_text(confirm)
    except Exception:
        await callback.answer(confirm[:100])
    await callback.answer()


# ──────────────────────────────────────────────
# "Qoldirdim" callback
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("qaza_"))
async def cb_qaza(callback: types.CallbackQuery):
    """Callback: qaza_{prayer_name}_{date_str}"""
    parts = callback.data.split("_", 2)
    if len(parts) < 3:
        await callback.answer("❌ Xatolik yuz berdi.")
        return

    prayer_name = parts[1]
    date_str    = parts[2]
    user_id     = callback.from_user.id
    lang        = await db.get_user_lang(user_id) or "uz"
    label       = get_label(prayer_name, lang)

    await db.log_prayer(user_id, date_str, prayer_name, "qaza")

    if lang == "ru":
        confirm = (
            f"📝 <b>{label}</b> намаз отмечен как пропущенный (казо).\n\n"
            "💡 <i>Не забудьте возместить пропущенный намаз!</i>"
        )
    else:
        confirm = (
            f"📝 <b>{label}</b> namozi qoldirildi (qazo) deb belgilandi.\n\n"
            "💡 <i>Qoldirgan namozingizni qazoga qoldirishdan qoching, "
            "imkoni boricha qazo qiling!</i>"
        )

    try:
        await callback.message.edit_text(confirm)
    except Exception:
        await callback.answer(confirm[:100])
    await callback.answer()


# ──────────────────────────────────────────────
# Yordamchi: inline tugmalar yaratish
# ──────────────────────────────────────────────

def prayer_confirm_kb(prayer_name: str, date_str: str, lang: str) -> InlineKeyboardMarkup:
    if lang == "ru":
        btn_prayed = "✅ Прочитал(а)"
        btn_qaza   = "❌ Пропустил(а)"
    else:
        btn_prayed = "✅ O'qidim"
        btn_qaza   = "❌ Qoldirdim"

    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=btn_prayed, callback_data=f"prayed_{prayer_name}_{date_str}"),
        InlineKeyboardButton(text=btn_qaza,   callback_data=f"qaza_{prayer_name}_{date_str}"),
    ]])
