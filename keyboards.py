from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 бюджет"), KeyboardButton(text="🗓 день зп")],
            [KeyboardButton(text="➕ добавить трату"), KeyboardButton(text="🎁 копилка")],
            [KeyboardButton(text="📊 история"), KeyboardButton(text="🔄 обновить лимит")],
            [KeyboardButton(text="⚙️ настройки")]
        ],
        resize_keyboard=True
    )

def get_settings_keyboard(auto_round: bool) -> InlineKeyboardMarkup:
    status_emoji = "🟢" if auto_round else "🔴"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{status_emoji} автокопилка", callback_data="toggle_round")],
            [InlineKeyboardButton(text="🗑 очистить все траты", callback_data="confirm_clear")]
        ]
    )

def get_goals_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ создать цель", callback_data="goal_add")],
            [
                InlineKeyboardButton(text="💰 пополнить", callback_data="goal_deposit"),
                InlineKeyboardButton(text="💸 снять", callback_data="goal_withdraw")
            ],
            [InlineKeyboardButton(text="🗑 удалить цель", callback_data="goal_delete")]
        ]
    )

def get_categories_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚬 табак"), KeyboardButton(text="🛒 продукты")],
            [KeyboardButton(text="⚡️ энергетики"), KeyboardButton(text="💊 лекарства")],
            [KeyboardButton(text="🏠 бытовуха"), KeyboardButton(text="❓ другое")],
            [KeyboardButton(text="❌ отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ отмена")]],
        resize_keyboard=True
    )
