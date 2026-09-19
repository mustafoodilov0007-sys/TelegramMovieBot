from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_ID
from app.database.db import (
    count_movies,
    get_all_movies,
    get_random_movie,
    get_setting,
    get_top_movies,
    increment_views,
)
from app.keyboards.admin_menu import admin_menu_keyboard
from app.keyboards.catalog import PAGE_SIZE, catalog_keyboard
from app.keyboards.main_menu import (
    BTN_AD,
    BTN_ADMIN,
    BTN_CARTOONS,
    BTN_MOVIES,
    BTN_RANDOM,
    BTN_SEARCH,
    BTN_SUPPORT,
    BTN_TOP,
)

router = Router()

CATEGORY_EMOJI = {"kino": "🎬", "multfilm": "🧸"}
CATEGORY_TITLES = {
    "kino": "🟦 Kinolar",
    "multfilm": "🟪 Multfilmlar",
    "all": "🎬 Barcha kino va multfilmlar",
}

DEFAULT_SUPPORT_TEXT = (
    "💛 <b>Loyihani qo'llab-quvvatlash</b>\n\n"
    "Botimizdan foydalanganingiz uchun rahmat! Agar loyihani qo'llab-quvvatlamoqchi bo'lsangiz, "
    "admin bilan bog'laning."
)


class AdRequest(StatesGroup):
    waiting_message = State()


def _caption(movie) -> str:
    category = movie[5] or "kino"
    part = movie[6] or 1
    views = movie[7] or 0
    emoji = CATEGORY_EMOJI.get(category, "🎬")
    part_text = f" ({part}-qism)" if part and part > 1 else ""
    return f"{emoji} {movie[2]}{part_text}\n🔢 Kod: {movie[1]}\n👁 Ko'rishlar: {views}"


async def _show_catalog(message: Message, category: str):
    db_category = None if category == "all" else category
    total = count_movies(category=db_category)
    if total == 0:
        empty_text = (
            "📭 Bu bo'limda hozircha hech narsa yo'q."
            if category != "all"
            else "📭 Hozircha baza bo'sh."
        )
        await message.answer(empty_text)
        return
    movies = get_all_movies(offset=0, limit=PAGE_SIZE, category=db_category)
    await message.answer(
        f"{CATEGORY_TITLES[category]} ({total} ta):",
        reply_markup=catalog_keyboard(movies, 0, total, category),
    )


# ---------- Asosiy menyu tugmalari ----------
# Har bir tugma bosilganda FSM holati tozalanadi: aks holda foydalanuvchi
# "Reklama berish"ni bosib, fikridan qaytsa, keyingi qidiruv matni
# reklama so'rovi sifatida adminga ketib qolardi.

@router.message(F.text == BTN_RANDOM)
async def random_movie(message: Message, state: FSMContext):
    await state.clear()
    movie = get_random_movie()
    if not movie:
        await message.answer("📭 Hozircha baza bo'sh, birozdan keyin qayta urinib ko'ring.")
        return
    increment_views(movie[1])
    movie = list(movie)
    movie[7] = (movie[7] or 0) + 1
    await message.answer_video(movie[4], caption=_caption(movie))


@router.message(F.text == BTN_TOP)
async def top_movies(message: Message, state: FSMContext):
    await state.clear()
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
async def search_prompt(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🔎 Kino yoki multfilm nomini yoki kodini yozib yuboring.")


@router.message(F.text == BTN_MOVIES)
async def movies_list(message: Message, state: FSMContext):
    await state.clear()
    await _show_catalog(message, "kino")


@router.message(F.text == BTN_CARTOONS)
async def cartoons_list(message: Message, state: FSMContext):
    await state.clear()
    await _show_catalog(message, "multfilm")


@router.callback_query(F.data.startswith("ulist_"))
async def catalog_page(callback: CallbackQuery):
    # Format: ulist_<kategoriya>_<offset>  (masalan: ulist_kino_0, ulist_all_16)
    try:
        _, category, offset_str = callback.data.split("_", 2)
        offset = max(0, int(offset_str))
    except ValueError:
        # Eski formatdagi tugmalar (masalan: ulist_8) — jimgina o'tkazib yuboramiz
        await callback.answer()
        return

    if category not in CATEGORY_TITLES:
        await callback.answer()
        return

    db_category = None if category == "all" else category
    total = count_movies(category=db_category)
    if total == 0:
        await callback.answer("📭 Bu bo'limda hozircha hech narsa yo'q.", show_alert=True)
        return

    movies = get_all_movies(offset=offset, limit=PAGE_SIZE, category=db_category)
    try:
        await callback.message.edit_text(
            f"{CATEGORY_TITLES[category]} ({total} ta):",
            reply_markup=catalog_keyboard(movies, offset, total, category),
        )
    except TelegramBadRequest:
        # Tanlangan filtr qayta bosilganda "message is not modified" xatosi chiqadi
        pass
    await callback.answer()


# ---------- Qo'llab-quvvatlash ----------

@router.message(F.text == BTN_SUPPORT)
async def support(message: Message, state: FSMContext):
    await state.clear()
    text = get_setting("support_text", DEFAULT_SUPPORT_TEXT)
    await message.answer(text, parse_mode="HTML")


# ---------- Reklama berish ----------

@router.message(F.text == BTN_AD)
async def ad_start(message: Message, state: FSMContext):
    await message.answer(
        "📢 Reklama bermoqchi bo'lgan taklifingizni (matn, rasm yoki video) yuboring.\n\n"
        "Admin so'rovingizni ko'rib chiqib, siz bilan bog'lanadi.\n\n"
        "Bekor qilish uchun /bekor deb yozing."
    )
    await state.set_state(AdRequest.waiting_message)


@router.message(Command("bekor"), AdRequest.waiting_message)
async def ad_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


@router.message(AdRequest.waiting_message)
async def ad_send(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user = message.from_user
    username = f"@{user.username}" if user.username else "yo'q"
    info = (
        "📢 <b>Yangi reklama so'rovi</b>\n\n"
        f"👤 Foydalanuvchi: {user.full_name}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"🔗 Username: {username}"
    )
    try:
        await bot.send_message(ADMIN_ID, info, parse_mode="HTML")
        await message.copy_to(chat_id=ADMIN_ID)
    except Exception:
        await message.answer("⚠️ So'rovni yuborib bo'lmadi. Birozdan keyin qayta urinib ko'ring.")
        return
    await message.answer("✅ So'rovingiz adminga yuborildi. Tez orada siz bilan bog'lanishadi.")


# ---------- Admin panelga tezkor kirish (pastdagi tugma orqali) ----------

@router.message(F.text == BTN_ADMIN)
async def admin_button(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    await message.answer("⚙️ Admin panel:", reply_markup=admin_menu_keyboard())
