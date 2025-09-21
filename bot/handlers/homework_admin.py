# bot/handlers/homework_admin.py - НОВИЙ ФАЙЛ

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import pytz
from database.homework import HomeworkManager, StudentProfileManager, FileManager
from config import TIMEZONE, GROUP_ID
import io
import zipfile
import logging

logger = logging.getLogger(__name__)
router = Router()

# Стани для FSM
class CreateHomeworkStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_deadline = State()

class SetStudentNameStates(StatesGroup):
    waiting_for_user_selection = State()
    waiting_for_name = State()

@router.message(F.text == "📝 Управління ДЗ")
async def homework_admin_menu(message: Message, is_admin: bool):
    """Меню управління домашніми завданнями"""
    if not is_admin:
        await message.answer("❌ Ця функція доступна тільки адміністратору.")
        return
    
    keyboard = [
        [
            InlineKeyboardButton(text="➕ Створити ДЗ", callback_data="hw_create"),
            InlineKeyboardButton(text="📋 Всі ДЗ", callback_data="hw_list")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="hw_stats"),
            InlineKeyboardButton(text="👥 Імена студентів", callback_data="hw_names")
        ],
        [
            InlineKeyboardButton(text="📁 Завантажити файли", callback_data="hw_download"),
            InlineKeyboardButton(text="🔔 Нагадування", callback_data="hw_remind")
        ]
    ]
    
    await message.answer(
        "📝 **Управління домашніми завданнями**\n\n"
        "Оберіть дію:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "hw_create")
async def start_create_homework(callback: CallbackQuery, state: FSMContext):
    """Початок створення ДЗ"""
    await callback.message.edit_text(
        "📝 **Створення домашнього завдання**\n\n"
        "Крок 1/4: Введіть назву предмета:"
    )
    
    await state.set_state(CreateHomeworkStates.waiting_for_subject)
    await callback.answer()

@router.message(CreateHomeworkStates.waiting_for_subject)
async def process_hw_subject(message: Message, state: FSMContext):
    """Обробка введення предмета"""
    subject = message.text.strip()
    
    if len(subject) < 2:
        await message.answer("❌ Назва предмета занадто коротка. Спробуйте ще раз:")
        return
    
    await state.update_data(subject_name=subject)
    await message.answer(
        f"📚 **Предмет:** {subject}\n\n"
        "Крок 2/4: Введіть назву завдання:"
    )
    
    await state.set_state(CreateHomeworkStates.waiting_for_title)

@router.message(CreateHomeworkStates.waiting_for_title)
async def process_hw_title(message: Message, state: FSMContext):
    """Обробка введення назви ДЗ"""
    title = message.text.strip()
    
    if len(title) < 3:
        await message.answer("❌ Назва завдання занадто коротка. Спробуйте ще раз:")
        return
    
    await state.update_data(title=title)
    data = await state.get_data()
    
    await message.answer(
        f"📚 **Предмет:** {data['subject_name']}\n"
        f"📋 **Назва:** {title}\n\n"
        "Крок 3/4: Введіть опис завдання (або 'пропустити'):"
    )
    
    await state.set_state(CreateHomeworkStates.waiting_for_description)

@router.message(CreateHomeworkStates.waiting_for_description)
async def process_hw_description(message: Message, state: FSMContext):
    """Обробка введення опису ДЗ"""
    description = message.text.strip()
    
    if description.lower() in ['пропустити', 'skip', '-']:
        description = ""
    
    await state.update_data(description=description)
    data = await state.get_data()
    
    response = f"📚 **Предмет:** {data['subject_name']}\n"
    response += f"📋 **Назва:** {data['title']}\n"
    
    if description:
        response += f"📝 **Опис:** {description[:100]}{'...' if len(description) > 100 else ''}\n"
    
    response += "\nКрок 4/4: Введіть дедлайн у форматі:\n"
    response += "• `ДД.ММ ГГГГ ГГ:ХХ` (наприклад: 15.12 2024 23:59)\n"
    response += "• `ДД.ММ ГГ:ХХ` (наприклад: 15.12 23:59)\n"
    response += "• `завтра ГГ:ХХ` (наприклад: завтра 23:59)\n"
    response += "• `+Х днів` (наприклад: +3 дні)"
    
    await message.answer(response)
    await state.set_state(CreateHomeworkStates.waiting_for_deadline)

@router.message(CreateHomeworkStates.waiting_for_deadline)
async def process_hw_deadline(message: Message, state: FSMContext):
    """Обробка введення дедлайну"""
    deadline_text = message.text.strip()
    
    try:
        kiev_tz = pytz.timezone(TIMEZONE)
        now = datetime.now(kiev_tz)
        
        # Парсинг різних форматів дати
        deadline = None
        
        if deadline_text.startswith("завтра"):
            # Завтра + час
            time_part = deadline_text.replace("завтра", "").strip()
            if time_part:
                hour, minute = map(int, time_part.split(':'))
                deadline = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=1)
            else:
                deadline = now.replace(hour=23, minute=59, second=0, microsecond=0) + timedelta(days=1)
                
        elif deadline_text.startswith("+"):
            # +X днів
            days_str = deadline_text.replace("+", "").replace("днів", "").replace("дні", "").replace("день", "").strip()
            days = int(days_str)
            deadline = now.replace(hour=23, minute=59, second=0, microsecond=0) + timedelta(days=days)
            
        elif len(deadline_text.split()) == 2:
            # ДД.ММ ГГ:ХХ (поточний рік)
            date_part, time_part = deadline_text.split()
            day, month = map(int, date_part.split('.'))
            hour, minute = map(int, time_part.split(':'))
            
            year = now.year
            if month < now.month or (month == now.month and day < now.day):
                year += 1  # Наступний рік якщо дата в минулому
                
            deadline = kiev_tz.localize(datetime(year, month, day, hour, minute))
            
        elif len(deadline_text.split()) == 3:
            # ДД.ММ ГГГГ ГГ:ХХ
            date_part, year_part, time_part = deadline_text.split()
            day, month = map(int, date_part.split('.'))
            year = int(year_part)
            hour, minute = map(int, time_part.split(':'))
            
            deadline = kiev_tz.localize(datetime(year, month, day, hour, minute))
        
        if not deadline or deadline <= now:
            await message.answer("❌ Дедлайн має бути в майбутньому. Спробуйте ще раз:")
            return
        
        # Створюємо ДЗ
        data = await state.get_data()
        homework_id = await HomeworkManager.create_homework(
            subject_name=data['subject_name'],
            title=data['title'],
            description=data['description'],
            deadline=deadline.replace(tzinfo=None),  # Зберігаємо як UTC
            created_by=message.from_user.id
        )
        
        if homework_id:
            # Відправляємо повідомлення в групу
            group_message = f"📝 **Нове домашнє завдання!**\n\n"
            group_message += f"📚 **Предмет:** {data['subject_name']}\n"
            group_message += f"📋 **Завдання:** {data['title']}\n"
            
            if data['description']:
                group_message += f"📝 **Опис:** {data['description']}\n"
            
            group_message += f"⏰ **Дедлайн:** {deadline.strftime('%d.%m.%Y %H:%M')}\n\n"
            group_message += "💡 Для здачі пишіть боту в особисті повідомлення!"
            
            await message.bot.send_message(
                chat_id=GROUP_ID,
                text=group_message
            )
            
            await message.answer(
                "✅ **Домашнє завдання створено!**\n\n"
                f"📚 **Предмет:** {data['subject_name']}\n"
                f"📋 **Назва:** {data['title']}\n"
                f"⏰ **Дедлайн:** {deadline.strftime('%d.%m.%Y %H:%M')}\n\n"
                "Повідомлення надіслано в групу."
            )
        else:
            await message.answer("❌ Помилка створення завдання. Спробуйте ще раз.")
        
        await state.clear()
        
    except ValueError as e:
        await message.answer(f"❌ Неправильний формат дати. Спробуйте ще раз:\n{str(e)}")
    except Exception as e:
        logger.error(f"Помилка створення ДЗ: {e}")
        await message.answer("❌ Помилка створення завдання.")

