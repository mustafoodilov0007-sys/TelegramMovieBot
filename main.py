"""
🎬 KINO BOT — Telegram uchun tayyor kino bot (aiogram 3 + SQLite)

Imkoniyatlar:
  • Kino kodi yoki nomi bo'yicha qidirish
  • https://t.me/BOT?start=356 ko'rinishidagi havola orqali kino yuborish
  • Kinolar / Multfilmlar / Tasodifiy / Top / Qidiruv / Qo'llab-quvvatlash / Reklama berish
  • Majburiy obuna (kanal qo'shish / o'chirish)
  • Admin panel: kino qo'shish, o'chirish, statistika, xabar yuborish, adminlar, matnlar
"""
import asyncio
import html
import logging
import math
import os
import re
from contextlib import suppress
from urllib.parse import quote

import aiosqlite
from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.filters import BaseFilter, CommandObject, CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    KeyboardButton,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from dotenv import load_dotenv

# ============================ SOZLAMALAR ============================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
SUPER_ADMINS = {
    int(x) for x in re.split(r"[,\s]+", os.getenv("ADMINS", "")) if x.strip().isdigit()
}


def _db_path() -> str:
    explicit = os.getenv("DB_PATH", "").strip()
    if explicit:
        return explicit
    volume = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").strip()  # Railway Volume ulangan bo'lsa
    if volume:
        return os.path.join(volume, "kino.db")
    return "kino.db"


DB_PATH = _db_path()
PROTECT_CONTENT = os.getenv("PROTECT_CONTENT", "0") == "1"  # 1 bo'lsa kinoni forward/saqlash mumkin emas
PAGE_SIZE = 10

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("kinobot")

esc = html.escape

# ============================ TUGMALAR ============================
BTN_MOVIES = "🟦 Kinolar"
BTN_CARTOONS = "🟪 Multfilmlar"
BTN_RANDOM = "🎲 Tasodifiy"
BTN_TOP = "🏆 Top"
BTN_SEARCH = "🔍 Qidiruv"
BTN_SUPPORT = "💛 Qo'llab-quvvatlash"
BTN_ADS = "📢 Reklama berish"
BTN_ADMIN = "🛠 Admin panel"

A_ADD = "🎬 Kino qo'shish"
A_DEL = "🗑 Kino o'chirish"
A_STATS = "📊 Statistika"
A_CHANNELS = "🔗 Majburiy kanallar"
A_BROADCAST = "✉️ Xabar yuborish"
A_ADMINS = "👮 Adminlar"
A_TEXTS = "⚙️ Matnlar"
A_BACK = "◀️ Foydalanuvchi menyusi"
BTN_CANCEL = "❌ Bekor qilish"

CAT_NAMES = {"kino": "🟦 Kino", "multfilm": "🟪 Multfilm"}

DEFAULT_TEXTS = {
    "welcome": (
        "👋 Assalomu alaykum, {name}!\n\n"
        "🎬 Kino <b>kodini</b> yoki <b>nomini</b> yuboring — men darhol topib beraman.\n\n"
        "👇 Yoki quyidagi menyudan foydalaning."
    ),
    "support": "💛 Qo'llab-quvvatlash uchun admin bilan bog'laning:\n\n@admin",
    "ads": "📢 Reklama berish uchun admin bilan bog'laning:\n\n@admin",
}
TEXT_TITLES = {
    "welcome": "👋 Salomlashish matni",
    "support": "💛 Qo'llab-quvvatlash matni",
    "ads": "📢 Reklama matni",
}

LINK_RE = re.compile(r"t\.me/[A-Za-z0-9_]+\?start=(\d{1,9})")

# ============================ BAZA ============================
conn: aiosqlite.Connection


