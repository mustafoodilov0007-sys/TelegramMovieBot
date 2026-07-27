from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

PAGE_SIZE = 8
CATEGORY_EMOJI = {"kino": "🎬", "multfilm": "🧸"}


def catalog_keyboard(movies, offset, total) -> InlineKeyboardMarkup:
    buttons = []
    for row in movies:
        code, title, category, part = row[1], row[2], row[5] or "kino", row[6] or 1
        emoji = CATEGORY_EMOJI.get(category, "🎬")
        label = title if part <= 1 else f"{title} ({part}-qism)"
        buttons.append([InlineKeyboardButton(text=f"{emoji} {label}", callback_data=f"watch_{code}")])

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"ulist_{max(0, offset - PAGE_SIZE)}"))
    if offset + PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"ulist_{offset + PAGE_SIZE}"))
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)
