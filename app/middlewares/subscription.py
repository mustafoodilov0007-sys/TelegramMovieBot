from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message

from config import ADMIN_ID
from app.database.db import get_channels
from app.keyboards.subscription import subscription_keyboard


class SubscriptionMiddleware(BaseMiddleware):
    """Majburiy kanal(lar)ga obuna bo'lmagan foydalanuvchilarni botdan foydalanishdan to'xtatadi."""

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        channels = get_channels()

        if not channels or event.from_user.id == ADMIN_ID:
            return await handler(event, data)

        bot: Bot = data["bot"]
        missing = []

        for ch in channels:
            channel_id = ch[1]
            try:
                member = await bot.get_chat_member(chat_id=channel_id, user_id=event.from_user.id)
                is_subscribed = member.status in ("member", "administrator", "creator")
            except Exception:
                is_subscribed = False
            if not is_subscribed:
                missing.append(ch)

        if not missing:
            return await handler(event, data)

        word = "kanalga" if len(missing) == 1 else "kanallarga"
        await event.answer(
            f"⚠️ Botdan foydalanish uchun quyidagi {word} obuna bo'ling, "
            "so'ng «✅ Tekshirish» tugmasini bosing.",
            reply_markup=subscription_keyboard(missing),
        )
        return None