async def init_db() -> None:
    global conn
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            joined_at TEXT DEFAULT (datetime('now')),
            last_active TEXT DEFAULT (datetime('now')),
            active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS movies(
            code INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            search TEXT NOT NULL,
            category TEXT NOT NULL,
            file_id TEXT NOT NULL,
            file_type TEXT NOT NULL,
            views INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS channels(
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            link TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
        """
    )
    await conn.commit()


async def q_one(sql: str, args=()):
    async with conn.execute(sql, args) as cur:
        return await cur.fetchone()


async def q_all(sql: str, args=()):
    async with conn.execute(sql, args) as cur:
        return await cur.fetchall()


async def q_exec(sql: str, args=()):
    cur = await conn.execute(sql, args)
    await conn.commit()
    return cur


async def get_text(key: str) -> str:
    row = await q_one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else DEFAULT_TEXTS[key]


async def set_text(key: str, value: str) -> None:
    await q_exec("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (key, value))


async def is_admin(user_id: int) -> bool:
    if user_id in SUPER_ADMINS:
        return True
    return await q_one("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) is not None


def normalize(text: str) -> str:
    """Qidiruv uchun: kichik harf va o'zbekcha apostrof belgilarini bir xil qilish."""
    for ch in ("‘", "’", "ʻ", "ʼ", "`", "´"):
        text = text.replace(ch, "'")
    return text.lower().strip()


async def make_backup(path: str) -> None:
    """Bazaning to'liq va xavfsiz nusxasini `path` ga yozadi."""
    await conn.commit()
    if os.path.exists(path):
        os.remove(path)
    await conn.execute("VACUUM INTO ?", (path,))


RESTORE_SPEC = {
    "movies": ["code", "title", "search", "category", "file_id", "file_type", "views", "created_at"],
    "users": ["user_id", "full_name", "username", "joined_at", "last_active", "active"],
    "channels": ["chat_id", "title", "link"],
    "admins": ["user_id"],
    "settings": ["key", "value"],
}


async def merge_database(path: str) -> str:
    """Backup faylidagi ma'lumotlarni joriy bazaga qo'shadi (kodi bir xil kino ustiga yoziladi)."""
    await conn.commit()
    await conn.execute("ATTACH DATABASE ? AS old", (path,))
    try:
        tables = {r["name"] for r in await q_all("SELECT name FROM old.sqlite_master WHERE type='table'")}
        if "movies" not in tables:
            raise ValueError("Bu fayl kino bot bazasi emas (movies jadvali yo'q)")
        report = []
        for table, cols in RESTORE_SPEC.items():
            if table not in tables:
                continue
            old_cols = {r["name"] for r in await q_all(f"PRAGMA old.table_info({table})")}
            if not set(cols) <= old_cols:
                raise ValueError(f"«{table}» jadvali formati mos emas")
            col_list = ", ".join(cols)
            await conn.execute(f"INSERT OR REPLACE INTO main.{table}({col_list}) SELECT {col_list} FROM old.{table}")
            n = (await q_one(f"SELECT COUNT(*) c FROM old.{table}"))["c"]
            report.append((table, n))
        await conn.commit()
    finally:
        await conn.commit()
        await conn.execute("DETACH DATABASE old")
    names = {"movies": "🎬 Kinolar", "users": "👥 Foydalanuvchilar", "channels": "🔗 Kanallar",
             "admins": "👮 Adminlar", "settings": "⚙️ Matnlar"}
    return "\n".join(f"{names[t]}: <b>{n}</b>" for t, n in report)


# ============================ KLAVIATURALAR ============================
def user_menu(admin: bool = False):
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text=BTN_MOVIES), KeyboardButton(text=BTN_CARTOONS))
    b.row(KeyboardButton(text=BTN_RANDOM), KeyboardButton(text=BTN_TOP))
    b.row(KeyboardButton(text=BTN_SEARCH))
    b.row(KeyboardButton(text=BTN_SUPPORT), KeyboardButton(text=BTN_ADS))
    if admin:
        b.row(KeyboardButton(text=BTN_ADMIN))
    return b.as_markup(resize_keyboard=True, input_field_placeholder="Kino kodi yoki nomini yozing…")


def admin_menu():
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text=A_ADD), KeyboardButton(text=A_DEL))
    b.row(KeyboardButton(text=A_STATS), KeyboardButton(text=A_CHANNELS))
    b.row(KeyboardButton(text=A_BROADCAST), KeyboardButton(text=A_ADMINS))
    b.row(KeyboardButton(text=A_TEXTS))
    b.row(KeyboardButton(text=A_BACK))
    return b.as_markup(resize_keyboard=True)


def cancel_kb():
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text=BTN_CANCEL))
    return b.as_markup(resize_keyboard=True)


def sub_kb(channels, payload: str = "0"):
    b = InlineKeyboardBuilder()
    for i, ch in enumerate(channels, 1):
        b.row(InlineKeyboardButton(text=f"📢 {i}. {ch['title']}", url=ch["link"]))
    b.row(InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data=f"check:{payload}"))
    return b.as_markup()


# ============================ YORDAMCHI FUNKSIYALAR ============================
async def send_movie(bot: Bot, chat_id: int, code: int) -> bool:
    m = await q_one("SELECT * FROM movies WHERE code=?", (code,))
    if not m:
        return False
    me = await bot.me()
    link = f"https://t.me/{me.username}?start={m['code']}"
    caption = (
        f"🎬 <b>{esc(m['title'])}</b>\n\n"
        f"📂 Bo'lim: {CAT_NAMES.get(m['category'], m['category'])}\n"
        f"🔢 Kod: <code>{m['code']}</code>\n"
        f"👁 Ko'rishlar: {m['views'] + 1}\n\n"
        f"🤖 @{me.username}"
    )
    share = f"https://t.me/share/url?url={quote(link)}&text={quote('🎬 ' + m['title'])}"
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📤 Do'stlarga ulashish", url=share))
    kwargs = dict(caption=caption, reply_markup=kb.as_markup(), protect_content=PROTECT_CONTENT)
    if m["file_type"] == "video":
        await bot.send_video(chat_id, m["file_id"], **kwargs)
    else:
        await bot.send_document(chat_id, m["file_id"], **kwargs)
    await q_exec("UPDATE movies SET views = views + 1 WHERE code=?", (code,))
    return True


async def get_unsubscribed(bot: Bot, user_id: int):
    """Foydalanuvchi obuna bo'lmagan kanallar ro'yxatini qaytaradi."""
    missing = []
    for ch in await q_all("SELECT * FROM channels"):
        try:
            member = await bot.get_chat_member(ch["chat_id"], user_id)
            if member.status in ("left", "kicked"):
                missing.append(ch)
            elif member.status == "restricted" and not getattr(member, "is_member", True):
                missing.append(ch)
        except TelegramAPIError as e:
            # Bot kanalda admin emas yoki kanal o'chirilgan — foydalanuvchini bloklamaymiz
            log.warning("Kanalni tekshirib bo'lmadi (%s): %s", ch["chat_id"], e)
    return missing