@router.callback_query(F.data == "hw_list")
async def list_homework(callback: CallbackQuery):
    """Список всіх активних ДЗ"""
    homework_list = await HomeworkManager.get_active_homework()
    
    if not homework_list:
        await callback.message.edit_text("📭 Активних домашніх завдань немає.")
        return
    
    response = "📋 **Активні домашні завдання:**\n\n"
    
    keyboard = []
    
    for hw in homework_list:
        hw_id = str(hw['_id'])
        subject = hw['subject_name']
        title = hw['title']
        deadline = hw['deadline']
        
        # Кількість здач
        submissions_count = len(hw.get('submissions', []))
        
        response += f"📚 **{subject}**\n"
        response += f"📋 {title}\n"
        response += f"⏰ До: {deadline.strftime('%d.%m.%Y %H:%M')}\n"
        response += f"📊 Здали: {submissions_count}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"📊 {title[:20]}...",
                callback_data=f"hw_view_{hw_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="hw_back_menu")
    ])
    
    await callback.message.edit_text(
        response,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("hw_view_"))
async def view_homework_details(callback: CallbackQuery):
    """Детальний перегляд ДЗ"""
    homework_id = callback.data.replace("hw_view_", "")
    stats = await HomeworkManager.get_homework_statistics(homework_id)
    
    if not stats:
        await callback.answer("❌ ДЗ не знайдено")
        return
    
    hw = stats['homework']
    
    response = f"📋 **Деталі завдання:**\n\n"
    response += f"📚 **Предмет:** {hw['subject_name']}\n"
    response += f"📋 **Назва:** {hw['title']}\n"
    
    if hw['description']:
        response += f"📝 **Опис:** {hw['description']}\n"
    
    response += f"⏰ **Дедлайн:** {hw['deadline'].strftime('%d.%m.%Y %H:%M')}\n\n"
    
    response += f"📊 **Статистика:**\n"
    response += f"• Всього студентів: {stats['total_students']}\n"
    response += f"• Здали: {stats['submitted_count']}\n"
    response += f"• Не здали: {stats['not_submitted_count']}\n\n"
    
    if stats['submissions']:
        response += "👥 **Здали роботи:**\n"
        for submission in stats['submissions']:
            name = submission.get('full_name', submission.get('username', 'Ім\'я не встановлено'))
            submitted_time = submission['submitted_at'].strftime('%d.%m %H:%M')
            response += f"• {name} ({submitted_time})\n"
    
    keyboard = [
        [
            InlineKeyboardButton(text="📁 Завантажити файли", callback_data=f"hw_download_{homework_id}"),
            InlineKeyboardButton(text="🔔 Нагадати", callback_data=f"hw_remind_{homework_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Закрити ДЗ", callback_data=f"hw_close_{homework_id}"),
            InlineKeyboardButton(text="◀️ Назад", callback_data="hw_list")
        ]
    ]
    
    await callback.message.edit_text(
        response,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("hw_download_"))
