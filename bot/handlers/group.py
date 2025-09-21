from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated, CallbackQuery
from aiogram.filters import ChatMemberUpdatedFilter, KICKED, LEFT, MEMBER, ADMINISTRATOR, CREATOR, Command
from database.models import GroupMembersManager, LinksManager
from config import GROUP_ID, ADMIN_ID, TIMEZONE, CLASS_TYPES  # ДОДАНО CLASS_TYPES
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)
router = Router()

# Розклад пар з точними часами
CLASS_SCHEDULE = {
    1: {"start": "08:30", "end": "10:05", "break_start": "09:15", "break_end": "09:20"},
    2: {"start": "10:25", "end": "12:00", "break_start": "11:10", "break_end": "11:15"},
    3: {"start": "12:20", "end": "13:55", "break_start": "13:05", "break_end": "13:10"},
    4: {"start": "14:15", "end": "15:50", "break_start": "15:00", "break_end": "15:05"},
    5: {"start": "16:10", "end": "17:45", "break_start": "16:55", "break_end": "17:00"},
    6: {"start": "18:05", "end": "19:40", "break_start": "18:50", "break_end": "18:55"},
    7: {"start": "20:00", "end": "21:35", "break_start": "20:45", "break_end": "20:50"}
}

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED | LEFT))
async def on_user_leave(event: ChatMemberUpdated):
    """Коли користувач покидає групу"""
    if event.chat.id != GROUP_ID:
        return
    
    user = event.new_chat_member.user
    
    # Деактивуємо користувача в базі даних
    success = await GroupMembersManager.remove_member(user.id)
    
    if success:
        logger.info(f"Користувач покинув групу: {user.username} ({user.id})")
    else:
        logger.warning(f"Не вдалося деактивувати користувача: {user.id}")

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER | ADMINISTRATOR | CREATOR))
async def on_user_join(event: ChatMemberUpdated):
    """Коли користувач приєднується до групи"""
    if event.chat.id != GROUP_ID:
        return
    
    user = event.new_chat_member.user
    
    # Додаємо користувача до бази даних
    success = await GroupMembersManager.add_member(
        user_id=user.id,
        username=user.username or '',
        first_name=user.first_name or '',
        last_name=user.last_name
    )
    
    if success:
        logger.info(f"Новий учасник додан до групи: {user.username} ({user.id})")
    else:
        logger.warning(f"Не вдалося додати користувача до бази: {user.id}")

# ВИПРАВЛЕННЯ 1: Додаємо обробку команд з українськими назвами
@router.message(F.chat.id == GROUP_ID, Command("schedule", "розклад"))
async def group_schedule_command(message: Message):
    """Обробка команд розкладу в групі з інлайн кнопками"""
    from bot.keyboards.user import get_schedule_inline_keyboard
    
    await message.reply(
        "📅 Оберіть розклад:",
        reply_markup=get_schedule_inline_keyboard()
    )

# ВИПРАВЛЕННЯ 2: Додаємо команду /посилання як альтернативу до /links
@router.message(F.chat.id == GROUP_ID, Command("links", "посилання"))
async def group_links_command(message: Message):
    """Команда отримання посилань у групі (працює з /links та /посилання)"""
    links = await LinksManager.get_all_links()
    
    if not links:
        await message.reply("📭 Посилання на пари ще не додано.")
        return
    
    response = "🔗 **Посилання на пари:**\n\n"
    
    for link in links:
        subject = link.get('subject_name', 'Невідомий предмет')
        teacher = link.get('teacher_name', 'Невідомий викладач')
        class_type = link.get('class_type', '')
        meet_link = link.get('meet_link', '')
        classroom_link = link.get('classroom_link')
        
        response += f"📚 **{subject}**\n"
        response += f"👨‍🏫 {teacher} ({class_type})\n"
        response += f"🔗 [Приєднатися]({meet_link})\n"
        
        if classroom_link:
            response += f"📖 [Classroom]({classroom_link})\n"
        
        response += "\n"
    
    await message.reply(response, parse_mode="Markdown", disable_web_page_preview=True)