async def catalog_page(cat: str, page: int):
    total = (await q_one("SELECT COUNT(*) c FROM movies WHERE category=?", (cat,)))["c"]
    if total == 0:
        return None
    pages = math.ceil(total / PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    rows = await q_all(
        "SELECT code, title FROM movies WHERE category=? ORDER BY code DESC LIMIT ? OFFSET ?",
        (cat, PAGE_SIZE, page * PAGE_SIZE),
    )
    b = InlineKeyboardBuilder()
    for r in rows:
        b.row(InlineKeyboardButton(text=f"🎬 {r['title']}  •  {r['code']}", callback_data=f"mv:{r['code']}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"list:{cat}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="noop"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"list:{cat}:{page + 1}"))
    b.row(*nav)
    text = f"{CAT_NAMES[cat]} — jami <b>{total}</b> ta\n\nKerakli kinoni tanlang yoki kodini yuboring 👇"
    return text, b.as_markup()


async def search_movies(query: str):
    words = normalize(query).split()[:5]
    if not words:
        return []
    cond = " AND ".join(["search LIKE ? ESCAPE '\\'"] * len(words))
    args = ["%" + w.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%" for w in words]
    return await q_all(
        f"SELECT code, title, category FROM movies WHERE {cond} ORDER BY views DESC LIMIT 15", args
    )


def results_kb(rows):
    b = InlineKeyboardBuilder()
    for r in rows:
        b.row(InlineKeyboardButton(text=f"🎬 {r['title']}  •  {r['code']}", callback_data=f"mv:{r['code']}"))
    return b.as_markup()


# ============================ MIDDLEWARE ============================
class TrackMiddleware(BaseMiddleware):
    """Har bir foydalanuvchini bazaga yozib boradi."""

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user and not user.is_bot:
            await q_exec(
                """INSERT INTO users(user_id, full_name, username) VALUES(?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET
                     full_name=excluded.full_name, username=excluded.username,
                     last_active=datetime('now'), active=1""",
                (user.id, user.full_name, user.username),
            )
        return await handler(event, data)


class SubscriptionMiddleware(BaseMiddleware):
    """Majburiy obunani tekshiradi (adminlarga tegmaydi)."""

    async def __call__(self, handler, event, data):
        user = event.from_user
        bot: Bot = data["bot"]
        if await is_admin(user.id):
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and (event.data or "").startswith("check:"):
            return await handler(event, data)

        missing = await get_unsubscribed(bot, user.id)
        if not missing:
            return await handler(event, data)

        payload = "0"
        if isinstance(event, Message) and event.text and event.text.startswith("/start "):
            arg = event.text.split(maxsplit=1)[1].strip()
            if arg.isdigit():
                payload = arg
        elif isinstance(event, Message) and event.text:
            m = LINK_RE.search(event.text)
            if m:
                payload = m.group(1)

        await bot.send_message(
            user.id,
            "❗️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling, so'ng "
            "<b>«Obunani tekshirish»</b> tugmasini bosing:",
            reply_markup=sub_kb(missing, payload),
        )
        if isinstance(event, CallbackQuery):
            await event.answer()


# ============================ ROUTERLAR ============================
class IsAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        return await is_admin(event.from_user.id)


admin_router = Router(name="admin")
admin_router.message.filter(IsAdmin(), F.chat.type == "private")
admin_router.callback_query.filter(IsAdmin())

user_router = Router(name="user")
user_router.message.filter(F.chat.type == "private")
user_router.message.middleware(SubscriptionMiddleware())
user_router.callback_query.middleware(SubscriptionMiddleware())


# ============================ FOYDALANUVCHI ============================
@user_router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot: Bot):
    admin = await is_admin(message.from_user.id)
    code = (command.args or "").strip()
    if code.isdigit() and len(code) < 10:
        if await send_movie(bot, message.chat.id, int(code)):
            await message.answer("🎬 Boshqa kinolar uchun menyudan foydalaning 👇", reply_markup=user_menu(admin))
        else:
            await message.answer("❌ Bunday kodli kino topilmadi.", reply_markup=user_menu(admin))
        return
    text = (await get_text("welcome")).replace("{name}", esc(message.from_user.full_name))
    await message.answer(text, reply_markup=user_menu(admin))


@user_router.callback_query(F.data.startswith("check:"))
async def cb_check(call: CallbackQuery, bot: Bot):
    payload = call.data.split(":", 1)[1]
    missing = await get_unsubscribed(bot, call.from_user.id)
    if missing:
        await call.answer("❌ Hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)
        with suppress(TelegramBadRequest):
            await call.message.edit_reply_markup(reply_markup=sub_kb(missing, payload))
        return
    await call.answer("✅ Rahmat! Obuna tasdiqlandi.")
    with suppress(TelegramBadRequest):
        await call.message.delete()
    admin = await is_admin(call.from_user.id)
    if payload.isdigit() and payload != "0":
        if await send_movie(bot, call.from_user.id, int(payload)):
            await bot.send_message(call.from_user.id, "🎬 Boshqa kinolar uchun menyudan foydalaning 👇",
                                   reply_markup=user_menu(admin))
            return
        await bot.send_message(call.from_user.id, "❌ Bunday kodli kino topilmadi.")
    text = (await get_text("welcome")).replace("{name}", esc(call.from_user.full_name))
    await bot.send_message(call.from_user.id, text, reply_markup=user_menu(admin))


async def show_catalog(message: Message, cat: str):
    res = await catalog_page(cat, 0)
    if not res:
        await message.answer("😔 Hozircha bu bo'limda kontent yo'q.")
        return
    await message.answer(res[0], reply_markup=res[1])


@user_router.message(F.text == BTN_MOVIES)
async def btn_movies(message: Message):
    await show_catalog(message, "kino")


@user_router.message(F.text == BTN_CARTOONS)
async def btn_cartoons(message: Message):
    await show_catalog(message, "multfilm")


@user_router.callback_query(F.data.startswith("list:"))
async def cb_list(call: CallbackQuery):
    _, cat, page = call.data.split(":")
    if cat in CAT_NAMES and page.isdigit():
        res = await catalog_page(cat, int(page))
        if res:
            with suppress(TelegramBadRequest):
                await call.message.edit_text(res[0], reply_markup=res[1])
    await call.answer()


@user_router.callback_query(F.data.startswith("mv:"))
async def cb_movie(call: CallbackQuery, bot: Bot):
    code = call.data.split(":")[1]
    if not code.isdigit() or not await send_movie(bot, call.from_user.id, int(code)):
        await call.answer("❌ Kino topilmadi", show_alert=True)
        return
    await call.answer()


@user_router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()


@user_router.message(F.text == BTN_RANDOM)
async def btn_random(message: Message, bot: Bot):
    row = await q_one("SELECT code FROM movies ORDER BY RANDOM() LIMIT 1")
    if not row:
        await message.answer("😔 Hozircha kinolar yo'q.")
        return
    await send_movie(bot, message.chat.id, row["code"])


@user_router.message(F.text == BTN_TOP)
async def btn_top(message: Message):
    rows = await q_all("SELECT code, title, views FROM movies ORDER BY views DESC, code DESC LIMIT 10")
    if not rows:
        await message.answer("😔 Hozircha kinolar yo'q.")
        return
    medals = ["🥇", "🥈", "🥉"] + ["🔥"] * 7
    b = InlineKeyboardBuilder()
    for i, r in enumerate(rows):
        b.row(InlineKeyboardButton(text=f"{medals[i]} {r['title']} — 👁 {r['views']}", callback_data=f"mv:{r['code']}"))
    await message.answer("🏆 <b>Eng ko'p ko'rilgan kinolar</b>\n\nTanlang 👇", reply_markup=b.as_markup())


@user_router.message(F.text == BTN_SEARCH)
async def btn_search(message: Message):
    await message.answer(
        "🔍 <b>Qidiruv</b>\n\nKino <b>kodini</b> yoki <b>nomini</b> yozib yuboring.\n"
        "Masalan: <code>356</code> yoki <code>Titanik</code>"
    )


@user_router.message(F.text == BTN_SUPPORT)
async def btn_support(message: Message):
    await message.answer(await get_text("support"))


@user_router.message(F.text == BTN_ADS)
async def btn_ads(message: Message):
    await message.answer(await get_text("ads"))


@user_router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, bot: Bot):
    """Kod, havola yoki nom bo'yicha qidirish."""
    text = message.text.strip()
    code = None
    m = LINK_RE.search(text)
    if m:
        code = int(m.group(1))
    elif text.isdigit() and len(text) < 10:
        code = int(text)

    if code is not None:
        if not await send_movie(bot, message.chat.id, code):
            await message.answer("❌ Bunday kodli kino topilmadi.")
        return

    rows = await search_movies(text)
    if not rows:
        await message.answer(f"😔 «{esc(text[:50])}» bo'yicha hech narsa topilmadi.\nBoshqa nom yoki kod bilan urinib ko'ring.")
        return
    await message.answer(f"🔍 <b>Topilgan natijalar</b> ({len(rows)} ta) 👇", reply_markup=results_kb(rows))


# ============================ ADMIN: HOLATLAR ============================
class AddMovie(StatesGroup):
    video = State()
    title = State()
    category = State()


class DelMovie(StatesGroup):
    code = State()


class AddChannel(StatesGroup):
    wait = State()


class Broadcast(StatesGroup):
    msg = State()
    confirm = State()


class AddAdmin(StatesGroup):
    wait = State()


class EditText(StatesGroup):
    value = State()


class Restore(StatesGroup):
    file = State()


# ============================ ADMIN: MENYU TUGMALARI ============================
@admin_router.message(StateFilter("*"), F.text == BTN_CANCEL)
async def a_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())


