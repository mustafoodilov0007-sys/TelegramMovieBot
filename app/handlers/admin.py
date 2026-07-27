import asyncio
import sqlite3

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from config import ADMIN_ID, CHANNEL_ID, CHANNEL_URL
from app.database.db import (
    DB_PATH,
    add_movie as db_add_movie,
    count_movies,
    count_users,
    delete_movie,
    delete_setting,
    get_all_movies,
    get_all_user_ids,
    get_movie_by_code,
    get_setting,
    get_total_views,
    reload_connection,
    set_setting,
    update_movie,
)
from app.keyboards.admin_menu import admin_menu_keyboard, channel_settings_keyboard
from app.keyboards.category import category_keyboard
from app.keyboards.movie_actions import (
    category_edit_keyboard,
    confirm_delete_keyboard,
    movie_actions_keyboard,
)
from app.keyboards.movie_list import PAGE_SIZE, movie_list_keyboard

router = Router()


class AddMovie(StatesGroup):
    video = State()
    title = State()
    category = State()
    part = State()
    code = State()


class EditMovie(StatesGroup):
    waiting_value = State()
    waiting_video = State()


class RestoreDB(StatesGroup):
    waiting_file = State()


class Broadcast(StatesGroup):
    waiting_message = State()


class ChannelSetup(StatesGroup):
    waiting_link = State()
    waiting_forward = State()


def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def _movie_info_text(movie) -> str:
    category = movie[5] or "kino"
    part = movie[6] or 1
    return (
        f"🎬 <b>{movie[2]}</b>\n"
        f"🔢 Kod: <code>{movie[1]}</code>\n"
        f"📂 Kategoriya: {category}\n"
        f"🔁 Qism: {part}"
    )


# ---------- Admin panel bosh menyu ----------

@router.message(F.text == "/admin")
async def admin_panel(message: Message):
    if not _is_admin(message.from_user.id):
        return
    await message.answer("⚙️ Admin panel:", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "admin_home")
