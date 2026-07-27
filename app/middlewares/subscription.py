from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message

from config import ADMIN_ID
from app.database.db import get_setting
from app.keyboards.subscription import subscription_keyboard


class SubscriptionMiddleware(BaseMiddleware):
    """Kanalga obuna bo'lmagan foydalanuvchilarni botdan foydalanishdan to'xtatadi."""

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        channel_id = get_setting("channel_id")

        if not channel_id or event.from_user.id == ADMIN_ID:
            return await handler(event, data)

        bot: Bot = data["bot"]

        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=event.from_user.id)
            is_subscribed = member.status in ("member", "administrator", "creator")
        except Exception:
            is_subscribed = False

        if is_subscribed:
            return await handler(event, data)

        await event.answer(
            "⚠️ Botdan foydalanish uchun avval kanalga obuna bo'ling, "
            "so'ng «✅ Tekshirish» tugmasini bosing.",
            reply_markup=subscription_keyboard(),
        )
        return None