@admin_router.message(Command("admin"))
@admin_router.message(F.text == BTN_ADMIN)
async def a_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🛠 <b>Admin panel</b>\n\nKerakli bo'limni tanlang:", reply_markup=admin_menu())


@admin_router.message(F.text == A_BACK)
async def a_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👤 Foydalanuvchi menyusi", reply_markup=user_menu(True))


# ---------- Backup / Restore ----------
@admin_router.message(Command("backup"))
async def a_backup(message: Message):
    tmp = f"{DB_PATH}.backup"
    await make_backup(tmp)
    try:
        await message.answer_document(
            FSInputFile(tmp, filename="kino_backup.db"),
            caption="💾 Baza nusxasi.\nTiklash uchun: /restore → shu faylni yuboring.",
        )
    finally:
        with suppress(OSError):
            os.remove(tmp)


@admin_router.message(Command("restore"))
async def a_restore(message: Message, state: FSMContext):
    if message.from_user.id not in SUPER_ADMINS:
        await message.answer("⛔️ Tiklashni faqat asosiy admin bajara oladi.")
        return
    await state.clear()
    await state.set_state(Restore.file)
    await message.answer(
        "📥 <b>Bazani tiklash</b>\n\n"
        "Avval olingan backup <code>.db</code> faylini yuboring.\n"
        "⚠️ Kodi bir xil bo'lgan kinolar fayldagisi bilan almashtiriladi.",
        reply_markup=cancel_kb(),
    )


