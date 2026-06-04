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
    broadcast = State()

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
# Foydalanuvchilar ro'yxati
# ──────────────────────────────────────────────

@router.callback_query(F.data == "adm_users", F.from_user.id == ADMIN_ID)
async def adm_users(callback: types.CallbackQuery):
    users = await db.get_all_users_with_info()
    if not users:
        await callback.answer("❌ Foydalanuvchilar yo'q", show_alert=True)
        return

    shown = users[:15]
    text = f"👥 <b>Foydalanuvchilar ro'yxati</b> (oxirgi {len(shown)} ta)\n━━━━━━━━━━━━━━━━━━━━\n"

    kb_rows = []
    for user in shown:
        uid, username, full_name, lat, lon, is_banned, last_active = user
        status = "⛔" if is_banned else ("📍" if lat else "👤")
        name = full_name or (f"@{username}" if username else str(uid))
        last = last_active[:10] if last_active else "—"
        text += f"{status} <b>{name[:18]}</b> <code>[{uid}]</code> · {last}\n"

        action_text = "✅ Unban" if is_banned else "⛔ Ban"
        action_cb   = f"adm_unban_{uid}" if is_banned else f"adm_ban_{uid}"
        kb_rows.append([
            InlineKeyboardButton(text=f"{status} {name[:14]}", callback_data="adm_noop"),
            InlineKeyboardButton(text=action_text, callback_data=action_cb),
        ])

    kb_rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back")])
    await callback.message.edit_text(
        text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
    )
    await callback.answer()

@router.callback_query(F.data == "adm_noop", F.from_user.id == ADMIN_ID)
async def adm_noop(callback: types.CallbackQuery):
    await callback.answer()

@router.callback_query(F.data.startswith("adm_ban_"), F.from_user.id == ADMIN_ID)
async def adm_ban(callback: types.CallbackQuery):
    uid = int(callback.data.replace("adm_ban_", ""))
    await db.ban_user(uid)
    await callback.answer(f"⛔ {uid} blocklandi", show_alert=True)
    await adm_users(callback)

@router.callback_query(F.data.startswith("adm_unban_"), F.from_user.id == ADMIN_ID)
async def adm_unban(callback: types.CallbackQuery):
    uid = int(callback.data.replace("adm_unban_", ""))
    await db.unban_user(uid)
    await callback.answer(f"✅ {uid} blokdan chiqarildi", show_alert=True)
    await adm_users(callback)

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
        "Barcha foydalanuvchilarga yuboriladigan\n"
        "xabarni yozing yoki media yuboring:\n\n"
        "<i>✏️ Matn, 🖼 Rasm, 🎥 Video — istalgan format</i>",
        reply_markup=kb
    )
    await state.set_state(AdminState.broadcast)
    await callback.answer()

@router.callback_query(F.data == "adm_cancel_bc", F.from_user.id == ADMIN_ID)
async def adm_cancel_bc(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = await _panel_text()
    await callback.message.edit_text(text, reply_markup=admin_main_kb())
    await callback.answer("Bekor qilindi")

@router.message(AdminState.broadcast, F.from_user.id == ADMIN_ID)
async def adm_do_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    users = await db.get_all_users()
    progress = await message.answer(
        f"📤 <b>Yuborilmoqda...</b>\n"
        f"👥 Foydalanuvchilar soni: <b>{len(users)}</b>"
    )
    success, failed = 0, 0
    for user_id in users:
        try:
            await message.copy_to(chat_id=user_id)
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