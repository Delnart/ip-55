from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Клавіатура для адміна"""
    keyboard = [
        [KeyboardButton(text="➕ Додати посилання"), KeyboardButton(text="📋 Всі посилання")],
        [KeyboardButton(text="👥 Учасники групи"), KeyboardButton(text="🗑 Видалити посилання")],
        [KeyboardButton(text="👤 Користувач"), KeyboardButton(text="⚙️ Налаштування")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_link_type_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура для вибору типу посилання"""
    keyboard = [
        [
            InlineKeyboardButton(text="📚 Лекція", callback_data="link_type_Лек"),
            InlineKeyboardButton(text="💻 Практика", callback_data="link_type_Прак")
        ],
        [
            InlineKeyboardButton(text="🔬 Лабораторна", callback_data="link_type_Лаб")
        ],
        [
            InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_add_link")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура для скасування операції"""
    keyboard = [
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_confirm_delete_keyboard(link_id: str) -> InlineKeyboardMarkup:
    """Клавіатура для підтвердження видалення посилання"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Так, видалити", callback_data=f"delete_confirm_{link_id}"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="delete_cancel")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)