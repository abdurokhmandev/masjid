import io
import logging
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from database import db

router = Router()

# ──────────────────────────────────────────────
# Viloyatlar ro'yxati
# ──────────────────────────────────────────────

REGIONS = [
    ("Toshkent",    41.2995, 69.2401),
    ("Samarqand",   39.6542, 66.9597),
    ("Buxoro",      39.7680, 64.4220),
    ("Andijon",     40.7821, 72.3441),
    ("Namangan",    41.0011, 71.6726),
    ("Farg'ona",    40.3864, 71.7864),
    ("Qashqadaryo", 38.8600, 65.7900),
    ("Surxondaryo", 37.9400, 67.5700),
    ("Xorazm",      41.5500, 60.6300),
    ("Navoiy",      40.0840, 65.3792),
    ("Jizzax",      40.1158, 67.8422),
    ("Sirdaryo",    40.7497, 68.6540),
    ("Qoraqalpog'iston", 43.7682, 59.4024),
]

# ──────────────────────────────────────────────
# Sozlamalar klaviaturasi
# ──────────────────────────────────────────────

def _settings_kb(notif: bool, daily: bool, lang: str) -> InlineKeyboardMarkup:
    if lang == "ru":
        n_text     = "🔔 Уведомления: ВКЛ ✅" if notif else "🔕 Уведомления: ВЫКЛ ❌"
        d_text     = "🌅 Утренний отчёт: ВКЛ ✅" if daily else "🌅 Утренний отчёт: ВЫКЛ ❌"
        lang_text  = "🌐 Язык: 🇷🇺 Русский  →  🇺🇿"
        region_txt = "📍 Изменить регион"
        stats_text = "📊 Моя статистика"
        pdf_text   = "📄 Скачать PDF отчёт"
        close_text = "❌ Закрыть"
    else:
        n_text     = "🔔 Eslatmalar: YOQILGAN ✅" if notif else "🔕 Eslatmalar: O'CHIRILGAN ❌"
        d_text     = "🌅 Ertalabki xabar: YOQILGAN ✅" if daily else "🌅 Ertalabki xabar: O'CHIRILGAN ❌"
        lang_text  = "🌐 Til: 🇺🇿 O'zbekcha  →  🇷🇺"
        region_txt = "📍 Hududni o'zgartirish"
        stats_text = "📊 Mening natijalarim"
        pdf_text   = "📄 PDF hisobot yuklash"
        close_text = "❌ Yopish"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=n_text,     callback_data="toggle_notifications")],
        [InlineKeyboardButton(text=d_text,     callback_data="toggle_daily_report")],
        [InlineKeyboardButton(text=lang_text,  callback_data="change_lang")],
        [InlineKeyboardButton(text=region_txt, callback_data="select_region")],
        [InlineKeyboardButton(text=stats_text, callback_data="show_stats")],
        [InlineKeyboardButton(text=pdf_text,   callback_data="download_pdf")],
        [InlineKeyboardButton(text=close_text, callback_data="cancel_settings")],
    ])


def _settings_title(lang: str, region: str) -> str:
    if lang == "ru":
        return (
            "⚙️ <b>Настройки</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 Текущий регион: <b>{region}</b>\n\n"
            "Нажмите кнопку для изменения:"
        )
    return (
        "⚙️ <b>Sozlamalar</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 Joriy hudud: <b>{region}</b>\n\n"
        "O'zgartirish uchun tugmani bosing:"
    )


# ──────────────────────────────────────────────
# Sozlamalar menyusini ochish
# ──────────────────────────────────────────────

@router.message(F.text.in_({"⚙️ Sozlamalar", "⚙ Sozlamalar", "⚙️ Настройки"}))
async def open_settings(message: types.Message):
    user_id  = message.from_user.id
    lang     = await db.get_user_lang(user_id) or "uz"
    sett     = await db.get_user_settings(user_id)
    region, _, _ = await db.get_user_region(user_id)
    await db.update_last_active(user_id)
    await message.answer(
        _settings_title(lang, region),
        reply_markup=_settings_kb(sett["notifications"], sett["daily_report"], lang),
    )


# ──────────────────────────────────────────────
# Eslatmalarni yoqish / o'chirish
# ──────────────────────────────────────────────

