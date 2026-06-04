import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from database.db import init_db
from handlers import start, location, admin, settings, qibla, prayer, fallback

load_dotenv()

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    # Bazani yaratish/tekshirish
    await init_db()

    bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode="HTML"))
    # Initialize and start background scheduler
    from services.scheduler import start_scheduler
    start_scheduler(bot)
    dp = Dispatcher()

    # Handler routerlarini ro'yxatdan o'tkazish (Ketma-ketlik muhim!)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(location.router)
    dp.include_router(settings.router)
    dp.include_router(qibla.router)
    dp.include_router(prayer.router)
    dp.include_router(fallback.router)

    logging.info("Professional Masjid Bot ishga tushdi... ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")