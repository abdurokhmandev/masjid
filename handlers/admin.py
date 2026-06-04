import os
import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from database import db

router = Router()
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

@router.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    count = await db.get_users_count()
    await message.answer(
        "👑 <b>Admin Panel</b>\n\n"
        f"📊 Foydalanuvchilar soni: <code>{count}</code> ta\n"
        "📢 Hamma foydalanuvchilarga xabar yuborish uchun: \n"
        "<code>/send XABAR_MATNI</code> ko'rinishida yozing."
    )

@router.message(Command("send"), F.from_user.id == ADMIN_ID)
async def broadcast_message(message: types.Message):
    # Buyruqdan keyingi matnni ajratib olamiz
    text_to_send = message.text.replace("/send", "").strip()
    
    if not text_to_send:
        await message.answer("⚠️ Iltimos xabar matnini yozing. Masalan: <code>/send Assalomu alaykum</code>")
        return
        
    users = await db.get_all_users()
    await message.answer(f"⏳ <code>{len(users)}</code> ta foydalanuvchiga xabar yuborish boshlandi...")
    
    success = 0
    for user_id in users:
        try:
            await message.bot.send_message(chat_id=user_id, text=text_to_send)
            success += 1
            await asyncio.sleep(0.05) # Telegram blocklab qo'ymasligi uchun biroz kutish
        except Exception:
            pass # Botni blocklagan foydalanuvchilar o'tkazib yuboriladi
            
    await message.answer(f"✅ Xabar tarqatish yakunlandi.\n\n🎯 Yetkazildi: {success}/{len(users)}")