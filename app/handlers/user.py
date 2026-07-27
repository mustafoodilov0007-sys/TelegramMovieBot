from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database.db import (
    count_movies,
    get_all_movies,
    get_random_movie,
    get_top_movies,
    increment_views,
)
from app.keyboards.catalog import PAGE_SIZE, catalog_keyboard
from app.keyboards.main_menu import BTN_LIST, BTN_RANDOM, BTN_SEARCH, BTN_TOP

router = Router()

CATEGORY_EMOJI = {"kino": "🎬", "multfilm": "🧸"}


def _caption(movie) -> str:
    category = movie[5] or "kino"
    part = movie[6] or 1
    views = movie[7] or 0
    emoji = CATEGORY_EMOJI.get(category, "🎬")
    part_text = f" ({part}-qism)" if part and part > 1 else ""
    return f"{emoji} {movie[2]}{part_text}\n🔢 Kod: {movie[1]}\n👁 Ko'rishlar: {views}"


@router.message(F.text == BTN_RANDOM)
async def random_movie(message: Message):
    movie = get_random_movie()
    if not movie:
        await message.answer("📭 Hozircha baza bo'sh, birozdan keyin qayta urinib ko'ring.")
        return
    increment_views(movie[1])
    movie = list(movie)
    movie[7] = (movie[7] or 0) + 1
    await message.answer_video(movie[4], caption=_caption(movie))


@router.message(F.text == BTN_TOP)
async def top_movies(message: Message):
    movies = get_top_movies(5)
    if not movies:
        await message.answer("📭 Hozircha statistika yo'q. Birinchi bo'lib biror narsa ko'ring!")
        return

    lines = ["🏆 <b>Top 5 — eng ko'p ko'rilganlar:</b>\n"]
    buttons = []
    for i, row in enumerate(movies, start=1):
        code, title, part, views = row[1], row[2], row[6] or 1, row[7] or 0
        label = title if part <= 1 else f"{title} ({part}-qism)"
        lines.append(f"{i}. {label} — 👁 {views}")
        buttons.append([InlineKeyboardButton(text=f"{i}. {label}", callback_data=f"watch_{code}")])

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.message(F.text == BTN_SEARCH)
async def search_prompt(message: Message):
    await message.answer("🔎 Kino yoki multfilm nomini yoki kodini yozib yuboring.")


@router.message(F.text == BTN_LIST)
async def catalog_list(message: Message):
    total = count_movies()
    if total == 0:
        await message.answer("📭 Hozircha baza bo'sh.")
        return
    movies = get_all_movies(offset=0, limit=PAGE_SIZE)
    await message.answer(
        f"🎬 Barcha kino va multfilmlar ({total} ta):",
        reply_markup=catalog_keyboard(movies, 0, total),
    )


@router.callback_query(F.data.startswith("ulist_"))
async def catalog_page(callback: CallbackQuery):
    offset = int(callback.data.removeprefix("ulist_"))
    total = count_movies()
    movies = get_all_movies(offset=offset, limit=PAGE_SIZE)
    await callback.message.edit_text(
        f"🎬 Barcha kino va multfilmlar ({total} ta):",
        reply_markup=catalog_keyboard(movies, offset, total),
    )
    await callback.answer()
