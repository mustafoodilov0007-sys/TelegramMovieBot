from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kino/Multfilm qo'shish", callback_data="admin_add")],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="list_0")],
        [InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🔒 Majburiy obuna kanali", callback_data="admin_channel")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
    ])


def channel_settings_keyboard(has_channel: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text="🔁 Kanalni o'zgartirish" if has_channel else "➕ Kanal qo'shish",
        callback_data="channel_add",
    )]]
    if has_channel:
        rows.append([InlineKeyboardButton(text="🚫 Majburiy obunani o'chirish", callback_data="channel_remove")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
