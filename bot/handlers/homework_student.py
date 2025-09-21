# bot/handlers/homework_student.py - НОВИЙ ФАЙЛ

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from database.homework import HomeworkManager, StudentProfileManager, FileManager
from config import GROUP_ID
import logging

logger = logging.getLogger(__name__)
router = Router()

# Стани для FSM
class SubmitHomeworkStates(StatesGroup):
    waiting_for_homework_selection = State()
    waiting_for_files = State()
    waiting_for_text_answer = State()
    confirming_submission = State()

class SetNameStates(StatesGroup):
    waiting_for_name = State()

@router.message(F.text == "📝 Мої ДЗ", ~F.chat.id.in_({GROUP_ID}))
async def my_homework_menu(message: Message):
    """Меню домашніх завдань для студента"""
    # Перевіряємо чи встановлено ім'я
    full_name = await StudentProfileManager.get_student_name(message.from_user.id)
    
    if not full_name:
        keyboard = [
            [InlineKeyboardButton(text="✏️ Встановити ім'я", callback_data="set_my_name")]
        ]
        
        await message.answer(
            "❗️ **Увага!**\n\n"
            "Для здачі домашніх завдань необхідно встановити ваше повне ім'я.\n"
            "Це допоможе викладачу ідентифікувати вашу роботу.\n\n"
            "👤 **Поточне ім'я:** не встановлено",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        return
    
    # Показуємо меню ДЗ
    homework_list = await HomeworkManager.get_active_homework()
    my_submissions = await HomeworkManager.get_user_submissions(message.from_user.id)
    
    submitted_ids = {sub['homework_id'] for sub in my_submissions}
    
    keyboard = [
        [
            InlineKeyboardButton(text="📋 Активні ДЗ", callback_data="hw_active"),
            InlineKeyboardButton(text="📊 Мої здачі", callback_data="hw_my_submissions")
        ],
        [
            InlineKeyboardButton(text="✏️ Змінити ім'я", callback_data="set_my_name")
        ]
    ]
    
    response = f"📝 **Домашні завдання**\n\n"
    response += f"👤 **Ваше ім'я:** {full_name}\n\n"
    response += f"📊 **Статистика:**\n"
    response += f"• Активних ДЗ: {len(homework_list)}\n"
    response += f"• Ви здали: {len(submitted_ids)}\n"
    response += f"• Не здано: {len(homework_list) - len(submitted_ids)}\n"
    
    await message.answer(response, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "set_my_name")
async def set_my_name_start(callback: CallbackQuery, state: FSMContext):
    """Початок встановлення власного імені"""
    current_name = await StudentProfileManager.get_student_name(callback.from_user.id)
    
    response = "✏️ **Встановлення повного імені**\n\n"
    response += "Введіть ваше повне ім'я у форматі:\n"
    response += "**Прізвище Ім'я Побатькові**\n\n"
    response += "Наприклад: Іванов Іван Іванович\n\n"
    
    if current_name:
        response += f"📝 **Поточне ім'я:** {current_name}\n"
    
    await callback.message.edit_text(response)
    await state.set_state(SetNameStates.waiting_for_name)
    await callback.answer()

@router.message(SetNameStates.waiting_for_name)
async def process_my_name(message: Message, state: FSMContext):
    """Обробка встановлення власного імені"""
    full_name = message.text.strip()
    
    if len(full_name) < 5:
        await message.answer("❌ Повне ім'я занадто коротке. Спробуйте ще раз:")
        return
    
    if len(full_name.split()) < 2:
        await message.answer("❌ Введіть прізвище та ім'я. Спробуйте ще раз:")
        return
    
    success = await StudentProfileManager.set_student_name(message.from_user.id, full_name)
    
    if success:
        await message.answer(
            f"✅ **Ім'я встановлено!**\n\n"
            f"👤 **Ваше ім'я:** {full_name}\n\n"
            "Тепер ви можете здавати домашні завдання!"
        )
    else:
        await message.answer("❌ Помилка встановлення імені. Спробуйте пізніше.")
    
    await state.clear()

@router.callback_query(F.data == "hw_active")
async def show_active_homework(callback: CallbackQuery):
    """Показати активні ДЗ"""
    homework_list = await HomeworkManager.get_active_homework()
    my_submissions = await HomeworkManager.get_user_submissions(callback.from_user.id)
    
    submitted_ids = {sub['homework_id'] for sub in my_submissions}
    
    if not homework_list:
        await callback.message.edit_text(
            "📭 **Активних домашніх завдань немає**\n\n"
            "Коли з'являться нові завдання, ви отримаєте повідомлення в групі."
        )
        return
    
    response = "📋 **Активні домашні завдання:**\n\n"
    keyboard = []
    
    for hw in homework_list:
        hw_id = str(hw['_id'])
        subject = hw['subject_name']
        title = hw['title']
        deadline = hw['deadline']
        
        # Визначаємо статус
        if hw_id in submitted_ids:
            status = "✅ Здано"
            emoji = "✅"
        else:
            # Перевіряємо чи не прострочено
            time_left = deadline - datetime.utcnow()
            if time_left.total_seconds() < 0:
                status = "❌ Прострочено"
                emoji = "❌"
            elif time_left.days == 0 and time_left.seconds < 86400:  # Менше доби
                status = "⚠️ Терміново"
                emoji = "⚠️"
            else:
                status = "⏳ Потрібно здати"
                emoji = "📝"
        
        response += f"{emoji} **{subject}**\n"
        response += f"📋 {title}\n"
        response += f"⏰ До: {deadline.strftime('%d.%m.%Y %H:%M')}\n"
        response += f"📊 {status}\n\n"
        
        # Додаємо кнопку тільки для активних завдань
        if hw_id not in submitted_ids and time_left.total_seconds() > 0:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📝 Здати: {title[:15]}...",
                    callback_data=f"submit_hw_{hw_id}"
                )
            ])
        elif hw_id in submitted_ids:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"👁 Переглянути: {title[:15]}...",
                    callback_data=f"view_my_hw_{hw_id}"
                )
            ])
    
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="hw_back_student")
    ])
    
    await callback.message.edit_text(
        response, 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "hw_my_submissions")
