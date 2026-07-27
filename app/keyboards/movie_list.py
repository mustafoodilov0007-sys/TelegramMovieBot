from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

PAGE_SIZE = 8


def movie_list_keyboard(movies, offset, total) -> InlineKeyboardMarkup:
    buttons = []
    for row in movies:
        code, title, part = row[1], row[2], row[6] or 1
        label = title if part <= 1 else f"{title} ({part}-qism)"
        buttons.append([InlineKeyboardButton(text=f"🎬 {label}", callback_data=f"manage_{code}")])

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"list_{max(0, offset - PAGE_SIZE)}"))
    if offset + PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"list_{offset + PAGE_SIZE}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="admin_home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
