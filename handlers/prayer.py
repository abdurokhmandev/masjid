from aiogram import Router, types

router = Router()

# Placeholder for future prayer‑related commands.
# Currently the location handler returns prayer times, so this file can stay empty.
# You can later add commands like /today, /tomorrow, etc.

@router.message()
async def placeholder(message: types.Message):
    # No operation – prevents import errors.
    return
