"""
Admin panel handlerlari.

ESLATMA (tuzatish haqida):
Avval bu faylda handler kodi umuman yo'q edi — uning o'rniga xato bilan
ma'lumotlar bazasi kodi yozilgan edi, shuning uchun bot.py dagi
`from app.handlers.admin import router` qatori darhol xato berardi
va bot umuman ishga tushmasdi. Baza kodi endi o'z joyida
(app/database/db.py), bu yerda esa haqiqiy admin handlerlari.
"""

import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID
from app.database.db import (
    add_channel,
    add_movie,
    count_movies,
    count_users,
    delete_channel,
    delete_movie,
    get_all_movies,
    get_all_user_ids,
    get_channel,
    get_channels,
    get_movie_by_code,
    get_total_views,
    set_setting,
    update_channel,
    update_movie,
)
from app.keyboards.admin_menu import (
    admin_menu_keyboard,
    channel_delete_confirm_keyboard,
    channel_detail_keyboard,
    channels_list_keyboard,
)
from app.keyboards.category import category_keyboard
from app.keyboards.movie_actions import (
    category_edit_keyboard,
    confirm_delete_keyboard,
    movie_actions_keyboard,
)
from app.keyboards.movie_list import PAGE_SIZE, movie_list_keyboard

router = Router()

CATEGORY_LABEL = {"kino": "🟦 Kino", "multfilm": "🟪 Multfilm"}


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# =========================
# FSM HOLATLARI
# =========================

class AddMovie(StatesGroup):
    category = State()
    code = State()
    title = State()
    aliases = State()
    part = State()
    video = State()


class EditMovie(StatesGroup):
    title = State()
    code = State()
    part = State()
    video = State()


class Broadcast(StatesGroup):
    message = State()


class SupportText(StatesGroup):
    text = State()


class ChannelAdd(StatesGroup):
    channel_id = State()
    url = State()
    title = State()


class ChannelEdit(StatesGroup):
    channel_id = State()
    url = State()
    title = State()


# =========================
# ASOSIY MENYU
# =========================

@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("⚙️ <b>Admin panel</b>", parse_mode="HTML",
                         reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "admin_home")
