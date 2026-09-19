from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

PAGE_SIZE = 8
CATEGORY_EMOJI = {"kino": "🎬", "multfilm": "🧸"}
CATEGORY_FILTERS = [
    ("kino", "🟦 Kino"),
    ("multfilm", "🟪 Multfilm"),
    ("all", "⬜️ Hammasi"),
]


def catalog_keyboard(movies, offset, total, category="all") -> InlineKeyboardMarkup:
    buttons = []

    # Kategoriya bo'yicha saralash tugmalari (tanlangani ✅ bilan belgilanadi)
    filter_row = []
    for key, label in CATEGORY_FILTERS:
        text = f"✅ {label}" if key == category else label
        filter_row.append(InlineKeyboardButton(text=text, callback_data=f"ulist_{key}_0"))
    buttons.append(filter_row)

    for row in movies:
        code, title, movie_category, part = row[1], row[2], row[5] or "kino", row[6] or 1
        emoji = CATEGORY_EMOJI.get(movie_category, "🎬")
        label = title if part <= 1 else f"{title} ({part}-qism)"
        buttons.append([InlineKeyboardButton(text=f"{emoji} {label}", callback_data=f"watch_{code}")])

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Oldingi", callback_data=f"ulist_{category}_{max(0, offset - PAGE_SIZE)}"
        ))
    if offset + PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(
            text="Keyingi ➡️", callback_data=f"ulist_{category}_{offset + PAGE_SIZE}"
        ))
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)