async def show_my_submissions(callback: CallbackQuery):
    """Показати мої здачі"""
    my_submissions = await HomeworkManager.get_user_submissions(callback.from_user.id)
    
    if not my_submissions:
        await callback.message.edit_text(
            "📭 **Ви ще не здавали домашніх завдань**\n\n"
            "Коли здасте перше завдання, воно з'явиться тут."
        )
        return
    
    response = "📊 **Мої здачі:**\n\n"
    keyboard = []
    
    for submission in my_submissions:
        subject = submission['subject_name']
        title = submission['title']
        submitted_at = submission['submitted_at']
        deadline = submission['deadline']
        
        # Перевіряємо чи здано вчасно
        if submitted_at <= deadline:
            status = "✅ Вчасно"
        else:
            status = "⏰ Із запізненням"
        
        response += f"📚 **{subject}**\n"
        response += f"📋 {title}\n"
        response += f"📅 Здано: {submitted_at.strftime('%d.%m.%Y %H:%M')}\n"
        response += f"📊 {status}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"👁 {title[:20]}...",
                callback_data=f"view_my_hw_{submission['homework_id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="hw_back_student")
    ])
    
    await callback.message.edit_text(
        response,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("submit_hw_"))
async def start_submit_homework(callback: CallbackQuery, state: FSMContext):
    """Початок здачі ДЗ"""
    homework_id = callback.data.replace("submit_hw_", "")
    
    homework = await HomeworkManager.get_homework_by_id(homework_id)
    if not homework:
        await callback.answer("❌ ДЗ не знайдено")
        return
    
    # Перевіряємо дедлайн
    if homework['deadline'] < datetime.utcnow():
        await callback.answer("❌ Дедлайн минув, здача неможлива", show_alert=True)
        return
    
    await state.update_data(homework_id=homework_id, files=[])
    
    response = f"📝 **Здача домашнього завдання**\n\n"
    response += f"📚 **Предмет:** {homework['subject_name']}\n"
    response += f"📋 **Завдання:** {homework['title']}\n"
    
    if homework['description']:
        response += f"📝 **Опис:** {homework['description']}\n"
    
    response += f"⏰ **Дедлайн:** {homework['deadline'].strftime('%d.%m.%Y %H:%M')}\n\n"
    
    # Визначаємо час що залишився
    time_left = homework['deadline'] - datetime.utcnow()
    if time_left.days > 0:
        response += f"⏳ Залишилось: {time_left.days} днів\n\n"
    elif time_left.seconds > 0:
        hours_left = time_left.seconds // 3600
        response += f"⏳ Залишилось: {hours_left} годин\n\n"
    
    response += "📎 **Крок 1:** Надішліть файли (фото, документи) або натисніть 'Пропустити'\n"
    response += "💡 Після відправки всіх файлів натисніть 'Далі'"
    
    keyboard = [
        [
            InlineKeyboardButton(text="➡️ Далі (без файлів)", callback_data="hw_next_step"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="hw_back_student")
        ]
    ]
    
    await callback.message.edit_text(
        response,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    await state.set_state(SubmitHomeworkStates.waiting_for_files)

@router.message(SubmitHomeworkStates.waiting_for_files)
async def process_homework_files(message: Message, state: FSMContext):
    """Обробка файлів для ДЗ"""
    data = await state.get_data()
    files = data.get('files', [])
    
    file_id = None
    file_name = "file"
    file_type = "unknown"
    
    # Обробляємо різні типи файлів
    if message.photo:
        file_id = message.photo[-1].file_id  # Беремо найбільше фото
        file_name = f"photo_{len(files) + 1}.jpg"
        file_type = "photo"
    elif message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name or f"document_{len(files) + 1}"
        file_type = "document"
    elif message.video:
        file_id = message.video.file_id
        file_name = f"video_{len(files) + 1}.mp4"
        file_type = "video"
    elif message.audio:
        file_id = message.audio.file_id
        file_name = message.audio.file_name or f"audio_{len(files) + 1}.mp3"
        file_type = "audio"
    elif message.voice:
        file_id = message.voice.file_id
        file_name = f"voice_{len(files) + 1}.ogg"
        file_type = "voice"
    
    if file_id:
        # Зберігаємо інформацію про файл
        files.append({
            "file_id": file_id,
            "file_name": file_name,
            "file_type": file_type
        })
        
        await state.update_data(files=files)
        
        # Зберігаємо в базу
        await FileManager.save_file_info(
            file_id=file_id,
            user_id=message.from_user.id,
            file_name=file_name,
            file_type=file_type,
            homework_id=data['homework_id']
        )
        
        keyboard = [
            [
                InlineKeyboardButton(text="➡️ Далі", callback_data="hw_next_step"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="hw_back_student")
            ]
        ]
        
        await message.answer(
            f"✅ **Файл додано:** {file_name}\n"
            f"📊 **Всього файлів:** {len(files)}\n\n"
            "📎 Надішліть ще файли або натисніть 'Далі'",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        await message.answer(
            "❌ Непідтримуваний тип файлу.\n"
            "Підтримуються: фото, документи, відео, аудіо, голосові повідомлення."
        )

@router.callback_query(F.data == "hw_next_step", SubmitHomeworkStates.waiting_for_files)
async def homework_text_step(callback: CallbackQuery, state: FSMContext):
    """Перехід до текстової частини"""
    data = await state.get_data()
    files = data.get('files', [])
    
    response = f"📝 **Крок 2:** Текстова відповідь\n\n"
    
    if files:
        response += f"✅ Файлів додано: {len(files)}\n\n"
    
    response += "💭 Введіть текстову відповідь або пояснення до завдання.\n"
    response += "Якщо текстової частини немає, натисніть 'Пропустити'."
    
    keyboard = [
        [
            InlineKeyboardButton(text="⏭ Пропустити", callback_data="hw_final_step"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="hw_back_student")
        ]
    ]
    
    await callback.message.edit_text(
        response,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    await state.set_state(SubmitHomeworkStates.waiting_for_text_answer)

@router.message(SubmitHomeworkStates.waiting_for_text_answer)
async def process_homework_text(message: Message, state: FSMContext):
    """Обробка текстової відповіді"""
    text_answer = message.text.strip()
    
    if len(text_answer) > 4000:  # Обмеження Telegram
        await message.answer("❌ Текст занадто довгий. Максимум 4000 символів.")
        return
    
    await state.update_data(text_answer=text_answer)
    
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Здати роботу", callback_data="hw_final_step"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="hw_back_student")
        ]
    ]
    
    await message.answer(
        f"✅ **Текстова відповідь додана**\n\n"
        f"📝 **Перші 100 символів:** {text_answer[:100]}{'...' if len(text_answer) > 100 else ''}\n\n"
        "Натисніть 'Здати роботу' для завершення.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "hw_final_step")
async def final_submit_homework(callback: CallbackQuery, state: FSMContext):
    """Фінальне підтвердження здачі"""
    data = await state.get_data()
    homework_id = data['homework_id']
    files = data.get('files', [])
    text_answer = data.get('text_answer', '')
    
    # Отримуємо інформацію про ДЗ
    homework = await HomeworkManager.get_homework_by_id(homework_id)
    if not homework:
        await callback.answer("❌ ДЗ не знайдено")
        return
    
    # Отримуємо ім'я студента
    full_name = await StudentProfileManager.get_student_name(callback.from_user.id)
    if not full_name:
        await callback.answer("❌ Спочатку встановіть ваше ім'я")
        return
    
    # Показуємо підсумок
    response = f"📋 **Підтвердження здачі**\n\n"
    response += f"📚 **Предмет:** {homework['subject_name']}\n"
    response += f"📋 **Завдання:** {homework['title']}\n"
    response += f"👤 **Студент:** {full_name}\n\n"
    
    if files:
        response += f"📎 **Файлів:** {len(files)}\n"
        for i, file_info in enumerate(files, 1):
            response += f"  {i}. {file_info['file_name']} ({file_info['file_type']})\n"
        response += "\n"
    
    if text_answer:
        response += f"📝 **Текстова відповідь:** {len(text_answer)} символів\n\n"
    
    if not files and not text_answer:
        response += "⚠️ **Увага:** Ви здаєте роботу без файлів і тексту!\n\n"
    
    response += "Підтвердіть здачу домашнього завдання:"
    
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Підтверджую", callback_data="hw_confirm_submit"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="hw_back_student")
        ]
    ]
    
    await callback.message.edit_text(
        response,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    await state.set_state(SubmitHomeworkStates.confirming_submission)

@router.callback_query(F.data == "hw_confirm_submit", SubmitHomeworkStates.confirming_submission)
async def confirm_submit_homework(callback: CallbackQuery, state: FSMContext):
    """Підтвердження та збереження здачі"""
    data = await state.get_data()
    homework_id = data['homework_id']
    files = data.get('files', [])
    text_answer = data.get('text_answer', '')
    
    # Отримуємо ім'я студента
    full_name = await StudentProfileManager.get_student_name(callback.from_user.id)
    
    # Підготовуємо список file_id
    file_ids = [f['file_id'] for f in files]
    
    # Зберігаємо здачу
    success = await HomeworkManager.submit_homework(
        homework_id=homework_id,
        user_id=callback.from_user.id,
        username=callback.from_user.username or '',
        full_name=full_name,
        file_ids=file_ids,
        text_answer=text_answer if text_answer else None
    )
    
    if success:
        homework = await HomeworkManager.get_homework_by_id(homework_id)
        
        await callback.message.edit_text(
            f"✅ **Домашнє завдання здано успішно!**\n\n"
            f"📚 **Предмет:** {homework['subject_name']}\n"
            f"📋 **Завдання:** {homework['title']}\n"
            f"📅 **Здано:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"📊 **Ваша здача:**\n"
            f"• Файлів: {len(file_ids)}\n"
            f"• Текст: {'Є' if text_answer else 'Немає'}\n\n"
            "🎉 Дякуємо за виконання завдання!"
        )
        
        # Повідомляємо адміну в особисті повідомлення (опціонально)
        from config import ADMIN_ID
        try:
            await callback.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📝 **Нова здача ДЗ!**\n\n"
                     f"👤 **Студент:** {full_name} (@{callback.from_user.username})\n"
                     f"📚 **Предмет:** {homework['subject_name']}\n"
                     f"📋 **Завдання:** {homework['title']}\n"
                     f"📎 **Файлів:** {len(file_ids)}\n"
                     f"📝 **Текст:** {'Є' if text_answer else 'Немає'}"
            )
        except:
            pass  # Якщо не вдалося - не критично
            
    else:
        await callback.message.edit_text(
            "❌ **Помилка здачі роботи!**\n\n"
            "Спробуйте пізніше або зверніться до адміністратора."
        )
    
    await state.clear()

