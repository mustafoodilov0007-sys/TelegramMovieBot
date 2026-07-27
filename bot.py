import asyncio

from app.database import db
from app.database.db import add_user
from app.handlers.admin import router as admin_router
from app.handlers.subscription import router as subscription_router
from app.handlers.user import router as user_router
from app.handlers.search import router as search_router
from app.keyboards.main_menu import main_menu_keyboard
from app.middlewares.subscription import SubscriptionMiddleware


from aiogram.types import Message
from aiogram.filters import CommandStart

from loader import bot, dp

# Majburiy obuna tekshiruvi barcha xabarlar uchun ishga tushadi
dp.message.middleware(SubscriptionMiddleware())

# Routerlar shu yerda ulanadi (tartib muhim: admin -> obuna -> menyu tugmalari -> erkin qidiruv)
dp.include_router(admin_router)
dp.include_router(subscription_router)
dp.include_router(user_router)
dp.include_router(search_router)


@dp.message(CommandStart())
async def start(message: Message):
    add_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    name = message.from_user.full_name or "do'stim"
    await message.answer(
        f"👋 Assalomu alaykum, <b>{name}</b> botimizga xush kelibsiz.\n\n"
        f"✍️ <i>Kino yoki multfilm kodini yuboring.</i>",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