@router.message(F.chat.id == GROUP_ID, Command("help", "допомога"))
async def group_help_command(message: Message):
    """Команда допомоги в групі (працює з /help та /допомога)"""
    help_text = """
📖 **Команди бота в групі:**

📅 **Розклад:**
• `/schedule` або `/розклад` - меню розкладу з кнопками

🔗 **Посилання:**
• `/links` або `/посилання` - всі посилання на пари

❓ **Інше:**
• `/help` або `/допомога` - ця довідка

💡 Для повного функціонала пишіть боту в особисті повідомлення!
    """
    
    await message.reply(help_text)

# ВИПРАВЛЕННЯ 3: Додаємо обробку текстових команд без слешу
@router.message(F.chat.id == GROUP_ID, F.text.lower().in_(["посилання", "ссылки", "links"]))
async def group_links_text(message: Message):
    """Обробка текстових команд для посилань"""
    await group_links_command(message)

@router.message(F.chat.id == GROUP_ID, F.text.lower().in_(["розклад", "расписание", "schedule"]))
async def group_schedule_text(message: Message):
    """Обробка текстових команд для розкладу"""
    await group_schedule_command(message)

@router.message(F.chat.id == GROUP_ID, F.text.lower().in_(["допомога", "помощь", "help"]))
async def group_help_text(message: Message):
    """Обробка текстових команд для допомоги"""
    await group_help_command(message)

# Обробка інлайн кнопок для розкладу в групі
@router.callback_query(F.data.startswith("schedule_"), F.message.chat.id == GROUP_ID)
async def process_group_schedule_callback(callback: CallbackQuery):
    """Обробка інлайн кнопок розкладу в групі"""
    from bot.utils.api import ScheduleAPI
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    action = callback.data.replace("schedule_", "")
    
    if action == "today":
        schedule = await ScheduleAPI.get_today_schedule()
    elif action == "tomorrow":
        schedule = await ScheduleAPI.get_tomorrow_schedule()
    elif action == "current_week":
        schedule = await ScheduleAPI.get_week_schedule(0)
    elif action == "next_week":
        schedule = await ScheduleAPI.get_week_schedule(1)
    elif action == "back":
        from bot.keyboards.user import get_schedule_inline_keyboard
        await callback.message.edit_text(
            "📅 Оберіть розклад:",
            reply_markup=get_schedule_inline_keyboard()
        )
        await callback.answer()
        return
    else:
        await callback.answer("❌ Невідома команда")
        return
    
    # Створюємо клавіатуру з кнопкою "Назад"
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="schedule_back")]
    ])
    
    await callback.message.edit_text(schedule, reply_markup=back_keyboard)
    await callback.answer()

# Додаткові команди з текстом (для зворотної сумісності)
@router.message(F.chat.id == GROUP_ID, F.text.contains("сьогодні"))
async def group_today_schedule(message: Message):
    """Розклад на сьогодні через текст"""
    if any(word in message.text.lower() for word in ['/schedule', '/розклад', 'розклад']):
        from bot.utils.api import ScheduleAPI
        schedule = await ScheduleAPI.get_today_schedule()
        await message.reply(schedule)

@router.message(F.chat.id == GROUP_ID, F.text.contains("завтра"))
async def group_tomorrow_schedule(message: Message):
    """Розклад на завтра через текст"""
    if any(word in message.text.lower() for word in ['/schedule', '/розклад', 'розклад']):
        from bot.utils.api import ScheduleAPI
        schedule = await ScheduleAPI.get_tomorrow_schedule()
        await message.reply(schedule)

@router.message(F.chat.id == GROUP_ID, F.text.contains("тиждень"))
async def group_week_schedule(message: Message):
    """Розклад на тиждень через текст"""
    if any(word in message.text.lower() for word in ['/schedule', '/розклад', 'розклад']):
        from bot.utils.api import ScheduleAPI
        if "наступ" in message.text.lower() or "next" in message.text.lower():
            schedule = await ScheduleAPI.get_week_schedule(1)
        else:
            schedule = await ScheduleAPI.get_week_schedule(0)
        await message.reply(schedule)