@admin_router.message(Restore.file, F.document)
async def a_restore_file(message: Message, state: FSMContext, bot: Bot):
    doc = message.document
    if doc.file_size and doc.file_size > 19 * 1024 * 1024:
        await message.answer("❌ Fayl 20 MB dan katta — Telegram bot uni yuklab ololmaydi.")
        return
    tmp = f"{DB_PATH}.restore"
    try:
        await bot.download(doc, destination=tmp)
        report = await merge_database(tmp)
    except Exception as e:  # noqa: BLE001
        log.exception("Restore xatosi")
        await message.answer(f"❌ Tiklab bo'lmadi: {esc(str(e))[:300]}")
        return
    finally:
        with suppress(OSError):
            os.remove(tmp)
    await state.clear()
    await message.answer(f"✅ <b>Baza tiklandi</b>\n\n{report}", reply_markup=admin_menu())


@admin_router.message(Restore.file)
async def a_restore_wrong(message: Message):
    await message.answer("⚠️ Iltimos, <code>.db</code> faylni hujjat sifatida yuboring.")


# ---------- Kino qo'shish ----------
@admin_router.message(Command("add"))
@admin_router.message(F.text == A_ADD)
async def a_add(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddMovie.video)
    await message.answer("🎬 Kinoni <b>video</b> yoki <b>fayl</b> qilib yuboring:", reply_markup=cancel_kb())


@admin_router.message(AddMovie.video, F.video | F.document)
async def a_add_video(message: Message, state: FSMContext):
    if message.video:
        file_id, ftype = message.video.file_id, "video"
        default_title = message.caption or ""
    else:
        file_id, ftype = message.document.file_id, "document"
        default_title = message.caption or (message.document.file_name or "")
    await state.update_data(file_id=file_id, file_type=ftype)
    hint = f"\n\nTaklif: <code>{esc(default_title[:100])}</code>" if default_title else ""
    await state.set_state(AddMovie.title)
    await message.answer(f"✏️ Kino <b>nomini</b> yozing:{hint}")


@admin_router.message(AddMovie.video)
async def a_add_video_wrong(message: Message):
    await message.answer("⚠️ Iltimos, video yoki fayl yuboring.")


@admin_router.message(AddMovie.title, F.text)
async def a_add_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip()[:200])
    await state.set_state(AddMovie.category)
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text=CAT_NAMES["kino"], callback_data="cat:kino"),
        InlineKeyboardButton(text=CAT_NAMES["multfilm"], callback_data="cat:multfilm"),
    )
    await message.answer("📂 Qaysi bo'limga qo'shamiz?", reply_markup=b.as_markup())


@admin_router.callback_query(AddMovie.category, F.data.startswith("cat:"))
async def a_add_category(call: CallbackQuery, state: FSMContext, bot: Bot):
    cat = call.data.split(":")[1]
    if cat not in CAT_NAMES:
        await call.answer()
        return
    data = await state.get_data()
    cur = await q_exec(
        "INSERT INTO movies(title, search, category, file_id, file_type) VALUES(?,?,?,?,?)",
        (data["title"], normalize(data["title"]), cat, data["file_id"], data["file_type"]),
    )
    code = cur.lastrowid
    await state.clear()
    me = await bot.me()
    await call.answer("✅ Qo'shildi")
    with suppress(TelegramBadRequest):
        await call.message.delete()
    await bot.send_message(
        call.from_user.id,
        f"✅ <b>Kino qo'shildi!</b>\n\n"
        f"🎬 Nomi: {esc(data['title'])}\n"
        f"📂 Bo'lim: {CAT_NAMES[cat]}\n"
        f"🔢 Kod: <code>{code}</code>\n"
        f"🔗 Havola: https://t.me/{me.username}?start={code}",
        reply_markup=admin_menu(),
    )


