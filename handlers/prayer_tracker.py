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
# "Kechki xulosa" uchun multi-select callback
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("tgl_"))
async def cb_tgl(callback: types.CallbackQuery):
    """Callback: tgl_{prayer_name}_{date_str}"""
    kb = callback.message.reply_markup.inline_keyboard
    new_kb = []
    
    for row in kb:
        new_row = []
        for btn in row:
            if btn.callback_data == callback.data:
                if btn.text.startswith("❌"):
                    new_text = btn.text.replace("❌", "✅")
                else:
                    new_text = btn.text.replace("✅", "❌")
                new_row.append(InlineKeyboardButton(text=new_text, callback_data=btn.callback_data))
            else:
                new_row.append(btn)
        new_kb.append(new_row)
    
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb))
    await callback.answer()

@router.callback_query(F.data.startswith("save_evening_"))
async def cb_save_evening(callback: types.CallbackQuery):
    """Callback: save_evening_{date_str}"""
    date_str = callback.data.replace("save_evening_", "")
    user_id = callback.from_user.id
    
    kb = callback.message.reply_markup.inline_keyboard
    
    saved_count = 0
    for row in kb:
        for btn in row:
            if btn.callback_data and btn.callback_data.startswith("tgl_"):
                parts = btn.callback_data.split("_")
                prayer_name = parts[1]
                
                status = "prayed" if btn.text.startswith("✅") else "qaza"
                await db.log_prayer(user_id, date_str, prayer_name, status)
                saved_count += 1
                
    lang = await db.get_user_lang(user_id) or "uz"
    if lang == "ru":
        text = f"✅ <b>Отчет сохранен!</b>\n\nКоличество отмеченных намазов: {saved_count}\n\n🤲 <i>Да примет Аллах!</i>"
    else:
        text = f"✅ <b>Hisobot saqlandi!</b>\n\nJami belgilangan namozlar: {saved_count}\n\n🤲 <i>Alloh ibodatlaringizni qabul qilsin!</i>"
        
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer("Saqlandi!" if lang != "ru" else "Сохранено!")


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

# ──────────────────────────────────────────────
# O'tgan kunlar hisoboti (Missing Reports)
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("fill_past_"))
async def cb_fill_past(callback: types.CallbackQuery):
    """Callback: fill_past_{date_str}"""
    date_str = callback.data.replace("fill_past_", "")
    user_id = callback.from_user.id
    lang = await db.get_user_lang(user_id) or "uz"
    
    parts = date_str.split("-")
    formatted_date = f"{parts[2]}.{parts[1]}.{parts[0]}" if len(parts) == 3 else date_str
    
    # 5 ta namoz uchun tugmalarni yaratish
    prayers = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
    kb_rows = []
    
    for p in prayers:
        status = await db.get_prayer_status(user_id, date_str, p)
        # O'tmish bo'lgani uchun yo'q yoki pending bo'lsa x qaza hisoblanadi
        is_prayed = (status == "prayed")
        mark = "✅" if is_prayed else "❌"
        
        lbl = PRAYER_LABELS_RU.get(p, p) if lang == "ru" else PRAYER_LABELS.get(p, p)
        text = f"{mark} {lbl}"
        kb_rows.append([InlineKeyboardButton(text=text, callback_data=f"tgl_{p}_{date_str}")])
        
    save_text = "💾 Сохранить" if lang == "ru" else "💾 Saqlash"
    kb_rows.append([InlineKeyboardButton(text=save_text, callback_data=f"save_evening_{date_str}")])
    
    if lang == "ru":
        msg_text = (
            f"📅 Отчет за <b>{formatted_date}</b>:\n\n"
            f"Отметьте прочитанные намазы как ✅ и нажмите Сохранить."
        )
    else:
        msg_text = (
            f"📅 <b>{formatted_date}</b> kungi hisobot:\n\n"
            f"O'qilgan namozlarni ✅ qilib belgilang va Saqlash tugmasini bosing."
        )
    
    await callback.message.edit_text(msg_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()
