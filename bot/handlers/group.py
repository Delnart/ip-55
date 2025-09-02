from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated, CallbackQuery
from aiogram.filters import ChatMemberUpdatedFilter, KICKED, LEFT, MEMBER, ADMINISTRATOR, CREATOR, Command
from database.models import GroupMembersManager
from config import GROUP_ID, ADMIN_ID
import logging

logger = logging.getLogger(__name__)
router = Router()

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

@router.message(F.chat.id == GROUP_ID)
async def handle_group_messages(message: Message):
    """Обробка повідомлень у групі"""
    user = message.from_user
    
    if not user:
        return
    
    # Якщо це адмін - не обробляємо автоматично, але додаємо до бази
    if user.id == ADMIN_ID:
        # Додаємо адміна до бази якщо його немає
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

@router.message(F.chat.id == GROUP_ID, Command("schedule", "розклад"))
async def group_schedule_command(message: Message):
    """Обробка команд розкладу в групі з інлайн кнопками"""
    from bot.keyboards.user import get_schedule_inline_keyboard
    
    await message.reply(
        "📅 Оберіть розклад:",
        reply_markup=get_schedule_inline_keyboard()
    )

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

@router.message(F.chat.id == GROUP_ID, Command("links", "посилання"))
async def group_links_command(message: Message):
    """Команда отримання посилань у групі"""
    from database.models import LinksManager
    
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

@router.message(F.chat.id == GROUP_ID, Command("help"))
async def group_help_command(message: Message):
    """Команда допомоги в групі"""
    help_text = """
📖 **Команди бота в групі:**

📅 **Розклад:**
• `/schedule` або `/розклад` - меню розкладу з кнопками
• Можна також писати:
  - `/schedule сьогодні` - розклад на сьогодні
  - `/schedule завтра` - розклад на завтра
  - `/schedule тиждень` - поточний тиждень
  - `/schedule наступний тиждень` - наступний тиждень

🔗 **Посилання:**
• `/links` або `/посилання` - всі посилання на пари

❓ **Інше:**
• `/help` - ця довідка

💡 Для повного функціонала пишіть боту в особисті повідомлення!
    """
    
    await message.reply(help_text)

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