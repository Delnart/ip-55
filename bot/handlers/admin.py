from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import LinksManager, GroupMembersManager
from bot.keyboards.admin import (
    get_admin_keyboard, 
    get_link_type_keyboard, 
    get_cancel_keyboard,
    get_confirm_delete_keyboard
)
from bot.keyboards.user import get_main_keyboard
import logging

logger = logging.getLogger(__name__)
router = Router()

# Стани для FSM
class AddLinkStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_subject = State()
    waiting_for_teacher = State()
    waiting_for_meet_link = State()
    waiting_for_classroom_link = State()

class DeleteLinkStates(StatesGroup):
    waiting_for_selection = State()

# Фільтр для адміна
def admin_only():
    async def check(message: Message, is_admin: bool) -> bool:
        if not is_admin:
            await message.answer("❌ Ця команда доступна тільки адміністратору.")
            return False
        return True
    return check

@router.message(Command("admin"), admin_only())
async def cmd_admin(message: Message):
    """Панель адміністратора"""
    admin_text = """
🔧 **Панель адміністратора**

Доступні функції:
• ➕ Додати посилання на пару
• 📋 Переглянути всі посилання
• 👥 Список учасників групи
• 🗑 Видалити посилання
• ⚙️ Налаштування бота

Оберіть дію з меню нижче:
    """
    
    await message.answer(admin_text, reply_markup=get_admin_keyboard())

@router.message(F.text == "➕ Додати посилання", admin_only())
async def start_add_link(message: Message, state: FSMContext):
    """Початок процесу додавання посилання"""
    await message.answer(
        "🔗 **Додавання посилання на пару**\n\n"
        "Оберіть тип заняття:",
        reply_markup=get_link_type_keyboard()
    )
    await state.set_state(AddLinkStates.waiting_for_type)