# ВИПРАВЛЕННЯ 4: Обробка всіх повідомлень у групі (для автоматичного додавання користувачів)
@router.message(F.chat.id == GROUP_ID)
async def handle_group_messages(message: Message):
    """Обробка повідомлень у групі"""
    user = message.from_user
    
    if not user:
        return
    
    # Якщо це адмін - додаємо до бази якщо його немає
    if user.id == ADMIN_ID:
        is_member = await GroupMembersManager.is_member(user.id)
        if not is_member:
            await GroupMembersManager.add_member(
                user_id=user.id,
                username=user.username or '',
                first_name=user.first_name or '',
                last_name=user.last_name
            )
        return
    
    # Перевіряємо чи користувач є в базі даних
    is_member = await GroupMembersManager.is_member(user.id)
    
    if not is_member:
        # Додаємо користувача до бази
        await GroupMembersManager.add_member(
            user_id=user.id,
            username=user.username or '',
            first_name=user.first_name or '',
            last_name=user.last_name
        )
        logger.info(f"Додано учасника з групового повідомлення: {user.username} ({user.id})")

# ВИПРАВЛЕННЯ 5: Додаємо тестову команду для діагностики
@router.message(F.chat.id == GROUP_ID, Command("test"))
async def test_command(message: Message):
    """Тестова команда для перевірки роботи бота в групі"""
    await message.reply(
        f"✅ Бот працює в групі!\n"
        f"👤 Користувач: {message.from_user.first_name}\n"
        f"🆔 ID групи: {message.chat.id}\n"
        f"🤖 Відповідь від бота"
    )




def get_current_time():
    """Отримання поточного часу в київській зоні"""
    kiev_tz = pytz.timezone(TIMEZONE)
    return datetime.now(kiev_tz)

def time_from_string(time_str):
    """Конвертація рядка часу в datetime об'єкт"""
    hour, minute = map(int, time_str.split(':'))
    current = get_current_time()
    return current.replace(hour=hour, minute=minute, second=0, microsecond=0)

async def get_current_class_info():
    """Отримання інформації про поточну пару"""
    from bot.utils.api import ScheduleAPI
    
    current_time = get_current_time()
    current_time_str = current_time.strftime('%H:%M')
    
    # Отримуємо розклад на сьогодні
    schedule_data = await ScheduleAPI.get_schedule()
    if not schedule_data:
        return None, None
    
    # Визначаємо поточний день та тиждень
    today = current_time.strftime('%A')
    week_number = ScheduleAPI.get_week_number(current_time)
    week_key = 'scheduleFirstWeek' if week_number == 1 else 'scheduleSecondWeek'
    
    day_mapping = {
        'Monday': 'Пн',
        'Tuesday': 'Вв',
        'Wednesday': 'Ср',
        'Thursday': 'Чт',
        'Friday': 'Пт',
        'Saturday': 'Сб'
    }
    
    day_code = day_mapping.get(today)
    if not day_code:
        return None, None
    
    # Знаходимо розклад на сьогодні
    week_schedule = schedule_data.get(week_key, [])
    today_classes = None
    
    for day_data in week_schedule:
        if day_data.get('day') == day_code:
            today_classes = day_data.get('pairs', [])
            break
    
    if not today_classes:
        return None, None
    
    # Знаходимо поточну пару
    for i, class_data in enumerate(today_classes, 1):
        if i in CLASS_SCHEDULE:
            class_start = time_from_string(CLASS_SCHEDULE[i]["start"])
            class_end = time_from_string(CLASS_SCHEDULE[i]["end"])
            
            if class_start <= current_time <= class_end:
                return class_data, i
    
    return None, None