async def download_homework_files(callback: CallbackQuery):
    """Завантаження файлів ДЗ як архіву"""
    homework_id = callback.data.replace("hw_download_", "")
    
    try:
        # Отримуємо інформацію про ДЗ
        homework = await HomeworkManager.get_homework_by_id(homework_id)
        if not homework:
            await callback.answer("❌ ДЗ не знайдено")
            return
        
        submissions = homework.get('submissions', [])
        if not submissions:
            await callback.answer("❌ Файлів для завантаження немає")
            return
        
        await callback.answer("📁 Готую архів з файлами...")
        
        # Створюємо ZIP архів в пам'яті
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            file_count = 0
            
            for submission in submissions:
                student_name = submission.get('full_name', submission.get('username', f"user_{submission['user_id']}"))
                file_ids = submission.get('file_ids', [])
                text_answer = submission.get('text_answer')
                
                # Створюємо папку для кожного студента
                student_folder = f"{student_name.replace('/', '_')}/"
                
                # Додаємо текстову відповідь якщо є
                if text_answer:
                    zip_file.writestr(
                        f"{student_folder}answer.txt",
                        f"Відповідь від {student_name}:\n\n{text_answer}"
                    )
                
                # Додаємо файли (тут потрібно буде реалізувати завантаження файлів з Telegram)
                for i, file_id in enumerate(file_ids, 1):
                    try:
                        # Отримуємо файл від Telegram
                        file = await callback.bot.get_file(file_id)
                        file_data = await callback.bot.download_file(file.file_path)
                        
                        # Визначаємо розширення файлу
                        file_name = f"file_{i}"
                        if file.file_path:
                            file_name = file.file_path.split('/')[-1]
                        
                        zip_file.writestr(f"{student_folder}{file_name}", file_data.read())
                        file_count += 1
                        
                    except Exception as e:
                        logger.error(f"Помилка завантаження файлу {file_id}: {e}")
        
        if file_count == 0:
            await callback.message.answer("❌ Не вдалося завантажити файли")
            return
        
        # Відправляємо архів
        zip_buffer.seek(0)
        
        await callback.message.answer_document(
            document=zip_buffer,
            filename=f"{homework['subject_name']}_{homework['title']}.zip",
            caption=f"📁 Архів з роботами по завданню:\n"
                   f"📚 {homework['subject_name']}\n"
                   f"📋 {homework['title']}\n"
                   f"📊 Файлів: {file_count}"
        )
        
    except Exception as e:
        logger.error(f"Помилка створення архіву: {e}")
        await callback.answer("❌ Помилка створення архіву")

