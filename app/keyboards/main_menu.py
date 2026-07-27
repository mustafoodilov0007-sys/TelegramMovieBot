from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_RANDOM = "🎲 Tasodifiy"
BTN_TOP = "🏆 Top multfilmlar"
BTN_SEARCH = "🔍 Qidiruv"
BTN_LIST = "🎬 Multfilmlar"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_RANDOM), KeyboardButton(text=BTN_TOP)],
            [KeyboardButton(text=BTN_SEARCH), KeyboardButton(text=BTN_LIST)],
        ],
        resize_keyboard=True,
    )