@router.callback_query(F.data.startswith("link_type_"), AddLinkStates.waiting_for_type)
async def process_link_type(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору типу заняття"""
    class_type = callback.data.replace("link_type_", "")
    
    await state.update_data(class_type=class_type)
    
    await callback.message.edit_text(
        f"📚 **Додавання посилання ({class_type})**\n\n"
        "Введіть назву предмета:",
        reply_markup=get_cancel_keyboard()
    )
    
    await state.set_state(AddLinkStates.waiting_for_subject)
    await callback.answer()

@router.message(AddLinkStates.waiting_for_subject)
async def process_subject_name(message: Message, state: FSMContext):
    """Обробка введення назви предмета"""
    subject_name = message.text.strip()
    
    if len(subject_name) < 3:
        await message.answer("❌ Назва предмета занадто коротка. Введіть повну назву:")
        return
    
    await state.update_data(subject_name=subject_name)
    
    await message.answer(
        f"👨‍🏫 **Предмет:** {subject_name}\n\n"
        "Введіть ПІБ викладача:",
        reply_markup=get_cancel_keyboard()
    )
    
    await state.set_state(AddLinkStates.waiting_for_teacher)

@router.message(AddLinkStates.waiting_for_teacher)
async def process_teacher_name(message: Message, state: FSMContext):
    """Обробка введення ПІБ викладача"""
    teacher_name = message.text.strip()
    
    if len(teacher_name) < 5:
        await message.answer("❌ ПІБ викладача занадто коротке. Введіть повне ПІБ:")
        return
    
    await state.update_data(teacher_name=teacher_name)
    
    data = await state.get_data()
    
    await message.answer(
        f"📚 **Предмет:** {data['subject_name']}\n"
        f"👨‍🏫 **Викладач:** {teacher_name}\n"
        f"📝 **Тип:** {data['class_type']}\n\n"
        "🔗 Введіть посилання на зустріч (Google Meet/Zoom):",
        reply_markup=get_cancel_keyboard()
    )
    
    await state.set_state(AddLinkStates.waiting_for_meet_link)

@router.message(AddLinkStates.waiting_for_meet_link)
async def process_meet_link(message: Message, state: FSMContext):
    """Обробка введення посилання на зустріч"""
    meet_link = message.text.strip()
    
    # Перевірка чи це валідне посилання
    if not (meet_link.startswith('http://') or meet_link.startswith('https://')):
        await message.answer("❌ Введіть правильне посилання (має починатися з http:// або https://):")
        return
    
    await state.update_data(meet_link=meet_link)
    
    await message.answer(
        "📖 **Опційно:** Введіть посилання на Google Classroom (або надішліть 'пропустити'):",
        reply_markup=get_cancel_keyboard()
    )
    
    await state.set_state(AddLinkStates.waiting_for_classroom_link)

@router.message(AddLinkStates.waiting_for_classroom_link)
async def process_classroom_link(message: Message, state: FSMContext):
    """Обробка введення посилання на Google Classroom"""
    classroom_link = None
    
    if message.text.strip().lower() not in ['пропустити', 'skip', '-']:
        classroom_link = message.text.strip()
        
        # Перевірка чи це валідне посилання
        if not (classroom_link.startswith('http://') or classroom_link.startswith('https://')):
            await message.answer("❌ Введіть правильне посилання або 'пропустити':")
            return
    
    # Отримуємо всі дані та зберігаємо
    data = await state.get_data()
    
    success = await LinksManager.add_link(
        subject_name=data['subject_name'],
        teacher_name=data['teacher_name'],
        class_type=data['class_type'],
        meet_link=data['meet_link'],
        classroom_link=classroom_link
    )
    
    if success:
        response = "✅ **Посилання успішно додано!**\n\n"
        response += f"📚 **Предмет:** {data['subject_name']}\n"
        response += f"👨‍🏫 **Викладач:** {data['teacher_name']}\n"
        response += f"📝 **Тип:** {data['class_type']}\n"
        response += f"🔗 **Зустріч:** {data['meet_link']}\n"
        
        if classroom_link:
            response += f"📖 **Classroom:** {classroom_link}\n"
        
        await message.answer(response, reply_markup=get_admin_keyboard())
    else:
        await message.answer(
            "❌ Помилка при збереженні посилання. Спробуйте ще раз.",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

@router.message(F.text == "📋 Всі посилання", admin_only())
async def show_all_links_admin(message: Message):
    """Показати всі посилання (адмін версія)"""
    links = await LinksManager.get_all_links()
    
    if not links:
        await message.answer("📭 Посилання ще не додано.")
        return
    
    response = "🔗 **Всі посилання на пари:**\n\n"
    
    for i, link in enumerate(links, 1):
        subject = link.get('subject_name', 'Невідомий предмет')
        teacher = link.get('teacher_name', 'Невідомий викладач')
        class_type = link.get('class_type', '')
        meet_link = link.get('meet_link', '')
        classroom_link = link.get('classroom_link')
        
        response += f"**{i}. {subject}**\n"
        response += f"👨‍🏫 {teacher} ({class_type})\n"
        response += f"🔗 {meet_link}\n"
        
        if classroom_link:
            response += f"📖 {classroom_link}\n"
        
        response += "\n"
    
    await message.answer(response, parse_mode="Markdown", disable_web_page_preview=True)

@router.message(F.text == "👥 Учасники групи", admin_only())
async def show_group_members(message: Message):
    """Показати учасників групи"""
    members = await GroupMembersManager.get_all_members()
    
    if not members:
        await message.answer("📭 Учасників групи не знайдено.")
        return
    
    response = f"👥 **Учасники групи ({len(members)}):**\n\n"
    
    for i, member in enumerate(members, 1):
        username = member.get('username', 'Без username')
        first_name = member.get('first_name', '')
        last_name = member.get('last_name', '')
        user_id = member.get('user_id', '')
        
        full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            full_name = "Ім'я не вказано"
        
        response += f"{i}. **{full_name}**\n"
        response += f"   @{username} (ID: {user_id})\n\n"
    
    await message.answer(response, parse_mode="Markdown")

@router.message(F.text == "👤 Користувач", admin_only())
async def switch_to_user_mode(message: Message):
    """Перехід у користувацький режим"""
    await message.answer(
        "👤 Перехід у користувацький режим.\n\n"
        "Для повернення до панелі адміна використовуйте /admin",
        reply_markup=get_main_keyboard()
    )


@router.message(F.text == "🗑 Видалити посилання", admin_only())
async def start_delete_link(message: Message, state: FSMContext):
    """Початок процесу видалення посилання"""
    links = await LinksManager.get_all_links()
    
    if not links:
        await message.answer("📭 Посилання для видалення не знайдено.")
        return
    
    response = "🗑 **Видалення посилань**\n\nОберіть посилання для видалення:\n\n"
    
    keyboard = []
    
    for i, link in enumerate(links, 1):
        subject = link.get('subject_name', 'Невідомий предмет')
        teacher = link.get('teacher_name', 'Невідомий викладач')
        class_type = link.get('class_type', '')
        
        response += f"{i}. **{subject}** - {teacher} ({class_type})\n"
        
        # Створюємо унікальний ID для кнопки
        link_id = f"{subject}|{teacher}|{class_type}"
        keyboard.append([InlineKeyboardButton(
            text=f"{i}. {subject} ({class_type})",
            callback_data=f"delete_link_{i-1}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel")])
    
    await message.answer(
        response,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )
    
    # Зберігаємо список посилань в стані
    await state.update_data(links=links)
    await state.set_state(DeleteLinkStates.waiting_for_selection)

@router.callback_query(F.data.startswith("delete_link_"), DeleteLinkStates.waiting_for_selection)
async def confirm_delete_link(callback: CallbackQuery, state: FSMContext):
    """Підтвердження видалення посилання"""
    try:
        link_index = int(callback.data.replace("delete_link_", ""))
        data = await state.get_data()
        links = data.get('links', [])
        
        if link_index >= len(links):
            await callback.answer("❌ Невірний вибір")
            return
        
        selected_link = links[link_index]
        subject = selected_link.get('subject_name', '')
        teacher = selected_link.get('teacher_name', '')
        class_type = selected_link.get('class_type', '')
        
        await callback.message.edit_text(
            f"🗑 **Видалення посилання**\n\n"
            f"📚 **Предмет:** {subject}\n"
            f"👨‍🏫 **Викладач:** {teacher}\n"
            f"📝 **Тип:** {class_type}\n\n"
            f"❗️ Ви впевнені, що хочете видалити це посилання?",
            reply_markup=get_confirm_delete_keyboard(str(link_index))
        )
        
        await callback.answer()
        
    except ValueError:
        await callback.answer("❌ Помилка вибору")

@router.callback_query(F.data.startswith("delete_confirm_"))
async def delete_link_confirmed(callback: CallbackQuery, state: FSMContext):
    """Остаточне видалення посилання"""
    try:
        link_index = int(callback.data.replace("delete_confirm_", ""))
        data = await state.get_data()
        links = data.get('links', [])
        
        if link_index >= len(links):
            await callback.answer("❌ Невірний вибір")
            return
        
        selected_link = links[link_index]
        subject = selected_link.get('subject_name', '')
        teacher = selected_link.get('teacher_name', '')
        class_type = selected_link.get('class_type', '')
        
        success = await LinksManager.delete_link(subject, teacher, class_type)
        
        if success:
            await callback.message.edit_text(
                f"✅ **Посилання успішно видалено!**\n\n"
                f"📚 **Предмет:** {subject}\n"
                f"👨‍🏫 **Викладач:** {teacher}\n"
                f"📝 **Тип:** {class_type}"
            )
        else:
            await callback.message.edit_text("❌ Помилка видалення посилання.")
        
        await state.clear()
        await callback.answer("Посилання видалено" if success else "Помилка видалення")
        
    except ValueError:
        await callback.answer("❌ Помилка видалення")

@router.callback_query(F.data == "delete_cancel")
async def cancel_delete_link(callback: CallbackQuery, state: FSMContext):
    """Скасування видалення посилання"""
    await callback.message.edit_text("❌ Видалення скасовано.")
    await state.clear()
    await callback.answer("Видалення скасовано")

@router.message(F.text == "👤 Користувач", admin_only())
async def switch_to_user_mode(message: Message):
    """Перехід у користувацький режим"""
    await message.answer(
        "👤 Перехід у користувацький режим.\n\n"
        "Для повернення до панелі адміна використовуйте /admin",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "⚙️ Налаштування", admin_only())
async def show_settings(message: Message):
    """Показати налаштування бота"""
    settings_text = f"""
⚙️ **Налаштування бота:**

🔔 **Сповіщення:** За {NOTIFICATION_MINUTES_BEFORE} хв до початку пари
🕒 **Часова зона:** {TIMEZONE}
👥 **ID групи:** `{GROUP_ID}`
🤖 **Версія:** 1.0

📊 **Статистика:**
• Посилань у базі: {len(await LinksManager.get_all_links())}
• Учасників групи: {len(await GroupMembersManager.get_all_members())}
    """
    
    await message.answer(settings_text, parse_mode="Markdown")

# Обробка скасування операцій
@router.callback_query(F.data.in_(["cancel", "cancel_add_link"]))
async def cancel_operation(callback: CallbackQuery, state: FSMContext):
    """Скасування поточної операції"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Операцію скасовано.",
        reply_markup=None
    )
    await callback.answer("Операцію скасовано")