# ---------- Kino o'chirish ----------
@admin_router.message(Command("del"))
@admin_router.message(F.text == A_DEL)
async def a_del(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(DelMovie.code)
    await message.answer("🗑 O'chiriladigan kino <b>kodini</b> yuboring:", reply_markup=cancel_kb())


@admin_router.message(DelMovie.code, F.text)
async def a_del_code(message: Message, state: FSMContext):
    t = message.text.strip()
    m = LINK_RE.search(t)
    code = m.group(1) if m else t
    if not code.isdigit() or len(code) > 9:
        await message.answer("⚠️ Kod faqat raqamlardan iborat bo'lishi kerak.")
        return
    movie = await q_one("SELECT code, title FROM movies WHERE code=?", (int(code),))
    if not movie:
        await message.answer("❌ Bunday kodli kino topilmadi. Qayta yuboring yoki bekor qiling.")
        return
    await state.clear()
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"delmv:{movie['code']}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_inline"),
    )
    await message.answer(
        f"❓ <b>{esc(movie['title'])}</b> (kod: {movie['code']}) o'chirilsinmi?",
        reply_markup=b.as_markup(),
    )
    await message.answer("👇", reply_markup=admin_menu())


@admin_router.callback_query(F.data.startswith("delmv:"))
async def a_del_confirm(call: CallbackQuery):
    code = int(call.data.split(":")[1])
    await q_exec("DELETE FROM movies WHERE code=?", (code,))
    await call.answer("🗑 O'chirildi")
    with suppress(TelegramBadRequest):
        await call.message.edit_text(f"🗑 Kino (kod: {code}) o'chirildi.")


@admin_router.callback_query(F.data == "cancel_inline")
async def a_cancel_inline(call: CallbackQuery):
    await call.answer("Bekor qilindi")
    with suppress(TelegramBadRequest):
        await call.message.delete()


# ---------- Statistika ----------
@admin_router.message(Command("stats"))
@admin_router.message(F.text == A_STATS)
async def a_stats(message: Message):
    u = await q_one(
        """SELECT COUNT(*) total,
                  SUM(date(joined_at) = date('now')) new_today,
                  SUM(date(last_active) = date('now')) act_today,
                  SUM(active = 0) blocked
           FROM users"""
    )
    mv = await q_one(
        """SELECT COUNT(*) total,
                  SUM(category='kino') kino,
                  SUM(category='multfilm') mult,
                  SUM(views) views
           FROM movies"""
    )
    ch = (await q_one("SELECT COUNT(*) c FROM channels"))["c"]
    await message.answer(
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami obunachilar: <b>{u['total']}</b>\n"
        f"🆕 Bugun qo'shilgan: <b>{u['new_today'] or 0}</b>\n"
        f"⚡️ Bugun faol: <b>{u['act_today'] or 0}</b>\n"
        f"🚫 Botni bloklaganlar: <b>{u['blocked'] or 0}</b>\n\n"
        f"🎬 Jami kontent: <b>{mv['total']}</b>\n"
        f"   🟦 Kinolar: {mv['kino'] or 0}\n"
        f"   🟪 Multfilmlar: {mv['mult'] or 0}\n"
        f"👁 Jami ko'rishlar: <b>{mv['views'] or 0}</b>\n\n"
        f"🔗 Majburiy kanallar: <b>{ch}</b>"
    )


# ---------- Majburiy kanallar ----------
async def render_channels():
    rows = await q_all("SELECT * FROM channels")
    text = "🔗 <b>Majburiy obuna kanallari</b>\n\n"
    if rows:
        text += "\n".join(f"{i}. {esc(r['title'])} — {r['link']}" for i, r in enumerate(rows, 1))
        text += "\n\nO'chirish uchun kanal nomini bosing 👇"
    else:
        text += "Hozircha kanal yo'q — obuna talab qilinmaydi."
    b = InlineKeyboardBuilder()
    for r in rows:
        b.row(InlineKeyboardButton(text=f"🗑 {r['title']}", callback_data=f"delch:{r['chat_id']}"))
    b.row(InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="addch"))
    return text, b.as_markup()


@admin_router.message(Command("channels"))
@admin_router.message(F.text == A_CHANNELS)
async def a_channels(message: Message, state: FSMContext):
    await state.clear()
    text, kb = await render_channels()
    await message.answer(text, reply_markup=kb)


@admin_router.callback_query(F.data == "addch")
async def a_addch(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddChannel.wait)
    await call.answer()
    await call.message.answer(
        "➕ <b>Kanal qo'shish</b>\n\n"
        "1️⃣ Avval botni kanalga <b>admin</b> qiling.\n"
        "2️⃣ Keyin quyidagilardan birini yuboring:\n"
        "   • kanaldan istalgan xabarni <b>forward</b> qiling (shaxsiy kanal uchun ham),\n"
        "   • yoki kanal <code>@username</code> / havolasini yuboring.",
        reply_markup=cancel_kb(),
    )


