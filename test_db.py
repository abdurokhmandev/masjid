import asyncio
import aiosqlite
from database.db import DB_PATH, get_users_with_notifications, get_user_location, get_all_users
from services.scheduler import _fetch_prayer_times

async def test():
    print(f"DB Path: {DB_PATH}")
    users = await get_users_with_notifications()
    print(f"Users with notifications: {users}")
    all_u = await get_all_users()
    print(f"All users: {all_u}")
    if users:
        loc = await get_user_location(users[0])
        print(f"Location for user {users[0]}: {loc}")
        if loc:
            times = _fetch_prayer_times(loc[0], loc[1])
            print(f"Times: {times}")

asyncio.run(test())
