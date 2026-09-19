from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Kino/Multfilm qo'shish", callback_data="admin_add")],
        [InlineKeyboardButton(text="🔵 Ro'yxat", callback_data="list_all_0")],
        [InlineKeyboardButton(text="🟣 Xabar yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🟠 Majburiy obuna kanallari", callback_data="admin_channel")],
        [InlineKeyboardButton(text="💛 Qo'llab-quvvatlash matni", callback_data="admin_support")],
        [InlineKeyboardButton(text="🟡 Statistika", callback_data="admin_stats")],
    ])


def channels_list_keyboard(channels) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        title = ch[3] or ch[2] or f"Kanal #{ch[0]}"
        rows.append([InlineKeyboardButton(text=f"📢 {title}", callback_data=f"chinfo_{ch[0]}")])
    rows.append([InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="channel_add")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channel_detail_keyboard(channel_row_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"chedit_{channel_row_id}")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"chdel_{channel_row_id}")],
        [InlineKeyboardButton(text="⬅️ Ro'yxatga qaytish", callback_data="admin_channel")],
    ])


def channel_delete_confirm_keyboard(channel_row_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"chdelconfirm_{channel_row_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"chinfo_{channel_row_id}"),
        ],
    ])