@admin_router.message(AddChannel.wait)
async def a_addch_process(message: Message, state: FSMContext, bot: Bot):
    ref = None
    origin = message.forward_origin
    if origin is not None and getattr(origin, "type", None) == "channel":
        ref = origin.chat.id
    elif message.text:
        t = message.text.strip()
        m = re.match(r"^(?:https?://)?t\.me/([A-Za-z0-9_]{4,})/?$", t)
        if m:
            ref = "@" + m.group(1)
        elif re.fullmatch(r"-?\d{6,}", t):
            ref = int(t)
        elif re.fullmatch(r"@?[A-Za-z0-9_]{4,}", t):
            ref = "@" + t.lstrip("@")
    if ref is None:
        await message.answer("⚠️ Tushunmadim. Kanaldan xabar forward qiling yoki @username yuboring.")
        return

    try:
        chat = await bot.get_chat(ref)
        me_member = await bot.get_chat_member(chat.id, bot.id)
    except TelegramAPIError:
        await message.answer("❌ Kanal topilmadi yoki bot kanalda yo'q. Botni kanalga admin qilib, qayta urinib ko'ring.")
        return
    if me_member.status not in ("administrator", "creator"):
        await message.answer("❌ Bot bu kanalda <b>admin emas</b>. Avval botni admin qiling, so'ng qayta yuboring.")
        return

    link = f"https://t.me/{chat.username}" if chat.username else None
    if not link:
        try:
            link = (await bot.create_chat_invite_link(chat.id)).invite_link
        except TelegramAPIError:
            link = getattr(chat, "invite_link", None)
    if not link:
        await message.answer("❌ Havola olib bo'lmadi. Botga «Foydalanuvchilarni taklif qilish» huquqini bering.")
        return

    await q_exec(
        "INSERT OR REPLACE INTO channels(chat_id, title, link) VALUES(?,?,?)",
        (chat.id, chat.title or str(chat.id), link),
    )
    await state.clear()
    await message.answer(f"✅ <b>{esc(chat.title or '')}</b> majburiy kanallarga qo'shildi.", reply_markup=admin_menu())
    text, kb = await render_channels()
    await message.answer(text, reply_markup=kb)


@admin_router.callback_query(F.data.startswith("delch:"))
async def a_delch(call: CallbackQuery):
    await q_exec("DELETE FROM channels WHERE chat_id=?", (int(call.data.split(":")[1]),))
    await call.answer("🗑 Kanal o'chirildi")
    text, kb = await render_channels()
    with suppress(TelegramBadRequest):
        await call.message.edit_text(text, reply_markup=kb)


# ---------- Xabar yuborish ----------
@admin_router.message(Command("broadcast"))
@admin_router.message(F.text == A_BROADCAST)
async def a_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Broadcast.msg)
    await message.answer(
        "✉️ <b>Obunachilarga xabar yuborish</b>\n\n"
        "Yubormoqchi bo'lgan xabaringizni jo'nating (matn, rasm, video, tugmali post — istalgan).",
        reply_markup=cancel_kb(),
    )


@admin_router.message(Broadcast.msg)
async def a_broadcast_msg(message: Message, state: FSMContext):
    total = (await q_one("SELECT COUNT(*) c FROM users WHERE active=1"))["c"]
    await state.update_data(chat_id=message.chat.id, msg_id=message.message_id)
    await state.set_state(Broadcast.confirm)
    await message.answer("👆 Xabar shunday ko'rinadi.")
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text=f"✅ Yuborish ({total} ta)", callback_data="bc:yes"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="bc:no"),
    )
    await message.answer("Tasdiqlaysizmi?", reply_markup=b.as_markup())


background_tasks: set = set()


async def run_broadcast(bot: Bot, admin_chat: int, src_chat: int, msg_id: int):
    rows = await q_all("SELECT user_id FROM users WHERE active=1")
    ok = fail = 0
    for r in rows:
        uid = r["user_id"]
        for attempt in range(3):
            try:
                await bot.copy_message(uid, src_chat, msg_id)
                ok += 1
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
                continue
            except TelegramForbiddenError:
                fail += 1
                await q_exec("UPDATE users SET active=0 WHERE user_id=?", (uid,))
            except TelegramAPIError:
                fail += 1
            break
        await asyncio.sleep(0.05)  # ~20 ta/soniya — Telegram limitidan pastroq
    await bot.send_message(
        admin_chat,
        f"✅ <b>Xabar yuborish tugadi</b>\n\n📬 Yetkazildi: <b>{ok}</b>\n🚫 Yetkazilmadi: <b>{fail}</b>",
        reply_markup=admin_menu(),
    )


@admin_router.callback_query(Broadcast.confirm, F.data.in_({"bc:yes", "bc:no"}))
async def a_broadcast_confirm(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    with suppress(TelegramBadRequest):
        await call.message.delete()
    if call.data == "bc:no":
        await call.answer("Bekor qilindi")
        await bot.send_message(call.from_user.id, "❌ Xabar yuborish bekor qilindi.", reply_markup=admin_menu())
        return
    await call.answer("Yuborish boshlandi")
    await bot.send_message(call.from_user.id, "🚀 Xabar yuborish boshlandi. Tugagach xabar beraman.")
    task = asyncio.create_task(run_broadcast(bot, call.from_user.id, data["chat_id"], data["msg_id"]))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


# ---------- Adminlar ----------
async def render_admins():
    rows = await q_all("SELECT user_id FROM admins")
    text = "👮 <b>Adminlar</b>\n\n"
    text += "Asosiy adminlar: " + (", ".join(f"<code>{i}</code>" for i in SUPER_ADMINS) or "—") + "\n\n"
    text += "Qo'shilgan adminlar:\n" + ("\n".join(f"• <code>{r['user_id']}</code>" for r in rows) if rows else "—")
    b = InlineKeyboardBuilder()
    for r in rows:
        b.row(InlineKeyboardButton(text=f"🗑 {r['user_id']}", callback_data=f"deladm:{r['user_id']}"))
    b.row(InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="addadm"))
    return text, b.as_markup()