@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: types.CallbackQuery):
    user_id  = callback.from_user.id
    lang     = await db.get_user_lang(user_id) or "uz"
    sett     = await db.get_user_settings(user_id)
    new_val  = not sett["notifications"]
    await db.set_notifications(user_id, new_val)
    new_sett = await db.get_user_settings(user_id)
    region, _, _ = await db.get_user_region(user_id)
    await callback.message.edit_text(
        _settings_title(lang, region),
        reply_markup=_settings_kb(new_sett["notifications"], new_sett["daily_report"], lang)
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
    sett     = await db.get_user_settings(user_id)
    new_val  = not sett["daily_report"]
    await db.set_daily_report(user_id, new_val)
    new_sett = await db.get_user_settings(user_id)
    region, _, _ = await db.get_user_region(user_id)
    await callback.message.edit_text(
        _settings_title(lang, region),
        reply_markup=_settings_kb(new_sett["notifications"], new_sett["daily_report"], lang)
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
    sett     = await db.get_user_settings(user_id)
    region, _, _ = await db.get_user_region(user_id)
    await callback.message.edit_text(
        _settings_title(new_lang, region),
        reply_markup=_settings_kb(sett["notifications"], sett["daily_report"], new_lang),
    )
    from handlers.start import main_menu, TEXTS
    await callback.message.answer(
        TEXTS[new_lang]["welcome"],
        reply_markup=main_menu(new_lang),
    )
    msg = "Til o'zgartirildi: O'zbekcha 🇺🇿" if new_lang == "uz" else "Язык изменён: Русский 🇷🇺"
    await callback.answer(msg)


# ──────────────────────────────────────────────
# Hududni tanlash
# ──────────────────────────────────────────────

def _regions_kb(lang: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, (name, lat, lon) in enumerate(REGIONS):
        row.append(InlineKeyboardButton(
            text=name,
            callback_data=f"setregion_{name}_{lat}_{lon}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    back_text = "⬅️ Orqaga" if lang == "uz" else "⬅️ Назад"
    buttons.append([InlineKeyboardButton(text=back_text, callback_data="back_to_settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "select_region")
async def select_region_menu(callback: types.CallbackQuery):
    lang = await db.get_user_lang(callback.from_user.id) or "uz"
    title = (
        "📍 <b>Viloyatingizni tanlang:</b>\n\n"
        "<i>Tanlangan viloyat bo'yicha namoz vaqtlari va eslatmalar sozlanadi.</i>"
        if lang == "uz" else
        "📍 <b>Выберите ваш регион:</b>\n\n"
        "<i>По выбранному региону будет рассчитано время намаза и уведомления.</i>"
    )
    await callback.message.edit_text(title, reply_markup=_regions_kb(lang))
    await callback.answer()


@router.callback_query(F.data.startswith("setregion_"))
async def set_region(callback: types.CallbackQuery):
    # Format: setregion_{name}_{lat}_{lon}
    parts = callback.data.split("_", 3)
    if len(parts) < 4:
        await callback.answer("❌ Xatolik")
        return

    _, name, lat_str, lon_str = parts
    try:
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError:
        await callback.answer("❌ Koordinata xatolik")
        return

    user_id = callback.from_user.id
    lang    = await db.get_user_lang(user_id) or "uz"
    await db.set_user_region(user_id, name, lat, lon)

    sett = await db.get_user_settings(user_id)
    await callback.message.edit_text(
        _settings_title(lang, name),
        reply_markup=_settings_kb(sett["notifications"], sett["daily_report"], lang)
    )
    msg = f"✅ Hudud o'zgartirildi: {name}" if lang == "uz" else f"✅ Регион изменён: {name}"
    await callback.answer(msg)


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: types.CallbackQuery):
    user_id  = callback.from_user.id
    lang     = await db.get_user_lang(user_id) or "uz"
    sett     = await db.get_user_settings(user_id)
    region, _, _ = await db.get_user_region(user_id)
    await callback.message.edit_text(
        _settings_title(lang, region),
        reply_markup=_settings_kb(sett["notifications"], sett["daily_report"], lang)
    )
    await callback.answer()


# ──────────────────────────────────────────────
# Statistika ko'rish
# ──────────────────────────────────────────────

PRAYER_LABELS = {
    "Fajr":    "🌙 Bomdod",
    "Dhuhr":   "☀️ Peshin",
    "Asr":     "🌤 Asr",
    "Maghrib": "🌆 Shom",
    "Isha":    "🌃 Xufton",
}


@router.callback_query(F.data == "show_stats")
async def show_stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang    = await db.get_user_lang(user_id) or "uz"
    stats   = await db.get_qaza_statistics(user_id)

    total_prayed = stats.get("total_prayed", 0)
    total_qaza   = stats.get("total_qaza", 0)
    total_all    = total_prayed + total_qaza
    percent      = int(total_prayed / total_all * 100) if total_all > 0 else 0

    # Progress bar (10 ta blok)
    filled  = int(percent / 10)
    bar     = "🟩" * filled + "⬜" * (10 - filled)

    if lang == "ru":
        lines = [
            "📊 <b>Моя статистика намазов</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"✅ Прочитано:   <b>{total_prayed}</b>",
            f"❌ Казо:        <b>{total_qaza}</b>",
            f"📅 Всего:       <b>{total_all}</b>",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"📈 Процент:     <b>{percent}%</b>",
            f"{bar}",
            "━━━━━━━━━━━━━━━━━━━━",
            "<b>По каждому намазу:</b>",
        ]
        for key, label in PRAYER_LABELS.items():
            p = stats.get(key, {})
            label_ru = {"🌙 Bomdod": "🌙 Фаджр", "☀️ Peshin": "☀️ Зухр",
                       "🌤 Asr": "🌤 Аср", "🌆 Shom": "🌆 Магриб", "🌃 Xufton": "🌃 Иша"}.get(label, label)
            lines.append(
                f"  {label_ru}:  ✅{p.get('prayed',0)}  /  ❌{p.get('qaza',0)}"
            )
    else:
        lines = [
            "📊 <b>Mening namoz natijalarim</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"✅ O'qilgan:    <b>{total_prayed}</b>",
            f"❌ Qazo:        <b>{total_qaza}</b>",
            f"📅 Jami:        <b>{total_all}</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📈 Foiz:        <b>{percent}%</b>",
            f"{bar}",
            "━━━━━━━━━━━━━━━━━━━━",
            "<b>Har bir namoz bo'yicha:</b>",
        ]
        for key, label in PRAYER_LABELS.items():
            p = stats.get(key, {})
            lines.append(
                f"  {label}:  ✅{p.get('prayed',0)}  /  ❌{p.get('qaza',0)}"
            )

    back_text = "⬅️ Sozlamalarga qaytish" if lang == "uz" else "⬅️ Назад"
    pdf_text  = "📄 PDF hisobot" if lang == "uz" else "📄 PDF отчёт"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pdf_text,  callback_data="download_pdf")],
        [InlineKeyboardButton(text=back_text, callback_data="back_to_settings")],
    ])

    await callback.message.edit_text("\n".join(lines), reply_markup=kb)
    await callback.answer()


# ──────────────────────────────────────────────
# PDF hisobot yuklash
# ──────────────────────────────────────────────

@router.callback_query(F.data == "download_pdf")
async def download_pdf(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang    = await db.get_user_lang(user_id) or "uz"

    wait_txt = "⏳ PDF hisobot tayyorlanmoqda..." if lang == "uz" else "⏳ Формируется PDF отчёт..."
    await callback.answer(wait_txt, show_alert=False)

    stats    = await db.get_qaza_statistics(user_id)
    logs     = await db.get_all_prayer_logs(user_id)
    region, _, _ = await db.get_user_region(user_id)

    # Foydalanuvchi ismi
    try:
        full_name = callback.from_user.full_name or "Foydalanuvchi"
    except Exception:
        full_name = "Foydalanuvchi"

    from services.pdf_generator import generate_pdf, REPORTLAB_AVAILABLE
    if not REPORTLAB_AVAILABLE:
        err = (
            "❌ PDF yaratish uchun <code>reportlab</code> kutubxonasi o'rnatilmagan."
            if lang == "uz" else
            "❌ Библиотека <code>reportlab</code> не установлена для создания PDF."
        )
        await callback.message.answer(err)
        return

    try:
        pdf_bytes = generate_pdf(full_name, region, stats, logs)
        if not pdf_bytes:
            raise ValueError("PDF bo'sh qaytdi")
    except Exception as e:
        logging.error(f"[settings] PDF xatolik: {e}")
        err = "❌ PDF yaratishda xatolik yuz berdi." if lang == "uz" else "❌ Ошибка при создании PDF."
        await callback.message.answer(err)
        return

    filename = f"namoz_hisobot_{user_id}.pdf"
    caption  = (
        "📄 <b>Namoz va Qazo Hisobotingiz</b>\n"
        "Masjidgacha boti tomonidan yaratildi 🕌"
        if lang == "uz" else
        "📄 <b>Ваш отчёт по намазам и казо</b>\n"
        "Сгенерировано ботом Masjidgacha 🕌"
    )

    await callback.message.answer_document(
        BufferedInputFile(pdf_bytes, filename=filename),
        caption=caption,
    )


# ──────────────────────────────────────────────
# Yopish
# ──────────────────────────────────────────────

@router.callback_query(F.data == "cancel_settings")
async def cancel_settings(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer("✅")
