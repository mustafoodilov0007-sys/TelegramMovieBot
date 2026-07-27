from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def movie_actions_keyboard(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Nomi", callback_data=f"edit_title_{code}"),
            InlineKeyboardButton(text="✏️ Kodi", callback_data=f"edit_code_{code}"),
        ],
        [
            InlineKeyboardButton(text="📂 Kategoriya", callback_data=f"edit_category_{code}"),
            InlineKeyboardButton(text="🔁 Qism raqami", callback_data=f"edit_part_{code}"),
        ],
        [InlineKeyboardButton(text="🎞 Videoni almashtirish", callback_data=f"edit_video_{code}")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_{code}")],
        [InlineKeyboardButton(text="⬅️ Ro'yxatga qaytish", callback_data="list_0")],
    ])


def confirm_delete_keyboard(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirmdelete_{code}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"manage_{code}"),
        ],
    ])


def category_edit_keyboard(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Kino", callback_data=f"setcat_kino_{code}")],
        [InlineKeyboardButton(text="🧸 Multfilm", callback_data=f"setcat_multfilm_{code}")],
    ])
