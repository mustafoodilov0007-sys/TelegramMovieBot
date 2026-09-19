from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_RANDOM = "🎲 Tasodifiy"
BTN_TOP = "🏆 Top"
BTN_SEARCH = "🔍 Qidiruv"
BTN_MOVIES = "🟦 Kinolar"
BTN_CARTOONS = "🟪 Multfilmlar"
BTN_SUPPORT = "💛 Qo'llab-quvvatlash"
BTN_AD = "📢 Reklama berish"
BTN_ADMIN = "⚙️ Admin panel"


def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=BTN_MOVIES), KeyboardButton(text=BTN_CARTOONS)],
        [KeyboardButton(text=BTN_RANDOM), KeyboardButton(text=BTN_TOP)],
        [KeyboardButton(text=BTN_SEARCH)],
        [KeyboardButton(text=BTN_SUPPORT), KeyboardButton(text=BTN_AD)],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text=BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
