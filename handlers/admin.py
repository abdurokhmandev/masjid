import os
import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db

router = Router()
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# ──────────────────────────────────────────────
# FSM holatlari
# ──────────────────────────────────────────────

class AdminState(StatesGroup):
    broadcast_msg = State()
    broadcast_btn = State()

# ──────────────────────────────────────────────
# Klaviaturalar
# ──────────────────────────────────────────────

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistika",        callback_data="adm_stats"),
            InlineKeyboardButton(text="👥 Foydalanuvchilar",  callback_data="adm_users"),
        ],
        [InlineKeyboardButton(text="📢 Broadcast xabar",      callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="🔔 Qolib ketgan hisobotlar", callback_data="adm_missing_reports")],
        [InlineKeyboardButton(text="🔄 Yangilash",            callback_data="adm_refresh")],
    ])

# ──────────────────────────────────────────────
# Yordamchi funksiya
# ──────────────────────────────────────────────

async def _panel_text() -> str:
    total  = await db.get_users_count()
    active = await db.get_active_users_count()
    banned = await db.get_banned_count()
    return (
        "👑 <b>Admin Paneli</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Jami foydalanuvchilar:  <b>{total}</b>\n"
        f"📍 Lokatsiyali (faol):     <b>{active}</b>\n"
        f"⛔ Blocklangan:             <b>{banned}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

# ──────────────────────────────────────────────
# Asosiy panel
# ──────────────────────────────────────────────

@router.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    text = await _panel_text()
    await message.answer(text, reply_markup=admin_main_kb())

@router.callback_query(F.data == "adm_refresh", F.from_user.id == ADMIN_ID)
async def adm_refresh(callback: types.CallbackQuery):
    text = await _panel_text()
    await callback.message.edit_text(text, reply_markup=admin_main_kb())
    await callback.answer("✅ Yangilandi!")

@router.callback_query(F.data == "adm_back", F.from_user.id == ADMIN_ID)
async def adm_back(callback: types.CallbackQuery):
    text = await _panel_text()
    await callback.message.edit_text(text, reply_markup=admin_main_kb())
    await callback.answer()

# ──────────────────────────────────────────────
# Statistika
# ──────────────────────────────────────────────

@router.callback_query(F.data == "adm_stats", F.from_user.id == ADMIN_ID)
async def adm_stats(callback: types.CallbackQuery):
    total  = await db.get_users_count()
    active = await db.get_active_users_count()
    banned = await db.get_banned_count()
    text = (
        "📊 <b>Bot Statistikasi</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Jami foydalanuvchi:  <b>{total}</b> ta\n"
        f"📍 Lokatsiyali:         <b>{active}</b> ta\n"
        f"⛔ Blocklangan:          <b>{banned}</b> ta\n"
        f"✅ Faol (ban yo'q):      <b>{total - banned}</b> ta\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

# ──────────────────────────────────────────────
# Foydalanuvchilar ro'yxati (Paginatsiya bilan)
# ──────────────────────────────────────────────

@router.callback_query(F.data == "adm_users", F.from_user.id == ADMIN_ID)
async def adm_users_first_page(callback: types.CallbackQuery):
    await _show_users_page(callback, page=1)

@router.callback_query(F.data.startswith("adm_users_page_"), F.from_user.id == ADMIN_ID)
async def adm_users_page(callback: types.CallbackQuery):
    page = int(callback.data.replace("adm_users_page_", ""))
    await _show_users_page(callback, page=page)

async def _show_users_page(callback: types.CallbackQuery, page: int):
    users = await db.get_all_users_for_admin()
    if not users:
        await callback.answer("❌ Foydalanuvchilar yo'q", show_alert=True)
        return

    PER_PAGE = 10
    total_users = len(users)
    total_pages = (total_users + PER_PAGE - 1) // PER_PAGE
    
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    
    start_idx = (page - 1) * PER_PAGE
    end_idx = start_idx + PER_PAGE
    shown = users[start_idx:end_idx]
    
    text = (
        f"👥 <b>Foydalanuvchilar ro'yxati</b>\n"
        f"Jami: {total_users} ta (Sahifa {page}/{total_pages})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Batafsil ma'lumot uchun ism ustiga bosing:"
    )
    
    kb_rows = []
    for user in shown:
        uid, username, full_name, is_banned = user
        status = "⛔" if is_banned else "👤"
        name = full_name or (f"@{username}" if username else str(uid))
        
        btn_text = f"{status} {name}"
        # Callback data uzunligi chegarasidan chiqmasligi uchun qisqa yozamiz
        kb_rows.append([InlineKeyboardButton(text=btn_text, callback_data=f"adm_usr_{uid}_{page}")])

    # Paginatsiya tugmalari
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"adm_users_page_{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"adm_users_page_{page+1}"))
        
    if nav_row:
        kb_rows.append(nav_row)
        
    kb_rows.append([InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="adm_back")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()

# ──────────────────────────────────────────────
# Foydalanuvchi profili
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_usr_"), F.from_user.id == ADMIN_ID)
async def adm_user_profile(callback: types.CallbackQuery):
    # data = adm_usr_{uid}_{page}
    parts = callback.data.split("_")
    uid = int(parts[2])
    page = int(parts[3])
    
    info = await db.get_user_full_info(uid)
    if not info:
        await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
        return
        
    full_name = info.get('full_name') or "Kiritilmagan"
    username = f"@{info.get('username')}" if info.get('username') else "Mavjud emas"
    first_active = info.get('first_active')
    last_active = info.get('last_active') or "Noma'lum"
    is_banned = info.get('is_banned', 0)
    
    total_p = info.get('total_prayed', 0)
    total_q = info.get('total_qaza', 0)
    
    status_text = "⛔ Bloklangan" if is_banned else "✅ Faol"
    
    text = (
        f"👤 <b>Foydalanuvchi profili</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Ismi:</b> {full_name}\n"
        f"<b>ID:</b> <code>{uid}</code>\n"
        f"<b>Username:</b> {username}\n"
        f"<b>Status:</b> {status_text}\n\n"
        f"<b>Ilk faollik sanasi:</b> {first_active}\n"
        f"<b>Oxirgi faolligi:</b> {last_active}\n\n"
        f"📊 <b>Namoz statistikasi:</b>\n"
        f"✅ O'qilgan: <b>{total_p}</b> ta\n"
        f"❌ Qazo (qoldirilgan): <b>{total_q}</b> ta\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    
    # Tugmalar
    url_btn = InlineKeyboardButton(text="🔗 Profilga o'tish", url=f"tg://user?id={uid}")
    action_text = "✅ Blokdan chiqarish" if is_banned else "⛔ Bloklash (Ban)"
    action_cb = f"adm_tglban_{uid}_{page}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [url_btn],
        [InlineKeyboardButton(text=action_text, callback_data=action_cb)],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"adm_users_page_{page}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("adm_tglban_"), F.from_user.id == ADMIN_ID)
async def adm_tglban(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    uid = int(parts[2])
    page = int(parts[3])
    
    info = await db.get_user_full_info(uid)
    if not info:
        await callback.answer("Topilmadi", show_alert=True)
        return
        
    is_banned = info.get('is_banned', 0)
    if is_banned:
        await db.unban_user(uid)
        await callback.answer(f"✅ {uid} blokdan chiqarildi", show_alert=True)
    else:
        await db.ban_user(uid)
        await callback.answer(f"⛔ {uid} bloklandi", show_alert=True)
        
    # Qayta profilni yuklaymiz
    callback.data = f"adm_usr_{uid}_{page}"
    await adm_user_profile(callback)

# ──────────────────────────────────────────────
# Broadcast
# ──────────────────────────────────────────────

@router.callback_query(F.data == "adm_broadcast", F.from_user.id == ADMIN_ID)
async def adm_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm_cancel_bc")]
    ])
    await callback.message.edit_text(
        "📢 <b>Broadcast xabar yuborish</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni yoki mediani yuboring "
        "(yoki forward qiling).",
        reply_markup=kb
    )
    await state.set_state(AdminState.broadcast_msg)
    await callback.answer()

@router.callback_query(F.data == "adm_cancel_bc", F.from_user.id == ADMIN_ID)
async def adm_cancel_bc(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = await _panel_text()
    await callback.message.edit_text(text, reply_markup=admin_main_kb())
    await callback.answer("Bekor qilindi")

@router.message(AdminState.broadcast_msg, F.from_user.id == ADMIN_ID)
async def adm_bc_get_msg(message: types.Message, state: FSMContext):
    # Xabarni FSMda saqlab qolamiz (ID va chat_id orqali keyinchalik copy qilish uchun)
    await state.update_data(bc_message_id=message.message_id, bc_chat_id=message.chat.id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ O'tkazib yuborish (Tugmasiz)", callback_data="adm_bc_skip_btn")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm_cancel_bc")]
    ])
    
    await message.answer(
        "🎛 <b>Tugmalar qo'shish</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Agar xabarga inline tugmalar qo'shmoqchi bo'lsangiz, quyidagi formatda yuboring:\n\n"
        "<code>Tugma matni | https://link.uz</code>\n\n"
        "Agar bir nechta tugma kerak bo'lsa, har birini yangi qatordan yozing:\n"
        "<code>Tugma 1 | https://link1.uz\nTugma 2 | https://link2.uz</code>\n\n"
        "Agar tugma kerak bo'lmasa, «O'tkazib yuborish» ni bosing.",
        reply_markup=kb
    )
    await state.set_state(AdminState.broadcast_btn)

from aiogram import Bot

async def _show_bc_preview(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_id = data.get("bc_message_id")
    chat_id = data.get("bc_chat_id")
    reply_markup = data.get("bc_reply_markup")
    
    # Klaviatura obyektini tiklash
    kb = None
    if reply_markup:
        kb = InlineKeyboardMarkup.model_validate(reply_markup)
        
    await message.answer("👀 <b>Xabar premyerasi (shunday ko'rinadi):</b>")
    await bot.copy_message(
        chat_id=message.chat.id,
        from_chat_id=chat_id,
        message_id=msg_id,
        reply_markup=kb
    )
    
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Barchaga yuborish", callback_data="adm_bc_send")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm_cancel_bc")]
    ])
    await message.answer("Yuboramizmi?", reply_markup=confirm_kb)

