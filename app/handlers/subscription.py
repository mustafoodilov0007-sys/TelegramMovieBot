from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from config import CHANNEL_ID
from app.database.db import add_user, get_setting
from app.keyboards.main_menu import main_menu_keyboard

router = Router()


@router.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery, bot: Bot):
    channel_id = get_setting("channel_id", CHANNEL_ID)
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=callback.from_user.id)
        is_subscribed = member.status in ("member", "administrator", "creator")
    except Exception:
        is_subscribed = False

    if is_subscribed:
        add_user(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
        await callback.message.edit_text("✅ Obuna tasdiqlandi!")
        await callback.message.answer(
            "🔎 Endi kino yoki multfilm nomini/kodini yuboring, "
            "yoki quyidagi menyudan foydalaning.",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmagansiz.", show_alert=True)
