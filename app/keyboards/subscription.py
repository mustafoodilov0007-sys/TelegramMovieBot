from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import CHANNEL_URL
from app.database.db import get_setting


def subscription_keyboard() -> InlineKeyboardMarkup:
    url = get_setting("channel_url", CHANNEL_URL) or "https://t.me"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga o'tish", url=url)],
        [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")],
    ])