async def get_next_class_info():
    """Отримання інформації про наступну пару"""
    from bot.utils.api import ScheduleAPI
    
    current_time = get_current_time()
    
    # Спочатку перевіряємо сьогодні
    schedule_data = await ScheduleAPI.get_schedule()
    if not schedule_data:
        return None, None, None
    
    # Сьогоднішній розклад
    today = current_time.strftime('%A')
    week_number = ScheduleAPI.get_week_number(current_time)
    week_key = 'scheduleFirstWeek' if week_number == 1 else 'scheduleSecondWeek'
    
    day_mapping = {
        'Monday': 'Пн',
        'Tuesday': 'Вв', 
        'Wednesday': 'Ср',
        'Thursday': 'Чт',
        'Friday': 'Пт',
        'Saturday': 'Сб'
    }
    
    day_code = day_mapping.get(today)
    if day_code:
        week_schedule = schedule_data.get(week_key, [])
        for day_data in week_schedule:
            if day_data.get('day') == day_code:
                today_classes = day_data.get('pairs', [])
                
                # Шукаємо наступну пару сьогодні
                for i, class_data in enumerate(today_classes, 1):
                    if i in CLASS_SCHEDULE:
                        class_start = time_from_string(CLASS_SCHEDULE[i]["start"])
                        if class_start > current_time:
                            return class_data, i, "сьогодні"
                break
    
    # Якщо сьогодні наступних пар немає, шукаємо завтра
    tomorrow = current_time + timedelta(days=1)
    tomorrow_day = tomorrow.strftime('%A')
    tomorrow_week_number = ScheduleAPI.get_week_number(tomorrow)
    tomorrow_week_key = 'scheduleFirstWeek' if tomorrow_week_number == 1 else 'scheduleSecondWeek'
    
    if tomorrow_day == 'Sunday':  # Якщо завтра неділя, шукаємо понеділок
        tomorrow = tomorrow + timedelta(days=1)
        tomorrow_day = 'Monday'
        tomorrow_week_number = ScheduleAPI.get_week_number(tomorrow)
        tomorrow_week_key = 'scheduleFirstWeek' if tomorrow_week_number == 1 else 'scheduleSecondWeek'
    
    tomorrow_day_code = day_mapping.get(tomorrow_day)
    if tomorrow_day_code:
        tomorrow_schedule = schedule_data.get(tomorrow_week_key, [])
        for day_data in tomorrow_schedule:
            if day_data.get('day') == tomorrow_day_code:
                tomorrow_classes = day_data.get('pairs', [])
                if tomorrow_classes:
                    return tomorrow_classes[0], 1, "завтра"
                break
    
    return None, None, None

# НОВІ КОМАНДИ ДЛЯ ГРУПИ

@router.message(F.chat.id == GROUP_ID, Command("now", "зараз"))
async def group_current_class(message: Message):
    """Команда /now - поточна пара"""
    class_data, class_number = await get_current_class_info()
    
    if not class_data:
        await message.reply("📭 Зараз пар немає")
        return
    
    subject = class_data.get('name', '')
    teacher = class_data.get('teacherName', '')
    class_type = CLASS_TYPES.get(class_data.get('type', ''), class_data.get('type', ''))
    place = class_data.get('place', '')
    
    schedule_info = CLASS_SCHEDULE[class_number]
    
    response = f"📚 **Поточна пара ({class_number}-а):**\n\n"
    response += f"📖 **Предмет:** {subject}\n"
    response += f"👨‍🏫 **Викладач:** {teacher}\n"
    response += f"📝 **Тип:** {class_type}\n"
    response += f"⏰ **Час:** {schedule_info['start']} - {schedule_info['end']}\n"
    
    if place:
        response += f"📍 **Місце:** {place}\n"
    
    # Додаємо посилання якщо є
    from database.models import LinksManager
    link_data = await LinksManager.get_link(subject, teacher, class_data.get('type', ''))
    
    if link_data:
        meet_link = link_data.get('meet_link')
        classroom_link = link_data.get('classroom_link')
        
        if meet_link:
            response += f"🔗 [Приєднатися]({meet_link})\n"
        
        if classroom_link:
            response += f"📖 [Classroom]({classroom_link})\n"
    
    await message.reply(response, parse_mode="Markdown", disable_web_page_preview=True)

