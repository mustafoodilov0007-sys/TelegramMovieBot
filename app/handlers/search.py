from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database.db import get_movie_by_code, increment_views, search_movies

router = Router()

CATEGORY_EMOJI = {"kino": "🎬", "multfilm": "🧸"}
MAX_CHOICES = 10


def _caption(movie) -> str:
    category = movie[5] or "kino"
    part = movie[6] or 1
    views = movie[7] or 0
    emoji = CATEGORY_EMOJI.get(category, "🎬")
    part_text = f" ({part}-qism)" if part and part > 1 else ""
    return f"{emoji} {movie[2]}{part_text}\n🔢 Kod: {movie[1]}\n👁 Ko'rishlar: {views}"


@router.message(F.text & ~F.text.startswith("/"))
async def search_movie(message: Message):
    text = message.text.strip()
    results = search_movies(text)

    if not results:
        await message.answer("❌ Hech narsa topilmadi. Kod yoki nomni tekshirib qayta yuboring.")
        return

    if len(results) == 1:
        movie = results[0]
        increment_views(movie[1])
        movie = list(movie)
        movie[7] = (movie[7] or 0) + 1
        await message.answer_video(movie[4], caption=_caption(movie))
        return

    titles = {row[2] for row in results}
    buttons = []

    if len(titles) == 1:
        # bitta nom, bir nechta qism — 1, 2, 3...
        for row in sorted(results, key=lambda r: (r[6] or 1)):
            part = row[6] or 1
            buttons.append([InlineKeyboardButton(text=f"{part}-qism", callback_data=f"watch_{row[1]}")])
        await message.answer(
            f"🎬 «{results[0][2]}» topildi — qismni tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
    else:
        for row in results[:MAX_CHOICES]:
            part = row[6] or 1
            label = row[2] if part <= 1 else f"{row[2]} ({part}-qism)"
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"watch_{row[1]}")])
        await message.answer(
            "🔎 Bir nechta natija topildi, kerakligini tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )


@router.callback_query(F.data.startswith("watch_"))
async def watch_movie(callback: CallbackQuery):
    code = callback.data.removeprefix("watch_")
    movie = get_movie_by_code(code)
    if not movie:
        await callback.answer("❌ Topilmadi.", show_alert=True)
        return
    increment_views(code)
    movie = list(movie)
    movie[7] = (movie[7] or 0) + 1
    await callback.message.answer_video(movie[4], caption=_caption(movie))
    await callback.answer()