async def admin_home(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.clear()
    await callback.message.edit_text("⚙️ <b>Admin panel</b>", parse_mode="HTML",
                                     reply_markup=admin_menu_keyboard())
    await callback.answer()


@router.message(Command("bekor"))
async def cancel_any(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if await state.get_state() is None:
        return
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu_keyboard())


# =========================
# KINO QO'SHISH
# =========================

@router.callback_query(F.data == "admin_add")
async def add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(AddMovie.category)
    await callback.message.edit_text("📂 Kategoriyani tanlang:", reply_markup=category_keyboard())
    await callback.answer()


@router.callback_query(AddMovie.category, F.data.startswith("cat_"))
async def add_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.removeprefix("cat_")
    await state.update_data(category=category)
    await state.set_state(AddMovie.code)
    await callback.message.edit_text(
        f"{CATEGORY_LABEL.get(category, category)} tanlandi.\n\n"
        "🔢 Endi <b>kod</b> yuboring (masalan: <code>101</code>).\n\n"
        "<i>Bekor qilish uchun /bekor</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AddMovie.code)
async def add_code(message: Message, state: FSMContext):
    code = message.text.strip()
    if get_movie_by_code(code):
        await message.answer("⚠️ Bu kod band. Boshqa kod yuboring.")
        return
    await state.update_data(code=code)
    await state.set_state(AddMovie.title)
    await message.answer("📝 <b>Nomini</b> yuboring:", parse_mode="HTML")


@router.message(AddMovie.title)
async def add_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddMovie.aliases)
    await message.answer(
        "🔎 Qidiruv uchun <b>qo'shimcha nomlar</b>ni vergul bilan yuboring.\n"
        "<i>Kerak bo'lmasa «-» yuboring.</i>",
        parse_mode="HTML",
    )


@router.message(AddMovie.aliases)
async def add_aliases(message: Message, state: FSMContext):
    aliases = message.text.strip()
    await state.update_data(aliases="" if aliases == "-" else aliases)
    await state.set_state(AddMovie.part)
    await message.answer(
        "🔁 <b>Qism raqami</b>ni yuboring (oddiy kino bo'lsa <code>1</code>):",
        parse_mode="HTML",
    )


@router.message(AddMovie.part)
async def add_part(message: Message, state: FSMContext):
    try:
        part = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Faqat raqam yuboring (masalan: 1).")
        return
    await state.update_data(part=max(1, part))
    await state.set_state(AddMovie.video)
    await message.answer("🎞 Endi <b>videoni</b> yuboring:", parse_mode="HTML")


@router.message(AddMovie.video, F.video)
async def add_video(message: Message, state: FSMContext):
    data = await state.get_data()
    add_movie(
        code=data["code"],
        title=data["title"],
        aliases=data.get("aliases", ""),
        file_id=message.video.file_id,
        category=data.get("category", "kino"),
        part=data.get("part", 1),
    )
    await state.clear()
    await message.answer(
        f"✅ Saqlandi!\n\n🔢 Kod: <code>{data['code']}</code>\n📝 Nomi: {data['title']}",
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )


@router.message(AddMovie.video)
async def add_video_invalid(message: Message):
    await message.answer("⚠️ Iltimos, <b>video</b> yuboring.", parse_mode="HTML")


# =========================
# RO'YXAT VA BOSHQARUV
# =========================

@router.callback_query(F.data.startswith("list_"))
async def list_movies(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.clear()

    _, category, offset = callback.data.split("_", 2)
    offset = int(offset)
    db_category = None if category == "all" else category

    total = count_movies(category=db_category)
    movies = get_all_movies(offset=offset, limit=PAGE_SIZE, category=db_category)

    if not movies:
        text = "📭 Bu bo'limda hech narsa yo'q."
    else:
        text = f"🔵 <b>Ro'yxat</b> — jami {total} ta\n\nTahrirlash uchun tanlang:"

    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=movie_list_keyboard(movies, offset, total, category),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manage_"))
async def manage_movie(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.clear()

    code = callback.data.removeprefix("manage_")
    movie = get_movie_by_code(code)
    if not movie:
        await callback.answer("Topilmadi", show_alert=True)
        return

    await callback.message.edit_text(
        f"🎬 <b>{movie[2]}</b>\n\n"
        f"🔢 Kod: <code>{movie[1]}</code>\n"
        f"📂 Kategoriya: {CATEGORY_LABEL.get(movie[5], movie[5])}\n"
        f"🔁 Qism: {movie[6] or 1}\n"
        f"👁 Ko'rishlar: {movie[7] or 0}\n"
        f"🔎 Qo'shimcha nomlar: {movie[3] or '—'}",
        parse_mode="HTML",
        reply_markup=movie_actions_keyboard(code),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_title_"))
async def edit_title_start(callback: CallbackQuery, state: FSMContext):
    code = callback.data.removeprefix("edit_title_")
    await state.set_state(EditMovie.title)
    await state.update_data(code=code)
    await callback.message.answer("📝 Yangi <b>nom</b>ni yuboring:", parse_mode="HTML")
    await callback.answer()


@router.message(EditMovie.title)
async def edit_title_save(message: Message, state: FSMContext):
    data = await state.get_data()
    update_movie(data["code"], title=message.text.strip())
    await state.clear()
    await message.answer("✅ Nom yangilandi.", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data.startswith("edit_code_"))
async def edit_code_start(callback: CallbackQuery, state: FSMContext):
    code = callback.data.removeprefix("edit_code_")
    await state.set_state(EditMovie.code)
    await state.update_data(code=code)
    await callback.message.answer("🔢 Yangi <b>kod</b>ni yuboring:", parse_mode="HTML")
    await callback.answer()


@router.message(EditMovie.code)
async def edit_code_save(message: Message, state: FSMContext):
    new_code = message.text.strip()
    if get_movie_by_code(new_code):
        await message.answer("⚠️ Bu kod band. Boshqasini yuboring.")
        return
    data = await state.get_data()
    update_movie(data["code"], code=new_code)
    await state.clear()
    await message.answer("✅ Kod yangilandi.", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data.startswith("edit_part_"))
async def edit_part_start(callback: CallbackQuery, state: FSMContext):
    code = callback.data.removeprefix("edit_part_")
    await state.set_state(EditMovie.part)
    await state.update_data(code=code)
    await callback.message.answer("🔁 Yangi <b>qism raqami</b>ni yuboring:", parse_mode="HTML")
    await callback.answer()


@router.message(EditMovie.part)
async def edit_part_save(message: Message, state: FSMContext):
    try:
        part = max(1, int(message.text.strip()))
    except ValueError:
        await message.answer("⚠️ Faqat raqam yuboring.")
        return
    data = await state.get_data()
    update_movie(data["code"], part=part)
    await state.clear()
    await message.answer("✅ Qism raqami yangilandi.", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data.startswith("edit_video_"))
async def edit_video_start(callback: CallbackQuery, state: FSMContext):
    code = callback.data.removeprefix("edit_video_")
    await state.set_state(EditMovie.video)
    await state.update_data(code=code)
    await callback.message.answer("🎞 Yangi <b>videoni</b> yuboring:", parse_mode="HTML")
    await callback.answer()


@router.message(EditMovie.video, F.video)
async def edit_video_save(message: Message, state: FSMContext):
    data = await state.get_data()
    update_movie(data["code"], file_id=message.video.file_id)
    await state.clear()
    await message.answer("✅ Video almashtirildi.", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data.startswith("edit_category_"))
async def edit_category_start(callback: CallbackQuery):
    code = callback.data.removeprefix("edit_category_")
    await callback.message.edit_text("📂 Yangi kategoriyani tanlang:",
                                     reply_markup=category_edit_keyboard(code))
    await callback.answer()


@router.callback_query(F.data.startswith("setcat_"))
async def set_category(callback: CallbackQuery):
    _, category, code = callback.data.split("_", 2)
    update_movie(code, category=category)
    await callback.answer("✅ Kategoriya yangilandi")
    movie = get_movie_by_code(code)
    if movie:
        await callback.message.edit_text(
            f"🎬 <b>{movie[2]}</b>\n\n"
            f"🔢 Kod: <code>{movie[1]}</code>\n"
            f"📂 Kategoriya: {CATEGORY_LABEL.get(movie[5], movie[5])}\n"
            f"🔁 Qism: {movie[6] or 1}\n"
            f"👁 Ko'rishlar: {movie[7] or 0}",
            parse_mode="HTML",
            reply_markup=movie_actions_keyboard(code),
        )


@router.callback_query(F.data.startswith("delete_"))
async def delete_ask(callback: CallbackQuery):
    code = callback.data.removeprefix("delete_")
    await callback.message.edit_text(
        f"🗑 <code>{code}</code> o'chirilsinmi?", parse_mode="HTML",
        reply_markup=confirm_delete_keyboard(code),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirmdelete_"))
async def delete_confirm(callback: CallbackQuery):
    code = callback.data.removeprefix("confirmdelete_")
    delete_movie(code)
    await callback.message.edit_text("✅ O'chirildi.", reply_markup=admin_menu_keyboard())
    await callback.answer()


# =========================
# STATISTIKA
# =========================

@router.callback_query(F.data == "admin_stats")
async def stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await callback.message.edit_text(
        "🟡 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{count_users()}</b>\n"
        f"🟦 Kinolar: <b>{count_movies('kino')}</b>\n"
        f"🟪 Multfilmlar: <b>{count_movies('multfilm')}</b>\n"
        f"🎬 Jami: <b>{count_movies()}</b>\n"
        f"👁 Jami ko'rishlar: <b>{get_total_views()}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )
    await callback.answer()


# =========================
# XABAR YUBORISH
# =========================

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(Broadcast.message)
    await callback.message.edit_text(
        "🟣 Yubormoqchi bo'lgan xabaringizni yuboring.\n\n<i>Bekor qilish: /bekor</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Broadcast.message)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user_ids = get_all_user_ids()
    sent, failed = 0, 0

    status = await message.answer(f"📤 Yuborilmoqda… (0/{len(user_ids)})")

    for i, uid in enumerate(user_ids, start=1):
        try:
            await message.send_copy(chat_id=uid)
            sent += 1
        except Exception:
            failed += 1
        if i % 25 == 0:
            try:
                await status.edit_text(f"📤 Yuborilmoqda… ({i}/{len(user_ids)})")
            except Exception:
                pass
        await asyncio.sleep(0.05)  # Telegram limitiga urilmaslik uchun

    await status.edit_text(
        f"✅ Yakunlandi.\n\n📨 Yuborildi: <b>{sent}</b>\n⚠️ Yetib bormadi: <b>{failed}</b>",
        parse_mode="HTML",
    )
    await message.answer("⚙️ Admin panel", reply_markup=admin_menu_keyboard())


# =========================
# QO'LLAB-QUVVATLASH MATNI
# =========================

@router.callback_query(F.data == "admin_support")
async def support_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(SupportText.text)
    await callback.message.edit_text(
        "💛 Yangi <b>qo'llab-quvvatlash matni</b>ni yuboring.\n\n<i>Bekor qilish: /bekor</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SupportText.text)
async def support_save(message: Message, state: FSMContext):
    set_setting("support_text", message.html_text or message.text)
    await state.clear()
    await message.answer("✅ Matn saqlandi.", reply_markup=admin_menu_keyboard())


# =========================
# MAJBURIY OBUNA KANALLARI
# =========================

@router.callback_query(F.data == "admin_channel")
async def channels_list(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.clear()
    channels = get_channels()
    text = ("🟠 <b>Majburiy obuna kanallari</b>\n\nHozircha kanal qo'shilmagan."
            if not channels else
            f"🟠 <b>Majburiy obuna kanallari</b>\n\nJami: {len(channels)} ta")
    await callback.message.edit_text(text, parse_mode="HTML",
                                     reply_markup=channels_list_keyboard(channels))
    await callback.answer()


@router.callback_query(F.data == "channel_add")
async def channel_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChannelAdd.channel_id)
    await callback.message.edit_text(
        "📢 Kanal <b>ID</b> yoki <b>@username</b>ini yuboring.\n\n"
        "<i>Muhim: bot o'sha kanalda admin bo'lishi shart!</i>\n"
        "<i>Bekor qilish: /bekor</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ChannelAdd.channel_id)
async def channel_add_id(message: Message, state: FSMContext):
    await state.update_data(channel_id=message.text.strip())
    await state.set_state(ChannelAdd.url)
    await message.answer("🔗 Kanal <b>havolasi</b>ni yuboring:", parse_mode="HTML")


@router.message(ChannelAdd.url)
async def channel_add_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text.strip())
    await state.set_state(ChannelAdd.title)
    await message.answer("🏷 Kanal <b>nomi</b>ni yuboring:", parse_mode="HTML")


@router.message(ChannelAdd.title)
async def channel_add_title(message: Message, state: FSMContext):
    data = await state.get_data()
    add_channel(data["channel_id"], data["url"], message.text.strip())
    await state.clear()
    await message.answer("✅ Kanal qo'shildi.", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data.startswith("chinfo_"))
async def channel_info(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    row_id = int(callback.data.removeprefix("chinfo_"))
    ch = get_channel(row_id)
    if not ch:
        await callback.answer("Topilmadi", show_alert=True)
        return
    await callback.message.edit_text(
        f"📢 <b>{ch[3] or '—'}</b>\n\n🆔 <code>{ch[1]}</code>\n🔗 {ch[2] or '—'}",
        parse_mode="HTML",
        reply_markup=channel_detail_keyboard(row_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("chedit_"))
async def channel_edit_start(callback: CallbackQuery, state: FSMContext):
    row_id = int(callback.data.removeprefix("chedit_"))
    await state.set_state(ChannelEdit.channel_id)
    await state.update_data(row_id=row_id)
    await callback.message.answer(
        "🆔 Yangi kanal <b>ID / @username</b>ini yuboring:", parse_mode="HTML")
    await callback.answer()


@router.message(ChannelEdit.channel_id)
async def channel_edit_id(message: Message, state: FSMContext):
    await state.update_data(channel_id=message.text.strip())
    await state.set_state(ChannelEdit.url)
    await message.answer("🔗 Yangi <b>havola</b>ni yuboring:", parse_mode="HTML")


@router.message(ChannelEdit.url)
async def channel_edit_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text.strip())
    await state.set_state(ChannelEdit.title)
    await message.answer("🏷 Yangi <b>nom</b>ni yuboring:", parse_mode="HTML")


@router.message(ChannelEdit.title)
async def channel_edit_title(message: Message, state: FSMContext):
    data = await state.get_data()
    update_channel(data["row_id"], data["channel_id"], data["url"], message.text.strip())
    await state.clear()
    await message.answer("✅ Kanal yangilandi.", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data.startswith("chdelconfirm_"))
async def channel_delete_confirm(callback: CallbackQuery):
    row_id = int(callback.data.removeprefix("chdelconfirm_"))
    delete_channel(row_id)
    await callback.message.edit_text("✅ Kanal o'chirildi.",
                                     reply_markup=channels_list_keyboard(get_channels()))
    await callback.answer()


@router.callback_query(F.data.startswith("chdel_"))
async def channel_delete_ask(callback: CallbackQuery):
    row_id = int(callback.data.removeprefix("chdel_"))
    await callback.message.edit_text(
        "🗑 Ushbu kanal o'chirilsinmi?",
        reply_markup=channel_delete_confirm_keyboard(row_id),
    )
    await callback.answer()