@router.message(F.chat.id == GROUP_ID, Command("next", "наступна"))
async def group_next_class(message: Message):
    """Команда /next - наступна пара"""
    class_data, class_number, when = await get_next_class_info()
    
    if not class_data:
        await message.reply("📭 Наступних пар не знайдено")
        return
    
    subject = class_data.get('name', '')
    teacher = class_data.get('teacherName', '')
    class_type = CLASS_TYPES.get(class_data.get('type', ''), class_data.get('type', ''))
    place = class_data.get('place', '')
    
    schedule_info = CLASS_SCHEDULE[class_number]
    
    response = f"📚 **Наступна пара ({when}):**\n\n"
    response += f"📖 **Предмет:** {subject}\n"
    response += f"👨‍🏫 **Викладач:** {teacher}\n"
    response += f"📝 **Тип:** {class_type}\n"
    response += f"⏰ **Час:** {schedule_info['start']} - {schedule_info['end']}\n"
    
    if place:
        response += f"📍 **Місце:** {place}\n"
    
    # Додаємо посилання якщо є
    from database.models import LinksManager
    link_data = await LinksManager.get_link(subject, teacher, class_data.get('type', ''))
    
    if link_data:
        meet_link = link_data.get('meet_link')
        classroom_link = link_data.get('classroom_link')
        
        if meet_link:
            response += f"🔗 [Приєднатися]({meet_link})\n"
        
        if classroom_link:
            response += f"📖 [Classroom]({classroom_link})\n"
    
    await message.reply(response, parse_mode="Markdown", disable_web_page_preview=True)

@router.message(F.chat.id == GROUP_ID, Command("left", "залишилось"))
async def group_time_left(message: Message):
    """Команда /left - скільки залишилось до кінця пари"""
    class_data, class_number = await get_current_class_info()
    
    if not class_data:
        await message.reply("📭 Зараз пар немає")
        return
    
    current_time = get_current_time()
    schedule_info = CLASS_SCHEDULE[class_number]
    
    # Перевіряємо чи зараз перерва
    break_start = time_from_string(schedule_info["break_start"])
    break_end = time_from_string(schedule_info["break_end"])
    class_end = time_from_string(schedule_info["end"])
    
    subject = class_data.get('name', '')
    
    if break_start <= current_time <= break_end:
        # Зараз перерва
        time_left = (break_end - current_time).total_seconds()
        minutes = int(time_left // 60)
        seconds = int(time_left % 60)
        
        response = f"☕️ **Зараз перерва на парі:**\n"
        response += f"📖 {subject}\n\n"
        response += f"⏰ До кінця перерви: {minutes}хв {seconds}с"
    else:
        # Йде пара
        time_left = (class_end - current_time).total_seconds()
        minutes = int(time_left // 60)
        seconds = int(time_left % 60)
        
        response = f"📚 **Поточна пара:**\n"
        response += f"📖 {subject}\n\n"
        response += f"⏰ До кінця пари: {minutes}хв {seconds}с"
    
    await message.reply(response)

@router.message(F.chat.id == GROUP_ID, Command("today", "сьогодні"))
async def group_today_command(message: Message):
    """Команда /today - розклад на сьогодні в групі"""
    from bot.utils.api import ScheduleAPI
    schedule = await ScheduleAPI.get_today_schedule()
    await message.reply(schedule)

@router.message(F.chat.id == GROUP_ID, Command("tomorrow", "завтра"))
async def group_tomorrow_command(message: Message):
    """Команда /tomorrow - розклад на завтра в групі"""
    from bot.utils.api import ScheduleAPI
    schedule = await ScheduleAPI.get_tomorrow_schedule()
    await message.reply(schedule)