async def admin_home(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("⚙️ Admin panel:", reply_markup=admin_menu_keyboard())
    await callback.answer()


# ---------- Kino/multfilm qo'shish ----------

@router.message(F.text == "/add")
async def add_movie_command(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await message.answer("🎬 Kino/multfilm videosini yuboring.")
    await state.set_state(AddMovie.video)


@router.callback_query(F.data == "admin_add")
async def add_movie_callback(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🎬 Kino/multfilm videosini yuboring.")
    await state.set_state(AddMovie.video)
    await callback.answer()


@router.message(AddMovie.video, F.video)
async def get_video(message: Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await message.answer("📝 Nomini kiriting.")
    await state.set_state(AddMovie.title)


@router.message(AddMovie.title)
async def get_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("📂 Kategoriyasini tanlang:", reply_markup=category_keyboard())
    await state.set_state(AddMovie.category)


@router.callback_query(AddMovie.category, F.data.startswith("cat_"))
async def choose_category(callback: CallbackQuery, state: FSMContext):
    category = "kino" if callback.data == "cat_kino" else "multfilm"
    await state.update_data(category=category)
    await callback.message.edit_text(
        "🔁 Nechanchi qism? (Agar bitta bo'lsa — <b>1</b> deb yozing)",
        parse_mode="HTML",
    )
    await state.set_state(AddMovie.part)
    await callback.answer()


@router.message(AddMovie.part)
async def get_part(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await message.answer("⚠️ Faqat musbat raqam kiriting (masalan: 1).")
        return
    await state.update_data(part=int(text))
    await message.answer("🔢 Kodini kiriting (masalan: 101).")
    await state.set_state(AddMovie.code)


@router.message(AddMovie.code)
async def save_movie(message: Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()

    try:
        db_add_movie(
            code=code,
            title=data["title"],
            aliases=data["title"].lower(),
            file_id=data["file_id"],
            category=data.get("category", "kino"),
            part=data.get("part", 1),
        )
    except sqlite3.IntegrityError:
        await message.answer("⚠️ Bu kod band, boshqa kod kiriting.")
        return

    await message.answer("✅ Bazaga saqlandi.", reply_markup=admin_menu_keyboard())
    await state.clear()


# ---------- Ro'yxat va boshqaruv ----------

@router.callback_query(F.data.startswith("list_"))
async def list_movies(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    offset = int(callback.data.removeprefix("list_"))
    total = count_movies()

    if total == 0:
        await callback.message.edit_text("📭 Baza hozircha bo'sh.", reply_markup=admin_menu_keyboard())
        await callback.answer()
        return

    movies = get_all_movies(offset=offset, limit=PAGE_SIZE)
    await callback.message.edit_text(
        f"📋 Kinolar va multfilmlar ({total} ta):",
        reply_markup=movie_list_keyboard(movies, offset, total),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manage_"))
async def manage_movie(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    code = callback.data.removeprefix("manage_")
    movie = get_movie_by_code(code)
    if not movie:
        await callback.answer("❌ Topilmadi.", show_alert=True)
        return
    await callback.message.edit_text(
        _movie_info_text(movie), reply_markup=movie_actions_keyboard(code), parse_mode="HTML"
    )
    await callback.answer()


# ---------- Tahrirlash ----------

@router.callback_query(F.data.startswith("edit_title_"))
async def edit_title(callback: CallbackQuery, state: FSMContext):
    code = callback.data.removeprefix("edit_title_")
    await state.update_data(field="title", code=code)
    await state.set_state(EditMovie.waiting_value)
    await callback.message.edit_text("📝 Yangi nomni kiriting.")
    await callback.answer()


@router.callback_query(F.data.startswith("edit_code_"))
async def edit_code(callback: CallbackQuery, state: FSMContext):
    code = callback.data.removeprefix("edit_code_")
    await state.update_data(field="code", code=code)
    await state.set_state(EditMovie.waiting_value)
    await callback.message.edit_text("🔢 Yangi kodni kiriting.")
    await callback.answer()


@router.callback_query(F.data.startswith("edit_part_"))
async def edit_part(callback: CallbackQuery, state: FSMContext):
    code = callback.data.removeprefix("edit_part_")
    await state.update_data(field="part", code=code)
    await state.set_state(EditMovie.waiting_value)
    await callback.message.edit_text("🔁 Yangi qism raqamini kiriting (masalan: 2).")
    await callback.answer()


@router.callback_query(F.data.startswith("edit_category_"))
async def edit_category(callback: CallbackQuery):
    code = callback.data.removeprefix("edit_category_")
    await callback.message.edit_text("📂 Yangi kategoriyani tanlang:", reply_markup=category_edit_keyboard(code))
    await callback.answer()


@router.callback_query(F.data.startswith("setcat_"))
async def set_category(callback: CallbackQuery):
    _, category, code = callback.data.split("_", 2)
    update_movie(code, category=category)
    movie = get_movie_by_code(code)
    await callback.message.edit_text(
        "✅ Kategoriya yangilandi.\n\n" + _movie_info_text(movie),
        reply_markup=movie_actions_keyboard(code),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_video_"))
async def edit_video_start(callback: CallbackQuery, state: FSMContext):
    code = callback.data.removeprefix("edit_video_")
    await state.update_data(code=code)
    await state.set_state(EditMovie.waiting_video)
    await callback.message.edit_text("🎞 Yangi videoni yuboring.")
    await callback.answer()


@router.message(EditMovie.waiting_video, F.video)
async def edit_video_save(message: Message, state: FSMContext):
    data = await state.get_data()
    update_movie(data["code"], file_id=message.video.file_id)
    await message.answer("✅ Video yangilandi.", reply_markup=admin_menu_keyboard())
    await state.clear()


@router.message(EditMovie.waiting_value)
async def edit_value_save(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data["field"]
    code = data["code"]
    value = message.text.strip()

    if field == "part":
        if not value.isdigit() or int(value) < 1:
            await message.answer("⚠️ Faqat musbat raqam kiriting (masalan: 2).")
            return
        value = int(value)

    try:
        update_movie(code, **{field: value})
    except sqlite3.IntegrityError:
        await message.answer("⚠️ Bu kod band, boshqasini kiriting.")
        return

    await message.answer("✅ Yangilandi.", reply_markup=admin_menu_keyboard())
    await state.clear()


# ---------- O'chirish ----------

@router.callback_query(F.data.startswith("delete_"))
async def delete_confirm(callback: CallbackQuery):
    code = callback.data.removeprefix("delete_")
    await callback.message.edit_text("🗑 Rostdan ham o'chirmoqchimisiz?", reply_markup=confirm_delete_keyboard(code))
    await callback.answer()


@router.callback_query(F.data.startswith("confirmdelete_"))
async def delete_execute(callback: CallbackQuery):
    code = callback.data.removeprefix("confirmdelete_")
    delete_movie(code)
    await callback.message.edit_text("✅ O'chirildi.", reply_markup=admin_menu_keyboard())
    await callback.answer()


# ---------- Baza zaxirasi (backup / restore) ----------

@router.message(F.text == "/backup")
async def backup_db(message: Message):
    if not _is_admin(message.from_user.id):
        return
    await message.answer_document(FSInputFile(DB_PATH), caption="🗄 Joriy baza fayli.")


@router.message(F.text == "/restore")
async def restore_db_start(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await message.answer(
        "⚠️ Diqqat! Yuboradigan .db fayl joriy bazani <b>to'liq almashtiradi</b>.\n\n"
        "Zaxira faylni (.db) hujjat sifatida yuboring.",
        parse_mode="HTML",
    )
    await state.set_state(RestoreDB.waiting_file)


@router.message(RestoreDB.waiting_file, F.document)
async def restore_db_file(message: Message, state: FSMContext, bot: Bot):
    file = await bot.get_file(message.document.file_id)
    await bot.download_file(file.file_path, destination=DB_PATH)
    reload_connection()
    await message.answer("✅ Baza muvaffaqiyatli tiklandi.", reply_markup=admin_menu_keyboard())
    await state.clear()


# ---------- Statistika ----------

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Obunachilar: {count_users()}\n"
        f"🎬 Kino/multfilmlar soni: {count_movies()}\n"
        f"👁 Jami ko'rishlar: {get_total_views()}"
    )
    await callback.message.edit_text(text, reply_markup=admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


# ---------- Xabar yuborish (reklama / e'lon) ----------

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📢 Barcha obunachilarga yubormoqchi bo'lgan xabaringizni yuboring "
        "(matn, rasm, video — istalgani).\n\nBekor qilish uchun /bekor deb yozing."
    )
    await state.set_state(Broadcast.waiting_message)
    await callback.answer()


@router.message(F.text == "/xabar")
async def broadcast_command(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await message.answer(
        "📢 Barcha obunachilarga yubormoqchi bo'lgan xabaringizni yuboring "
        "(matn, rasm, video — istalgani).\n\nBekor qilish uchun /bekor deb yozing."
    )
    await state.set_state(Broadcast.waiting_message)


@router.message(F.text == "/bekor", Broadcast.waiting_message)
async def broadcast_cancel(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu_keyboard())


@router.message(Broadcast.waiting_message)
async def broadcast_send(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.clear()

    user_ids = get_all_user_ids()
    total = len(user_ids)
    if total == 0:
        await message.answer("📭 Hozircha obunachilar yo'q.")
        return

    status = await message.answer(f"⏳ Yuborilmoqda... 0/{total}")
    sent, failed = 0, 0

    for i, user_id in enumerate(user_ids, start=1):
        try:
            await message.copy_to(chat_id=user_id)
            sent += 1
        except Exception:
            failed += 1
        if i % 20 == 0 or i == total:
            try:
                await status.edit_text(f"⏳ Yuborilmoqda... {i}/{total}")
            except Exception:
                pass
        await asyncio.sleep(0.05)  # Telegram flood-limitiga tushmaslik uchun

    await status.edit_text(
        f"✅ Xabar yuborildi.\n\n📤 Yetib bordi: {sent}\n❌ Yetib bormadi: {failed}"
    )


# ---------- Majburiy obuna kanali ----------

@router.callback_query(F.data == "admin_channel")
async def channel_settings(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    channel_id = get_setting("channel_id", CHANNEL_ID)
    channel_url = get_setting("channel_url", CHANNEL_URL)
    has_channel = bool(channel_id)

    text = "🔒 <b>Majburiy obuna kanali</b>\n\n"
    if has_channel:
        text += (
            f"✅ Hozir sozlangan.\n"
            f"🔗 Link: {channel_url}\n"
            f"🆔 ID: <code>{channel_id}</code>\n\n"
            f"Foydalanuvchilar botdan foydalanishdan oldin shu kanalga obuna bo'lishi shart."
        )
    else:
        text += "❌ Hozircha majburiy obuna kanali sozlanmagan.\nIstalgan foydalanuvchi botdan erkin foydalana oladi."

    await callback.message.edit_text(
        text, reply_markup=channel_settings_keyboard(has_channel), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "channel_add")
async def channel_add_start(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "1️⃣ Kanalning ochiq linkini yuboring.\n\n"
        "Masalan: https://t.me/mychannel yoki https://t.me/+AbCdEfGh12345 "
        "(yopiq kanal bo'lsa, taklif linkini yuboring).\n\n"
        "Bekor qilish uchun /bekor deb yozing."
    )
    await state.set_state(ChannelSetup.waiting_link)
    await callback.answer()


@router.callback_query(F.data == "channel_remove")
async def channel_remove(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    delete_setting("channel_id")
    delete_setting("channel_url")
    await callback.message.edit_text(
        "✅ Majburiy obuna o'chirildi. Endi bot hamma uchun erkin ishlaydi.",
        reply_markup=admin_menu_keyboard(),
    )
    await callback.answer()


@router.message(ChannelSetup.waiting_link, F.text == "/bekor")
@router.message(ChannelSetup.waiting_forward, F.text == "/bekor")
async def channel_setup_cancel(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu_keyboard())


@router.message(ChannelSetup.waiting_link)
async def channel_get_link(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    link = message.text.strip()
    if not link.startswith("http"):
        await message.answer("⚠️ Iltimos, to'g'ri link yuboring (https:// bilan boshlansin).")
        return
    await state.update_data(channel_url=link)
    await message.answer(
        "2️⃣ Endi botni SHU KANALGA ADMIN qilib qo'ying (agar hali qilmagan bo'lsangiz), "
        "so'ng o'sha kanaldan istalgan bitta postni ushbu chatga FORWARD qiling — "
        "bot kanalni shundan avtomatik aniqlaydi.\n\n"
        "Bekor qilish uchun /bekor deb yozing."
    )
    await state.set_state(ChannelSetup.waiting_forward)


@router.message(ChannelSetup.waiting_forward)
async def channel_get_forward(message: Message, state: FSMContext, bot: Bot):
    if not _is_admin(message.from_user.id):
        return
    chat = message.forward_from_chat
    if not chat or chat.type != "channel":
        await message.answer(
            "⚠️ Bu kanal posti emas. Iltimos, kanaldagi istalgan bitta xabarni "
            "shu yerga forward qiling."
        )
        return

    channel_id = chat.id
    try:
        await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
    except Exception:
        await message.answer(
            "⚠️ Bot ushbu kanalda topilmadi. Iltimos, botni kanalga "
            "ADMIN sifatida qo'shing va qayta forward qiling."
        )
        return

    data = await state.get_data()
    channel_url = data.get("channel_url", "")
    set_setting("channel_id", str(channel_id))
    set_setting("channel_url", channel_url)
    await state.clear()
    await message.answer(
        f"✅ Majburiy obuna kanali sozlandi!\n\n🔗 {channel_url}",
        reply_markup=admin_menu_keyboard(),
    )