@router.callback_query(F.data == "adm_bc_skip_btn", AdminState.broadcast_btn, F.from_user.id == ADMIN_ID)
async def adm_bc_skip_btn(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await state.update_data(bc_reply_markup=None)
    await _show_bc_preview(callback.message, state, bot)
    await callback.answer()

@router.message(AdminState.broadcast_btn, F.from_user.id == ADMIN_ID)
async def adm_bc_get_btn(message: types.Message, state: FSMContext, bot: Bot):
    # Tugmalarni parsing qilish
    lines = message.text.split("\n")
    kb_rows = []
    for line in lines:
        if "|" in line:
            parts = line.split("|", 1)
            text = parts[0].strip()
            url = parts[1].strip()
            if url.startswith("http"):
                kb_rows.append([InlineKeyboardButton(text=text, url=url)])
                
    if not kb_rows:
        await message.answer("⚠️ Noto'g'ri format. Iltimos qaytadan yuboring yoki O'tkazib yuborishni bosing.")
        return
        
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    # Json formatida saqlaymiz (aiogram 3 da model_dump ishlatiladi)
    await state.update_data(bc_reply_markup=kb.model_dump())
    
    await _show_bc_preview(message, state, bot)

@router.callback_query(F.data == "adm_bc_send", F.from_user.id == ADMIN_ID)
async def adm_bc_send(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_id = data.get("bc_message_id")
    chat_id = data.get("bc_chat_id")
    reply_markup = data.get("bc_reply_markup")
    
    kb = None
    if reply_markup:
        kb = InlineKeyboardMarkup.model_validate(reply_markup)
        
    await state.clear()
    
    users = await db.get_all_users()
    progress = await callback.message.answer(
        f"📤 <b>Yuborilmoqda...</b>\n"
        f"👥 Foydalanuvchilar soni: <b>{len(users)}</b>"
    )
    
    success, failed = 0, 0
    for u_id in users:
        try:
            await bot.copy_message(
                chat_id=u_id,
                from_chat_id=chat_id,
                message_id=msg_id,
                reply_markup=kb
            )
            success += 1
            await asyncio.sleep(0.05)   # Telegram flood limitidan himoya
        except Exception:
            failed += 1

    await progress.edit_text(
        "✅ <b>Broadcast yakunlandi!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📤 Muvaffaqiyatli:  <b>{success}</b>\n"
        f"❌ Yetkazilmadi:   <b>{failed}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await callback.answer()

# ──────────────────────────────────────────────
# O'tgan kunlar uchun eslatma (Missing Reports)
# ──────────────────────────────────────────────

@router.callback_query(F.data == "adm_missing_reports", F.from_user.id == ADMIN_ID)
async def adm_missing_reports(callback: types.CallbackQuery, bot: Bot):
    progress = await callback.message.answer("⏳ <b>Hisobotlar tekshirilmoqda...</b>\nBu biroz vaqt olishi mumkin.")
    await callback.answer()
    
    missing_data = await db.get_users_missing_reports(days_back=3)
    if not missing_data:
        await progress.edit_text("✅ <b>Barcha foydalanuvchilar hisobotlarni topshirgan!</b>\nQolib ketganlar yo'q.")
        return
        
    sent_count = 0
    for uid, dates in missing_data.items():
        for d_str in dates:
            # Sana formatini o'zgartiramiz: 2026-06-05 -> 05.06.2026
            parts = d_str.split("-")
            formatted_date = f"{parts[2]}.{parts[1]}.{parts[0]}" if len(parts) == 3 else d_str
            
            text = (
                f"⚠️ <b>Assalomu alaykum!</b>\n\n"
                f"Siz <b>{formatted_date}</b> kungi namozlaringizni belgilashni unutgansiz.\n"
                f"Iltimos, o'sha kun uchun hisobotingizni yakunlab qo'ying!"
            )
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"📅 {formatted_date} ni belgilash", callback_data=f"fill_past_{d_str}")]
            ])
            
            try:
                await bot.send_message(uid, text, reply_markup=kb, parse_mode="HTML")
                sent_count += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
                
    await progress.edit_text(
        f"✅ <b>Qolib ketgan hisobotlar bo'yicha eslatmalar yuborildi!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Foydalanuvchilar soni: <b>{len(missing_data)}</b>\n"
        f"📤 Yuborilgan xabarlar: <b>{sent_count}</b>"
    )