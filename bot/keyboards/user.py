from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Головна клавіатура для користувачів"""
    keyboard = [
        [KeyboardButton(text="📅 Розклад на сьогодні"), KeyboardButton(text="📅 Розклад на завтра")],
        [KeyboardButton(text="📄 Поточний тиждень"), KeyboardButton(text="📄 Наступний тиждень")],
        [KeyboardButton(text="🔗 Посилання на пари")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_schedule_inline_keyboard() -> InlineKeyboardMarkup:
    """Інлайн клавіатура для розкладу"""
    keyboard = [
        [
            InlineKeyboardButton(text="📅 Сьогодні", callback_data="schedule_today"),
            InlineKeyboardButton(text="📅 Завтра", callback_data="schedule_tomorrow")
        ],
        [
            InlineKeyboardButton(text="📄 Поточний тиждень", callback_data="schedule_current_week"),
            InlineKeyboardButton(text="📄 Наступний тиждень", callback_data="schedule_next_week")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)