@router.callback_query(F.data.startswith("view_my_hw_"))
async def view_my_homework(callback: CallbackQuery):
    """Перегляд своєї здачі"""
    homework_id = callback.data.replace("view_my_hw_", "")
    
    # Отримуємо інформацію про ДЗ
    homework = await HomeworkManager.get_homework_by_id(homework_id)
    if not homework:
        await callback.answer("❌ ДЗ не знайдено")
        return
    
    # Знаходимо свою здачу
    my_submission = None
    for submission in homework.get('submissions', []):
        if submission['user_id'] == callback.from_user.id:
            my_submission = submission
            break
    
    if not my_submission:
        await callback.answer("❌ Здачу не знайдено")
        return
    
    response = f"👁 **Моя здача**\n\n"
    response += f"📚 **Предмет:** {homework['subject_name']}\n"
    response += f"📋 **Завдання:** {homework['title']}\n"
    response += f"📅 **Здано:** {my_submission['submitted_at'].strftime('%d.%m.%Y %H:%M')}\n"
    response += f"⏰ **Дедлайн був:** {homework['deadline'].strftime('%d.%m.%Y %H:%M')}\n\n"
    
    # Статус здачі
    if my_submission['submitted_at'] <= homework['deadline']:
        response += "✅ **Статус:** Здано вчасно\n\n"
    else:
        response += "⏰ **Статус:** Здано із запізненням\n\n"
    
    # Файли
    file_ids = my_submission.get('file_ids', [])
    if file_ids:
        response += f"📎 **Файлів здано:** {len(file_ids)}\n"
    
    # Текстова відповідь
    text_answer = my_submission.get('text_answer')
    if text_answer:
        response += f"📝 **Текстова відповідь:** {len(text_answer)} символів\n"
        if len(text_answer) <= 200:
            response += f"💭 *{text_answer}*\n"
        else:
            response += f"💭 *{text_answer[:200]}...*\n"
    
    keyboard = [
        [InlineKeyboardButton(text="◀️ Назад", callback_data="hw_my_submissions")]
    ]
    
    await callback.message.edit_text(
        response,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "hw_back_student")
async def back_to_student_menu(callback: CallbackQuery):
    """Повернення до студентського меню"""
    await my_homework_menu(callback.message)

# Команда для швидкого доступу до ДЗ
@router.message(Command("homework", "дз"), ~F.chat.id.in_({GROUP_ID}))
async def homework_command(message: Message):
    """Команда /homework або /дз для швидкого доступу"""
    await my_homework_menu(message)