@router.callback_query(F.data == "hw_names")
async def manage_student_names(callback: CallbackQuery, state: FSMContext):
    """Управління іменами студентів"""
    students_without_names = await StudentProfileManager.get_students_without_names()
    
    if not students_without_names:
        await callback.message.edit_text(
            "✅ У всіх студентів встановлені повні імена!"
        )
        return
    
    response = "👥 **Студенти без повних імен:**\n\n"
    keyboard = []
    
    for student in students_without_names:
        username = student.get('username', 'Без username')
        first_name = student.get('first_name', '')
        user_id = student['user_id']
        
        display_name = f"{first_name} (@{username})" if first_name else f"@{username}"
        response += f"• {display_name}\n"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"✏️ {display_name}",
                callback_data=f"set_name_{user_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="hw_back_menu")
    ])
    
    await callback.message.edit_text(
        response,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("set_name_"))
async def set_student_name_start(callback: CallbackQuery, state: FSMContext):
    """Початок встановлення імені студента"""
    user_id = int(callback.data.replace("set_name_", ""))
    
    # Отримуємо інформацію про студента
    from database.models import GroupMembersManager
    members = await GroupMembersManager.get_all_members()
    student = next((m for m in members if m['user_id'] == user_id), None)
    
    if not student:
        await callback.answer("❌ Студента не знайдено")
        return
    
    username = student.get('username', 'Без username')
    first_name = student.get('first_name', '')
    
    await state.update_data(target_user_id=user_id)
    
    await callback.message.edit_text(
        f"✏️ **Встановлення імені для студента:**\n\n"
        f"👤 **Telegram:** {first_name} (@{username})\n\n"
        f"Введіть повне ім'я студента (Прізвище Ім'я Побатькові):"
    )
    
    await state.set_state(SetStudentNameStates.waiting_for_name)

