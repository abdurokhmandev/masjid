import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from database.db import init_db
from handlers import start, location, admin, settings, qibla, prayer, fallback

load_dotenv()

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
    )

    # Bazani yaratish / migratsiya
    await init_db()

    bot = Bot(
        token=os.getenv("BOT_TOKEN"),
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    # FSM storage (admin broadcast uchun kerak)
    dp = Dispatcher(storage=MemoryStorage())

    # ── Routerlarni ro'yxatdan o'tkazish ──────
    # Ketma-ketlik muhim!
    dp.include_router(admin.router)     # Admin birinchi (command filter)
    dp.include_router(start.router)     # /start
    dp.include_router(prayer.router)    # 🕌 Namoz vaqtlari tugmasi
    dp.include_router(qibla.router)     # 🧭 Qibla yo'nalishi
    dp.include_router(settings.router)  # ⚙️ Sozlamalar
    dp.include_router(location.router)  # Lokatsiya (F.location)
    dp.include_router(fallback.router)  # Oxirgi — noma'lum xabarlar

    # ── Scheduler ─────────────────────────────
    from services.scheduler import start_scheduler
    start_scheduler(bot)

    logging.info("🕌 Professional Masjid Bot ishga tushdi ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")