@admin_router.message(F.text == A_ADMINS)
async def a_admins(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in SUPER_ADMINS:
        await message.answer("⛔️ Adminlarni faqat asosiy admin boshqara oladi.")
        return
    text, kb = await render_admins()
    await message.answer(text, reply_markup=kb)


@admin_router.callback_query(F.data == "addadm")
async def a_addadm(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in SUPER_ADMINS:
        await call.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AddAdmin.wait)
    await call.answer()
    await call.message.answer("👮 Yangi adminning <b>Telegram ID</b> raqamini yuboring:", reply_markup=cancel_kb())


@admin_router.message(AddAdmin.wait, F.text)
async def a_addadm_process(message: Message, state: FSMContext):
    t = message.text.strip()
    if not t.isdigit():
        await message.answer("⚠️ ID faqat raqamlardan iborat bo'lishi kerak.")
        return
    await q_exec("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (int(t),))
    await state.clear()
    await message.answer(f"✅ <code>{t}</code> admin qilib qo'shildi.", reply_markup=admin_menu())
    text, kb = await render_admins()
    await message.answer(text, reply_markup=kb)


@admin_router.callback_query(F.data.startswith("deladm:"))
async def a_deladm(call: CallbackQuery):
    if call.from_user.id not in SUPER_ADMINS:
        await call.answer("⛔️ Ruxsat yo'q", show_alert=True)
        return
    await q_exec("DELETE FROM admins WHERE user_id=?", (int(call.data.split(":")[1]),))
    await call.answer("🗑 O'chirildi")
    text, kb = await render_admins()
    with suppress(TelegramBadRequest):
        await call.message.edit_text(text, reply_markup=kb)


# ---------- Matnlarni o'zgartirish ----------
@admin_router.message(F.text == A_TEXTS)
async def a_texts(message: Message, state: FSMContext):
    await state.clear()
    b = InlineKeyboardBuilder()
    for key, title in TEXT_TITLES.items():
        b.row(InlineKeyboardButton(text=title, callback_data=f"et:{key}"))
    await message.answer("⚙️ Qaysi matnni o'zgartiramiz?", reply_markup=b.as_markup())


@admin_router.callback_query(F.data.startswith("et:"))
async def a_text_choose(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[1]
    if key not in TEXT_TITLES:
        await call.answer()
        return
    await state.set_state(EditText.value)
    await state.update_data(key=key)
    await call.answer()
    extra = "\n\n<i>{name} — foydalanuvchi ismi o'rniga qo'yiladi.</i>" if key == "welcome" else ""
    await call.message.answer(
        f"{TEXT_TITLES[key]}\n\nHozirgi matn:\n\n{await get_text(key)}\n\n"
        f"✏️ Yangi matnni yuboring (HTML formatlash ishlaydi).{extra}",
        reply_markup=cancel_kb(),
    )


@admin_router.message(EditText.value, F.text)
async def a_text_save(message: Message, state: FSMContext):
    key = (await state.get_data())["key"]
    await set_text(key, message.html_text)
    await state.clear()
    await message.answer("✅ Matn saqlandi.", reply_markup=admin_menu())


# ============================ ISHGA TUSHIRISH ============================
async def main():
    if not BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN topilmadi. .env faylini tekshiring.")
    if not SUPER_ADMINS:
        log.warning("ADMINS bo'sh! .env ga o'zingizning Telegram ID'ingizni yozing.")

    await init_db()
    log.info("Baza fayli: %s", os.path.abspath(DB_PATH))
    on_railway = os.getenv("RAILWAY_ENVIRONMENT_NAME") or os.getenv("RAILWAY_ENVIRONMENT")
    if on_railway and not os.getenv("RAILWAY_VOLUME_MOUNT_PATH") and not os.getenv("DB_PATH"):
        log.warning("⚠️ Railway'da Volume ulanmagan! Baza har deployda o'chib ketadi.")
    bot = Bot(
        BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.outer_middleware(TrackMiddleware())
    dp.callback_query.outer_middleware(TrackMiddleware())
    dp.include_router(admin_router)
    dp.include_router(user_router)

    await bot.set_my_commands([BotCommand(command="start", description="Botni ishga tushirish")])
    admin_commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="admin", description="Admin panel"),
        BotCommand(command="add", description="Kino qo'shish"),
        BotCommand(command="del", description="Kino o'chirish"),
        BotCommand(command="stats", description="Statistika"),
        BotCommand(command="channels", description="Majburiy kanallar"),
        BotCommand(command="broadcast", description="Xabar yuborish"),
        BotCommand(command="backup", description="Baza nusxasini olish"),
        BotCommand(command="restore", description="Bazani tiklash"),
    ]
    for admin_id in SUPER_ADMINS:
        with suppress(TelegramAPIError):
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
    me = await bot.me()
    log.info("Bot ishga tushdi: @%s", me.username)
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await conn.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot to'xtatildi")
