from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database.db import get_channels


def subscription_keyboard(channels=None) -> InlineKeyboardMarkup:
    """channels berilmasa, bazadagi barcha majburiy kanallarni ko'rsatadi.
    Har bir kanal alohida 'obuna bo'lish' tugmasi bilan, pastda bitta tekshirish tugmasi."""
    if channels is None:
        channels = get_channels()

    rows = []
    for ch in channels:
        title = ch[3] or "Kanalga o'tish"
        url = ch[2] or "https://t.me"
        rows.append([InlineKeyboardButton(text=f"🔒 {title}", url=url)])

    rows.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
