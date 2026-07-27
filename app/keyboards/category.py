from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def category_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Kino", callback_data="cat_kino")],
        [InlineKeyboardButton(text="🧸 Multfilm", callback_data="cat_multfilm")],
    ])
