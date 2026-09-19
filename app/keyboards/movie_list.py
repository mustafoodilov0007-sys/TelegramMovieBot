from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

PAGE_SIZE = 8
CATEGORY_FILTERS = [
    ("kino", "🟦 Kino"),
    ("multfilm", "🟪 Multfilm"),
    ("all", "⬜️ Hammasi"),
]


def movie_list_keyboard(movies, offset, total, category="all") -> InlineKeyboardMarkup:
    buttons = []

    filter_row = []
    for key, label in CATEGORY_FILTERS:
        text = f"✅ {label}" if key == category else label
        filter_row.append(InlineKeyboardButton(text=text, callback_data=f"list_{key}_0"))
    buttons.append(filter_row)

    for row in movies:
        code, title, part = row[1], row[2], row[6] or 1
        label = title if part <= 1 else f"{title} ({part}-qism)"
        buttons.append([InlineKeyboardButton(text=f"🎬 {label}", callback_data=f"manage_{code}")])

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Oldingi", callback_data=f"list_{category}_{max(0, offset - PAGE_SIZE)}"
        ))
    if offset + PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(
            text="Keyingi ➡️", callback_data=f"list_{category}_{offset + PAGE_SIZE}"
        ))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="admin_home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