@router.message(SetStudentNameStates.waiting_for_name)
async def process_student_name(message: Message, state: FSMContext):
    """Обробка введення імені студента"""
    full_name = message.text.strip()
    
    if len(full_name) < 5:
        await message.answer("❌ Повне ім'я занадто коротке. Спробуйте ще раз:")
        return
    
    data = await state.get_data()
    user_id = data['target_user_id']
    
    success = await StudentProfileManager.set_student_name(user_id, full_name)
    
    if success:
        await message.answer(f"✅ Ім'я встановлено: {full_name}")
    else:
        await message.answer("❌ Помилка встановлення імені")
    
    await state.clear()

@router.callback_query(F.data.startswith("hw_remind_"))
async def send_homework_reminder(callback: CallbackQuery):
    """Відправка нагадування про ДЗ"""
    homework_id = callback.data.replace("hw_remind_", "")
    
    homework = await HomeworkManager.get_homework_by_id(homework_id)
    if not homework:
        await callback.answer("❌ ДЗ не знайдено")
        return
    
    # Визначаємо хто ще не здав
    submitted_users = {sub['user_id'] for sub in homework.get('submissions', [])}
    
    from database.models import GroupMembersManager
    all_members = await GroupMembersManager.get_all_members()
    not_submitted = [m for m in all_members if m['user_id'] not in submitted_users]
    
    if not not_submitted:
        await callback.answer("✅ Всі студенти вже здали ДЗ!")
        return
    
    # Відправляємо нагадування в групу
    reminder_text = f"🔔 **Нагадування про домашнє завдання!**\n\n"
    reminder_text += f"📚 **Предмет:** {homework['subject_name']}\n"
    reminder_text += f"📋 **Завдання:** {homework['title']}\n"
    reminder_text += f"⏰ **Дедлайн:** {homework['deadline'].strftime('%d.%m.%Y %H:%M')}\n\n"
    
    # Визначаємо час що залишився
    time_left = homework['deadline'] - datetime.utcnow()
    if time_left.days > 0:
        reminder_text += f"⏳ Залишилось: {time_left.days} днів\n\n"
    elif time_left.seconds > 0:
        hours_left = time_left.seconds // 3600
        reminder_text += f"⏳ Залишилось: {hours_left} годин\n\n"
    
    reminder_text += f"❗️ Не здали: {len(not_submitted)} студентів\n"
    reminder_text += "💡 Для здачі пишіть боту в особисті повідомлення!"
    
    await callback.bot.send_message(
        chat_id=GROUP_ID,
        text=reminder_text
    )
    
    await callback.answer("✅ Нагадування надіслано в групу!")

@router.callback_query(F.data.startswith("hw_close_"))
async def close_homework(callback: CallbackQuery):
    """Закриття домашнього завдання"""
    homework_id = callback.data.replace("hw_close_", "")
    
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Так, закрити", callback_data=f"hw_close_confirm_{homework_id}"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data=f"hw_view_{homework_id}")
        ]
    ]
    
    await callback.message.edit_text(
        "❗️ **Підтвердження закриття ДЗ**\n\n"
        "Ви впевнені, що хочете закрити це домашнє завдання?\n"
        "Після закриття студенти не зможуть здавати роботи.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("hw_close_confirm_"))
async def confirm_close_homework(callback: CallbackQuery):
    """Підтвердження закриття ДЗ"""
    homework_id = callback.data.replace("hw_close_confirm_", "")
    
    success = await HomeworkManager.close_homework(homework_id)
    
    if success:
        await callback.message.edit_text("✅ Домашнє завдання закрито!")
        
        # Повідомляємо в групу
        await callback.bot.send_message(
            chat_id=GROUP_ID,
            text="🔒 **Домашнє завдання закрито!**\n\n"
                 "Прийом робіт припинено."
        )
    else:
        await callback.answer("❌ Помилка закриття ДЗ")

@router.callback_query(F.data == "hw_back_menu")
async def back_to_homework_menu(callback: CallbackQuery):
    """Повернення до меню ДЗ"""
    await homework_admin_menu(callback.message, True)