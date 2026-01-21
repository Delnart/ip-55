from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated, CallbackQuery
from aiogram.filters import ChatMemberUpdatedFilter, KICKED, LEFT, MEMBER, ADMINISTRATOR, CREATOR, Command
from database.models import GroupMembersManager, LinksManager
from config import GROUP_ID, ADMIN_IDS, TIMEZONE
import logging
from datetime import datetime
import pytz
import asyncio
from aiogram import Bot
from aiogram.enums import ChatMemberStatus


logger = logging.getLogger(__name__)
router = Router()

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED | LEFT))
async def on_user_leave(event: ChatMemberUpdated):
    """Коли користувач покидає групу"""
    if event.chat.id != GROUP_ID:
        return
    
    user = event.new_chat_member.user
    
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

@router.message(F.chat.id == GROUP_ID, Command("schedule", "розклад"))
async def group_schedule_command(message: Message):
    """Обробка команд розкладу в групі з інлайн кнопками"""
    from bot.keyboards.user import get_schedule_inline_keyboard
    
    await message.reply(
        "📅 Оберіть розклад:",
        reply_markup=get_schedule_inline_keyboard()
    )

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

🕒 **Статус пар:**
• `/now` - що зараз за пара
• `/left` - скільки часу до кінця пари

📅 **Розклад:**
• `/next` - розклад на завтра
• `/week` - розклад на наступний тиждень
• `/schedule` або `/розклад` - меню розкладу з кнопками

🔗 **Посилання:**
• `/links` або `/посилання` - всі посилання на пари

📣 **Для адмінів:**
• `/all` (або `@всі`) - пінгувати всіх учасників

❓ **Інше:**
• `/help` або `/допомога` - ця довідка

💡 Для повного функціонала пишіть боту в особисті повідомлення!
    """
    
    await message.reply(help_text)

@router.message(F.chat.id == GROUP_ID, Command("now"))
async def group_now_command(message: Message):
    """Обробка команди /now в групі"""
    from bot.utils.api import ScheduleAPI
    current_class = await ScheduleAPI.get_current_class_info()
    
    if not current_class:
        await message.reply("😌 Зараз пари немає.")
        return
        
    class_info = await ScheduleAPI.format_class_info(current_class)
    response = "🔔 **Зараз йде пара:**\n\n" + class_info
    
    await message.reply(response, parse_mode="Markdown", disable_web_page_preview=True)

@router.message(F.chat.id == GROUP_ID, Command("left"))
async def group_left_command(message: Message):
    """Обробка команди /left в групі"""
    from bot.utils.api import ScheduleAPI
    current_class = await ScheduleAPI.get_current_class_info()
    
    if not current_class or 'end_datetime' not in current_class:
        await message.reply("😌 Зараз пари немає, тому й закінчуватись нічому.")
        return
        
    kiev_tz = pytz.timezone(TIMEZONE)
    now = datetime.now(kiev_tz)
    end_datetime = current_class['end_datetime']
    
    time_left = end_datetime - now
    
    if time_left.total_seconds() <= 0:
        await message.reply("🧐 Пара вже мала закінчитись.")
        return
        
    minutes_left = int(time_left.total_seconds() // 60)
    seconds_left = int(time_left.total_seconds() % 60)
    
    subject_name = current_class.get('name', 'Поточна пара')
    
    await message.reply(
        f"⏳ До кінця пари **{subject_name}** залишилось: **{minutes_left} хв {seconds_left} с**"
    )

@router.message(F.chat.id == GROUP_ID, Command("next"))
async def group_next_command(message: Message):
    """Обробка команди /next (розклад на завтра) в групі"""
    from bot.utils.api import ScheduleAPI
    schedule = await ScheduleAPI.get_tomorrow_schedule()
    await message.reply(schedule, parse_mode="Markdown", disable_web_page_preview=True)

@router.message(F.chat.id == GROUP_ID, Command("week"))
async def group_week_command(message: Message):
    """Обробка команди /week (розклад на наступний тиждень) в групі"""
    from bot.utils.api import ScheduleAPI
    schedule = await ScheduleAPI.get_week_schedule(1) 
    await message.reply(schedule, parse_mode="Markdown", disable_web_page_preview=True)


@router.message(F.chat.id == GROUP_ID, Command("all", "tagall", "everyone"))
async def tag_all_command(message: Message, bot: Bot):
    try:
        member = await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)
        if member.status not in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]:
            await message.reply("❌ Ця команда доступна тільки адміністраторам групи.")
            return
    except Exception as e:
        logger.error(f"Помилка перевірки статусу адміна: {e}")
        await message.reply("❌ Не вдалося перевірити ваші права.")
        return

    members = await GroupMembersManager.get_all_members()
    if not members:
        logger.warning(f"Адмін {message.from_user.id} спробував пінганути, але база учасників порожня.")
        return

    mentions = []
    batch_size = 5 
    
    for member in members:
        user_id = member.get('user_id')

        if not member.get('allow_ping', True):
            continue
        if user_id == bot.id or user_id == message.from_user.id:
            continue

        first_name = member.get('first_name', 'Учасник').strip()
        if not first_name:
            first_name = member.get('username', 'Учасник')
        safe_name = first_name.replace("]", "\\]").replace("[", "\\[").replace("*", "\\*").replace("_", "\\_")
        mention_str = f"[{safe_name}](tg://user?id={user_id})"
        mentions.append(mention_str)
        
        if len(mentions) >= batch_size:
            text = " ".join(mentions)
            try:
                await message.answer(text, parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Не вдалося відправити пачку пінгів: {e}")
            
            mentions = [] 
            await asyncio.sleep(1) 

    if mentions:
        text = " ".join(mentions)
        try:
            await message.answer(text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Не вдалося відправити останню пачку пінгів: {e}")



@router.message(F.chat.id == GROUP_ID, F.text.lower().in_(["@all", "@всі"]))
async def tag_all_text(message: Message, bot: Bot):
    """Обробка текстових команд для пінгу"""
    await tag_all_command(message, bot)

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
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="schedule_back")]
    ])
    
    await callback.message.edit_text(schedule, reply_markup=back_keyboard)
    await callback.answer()

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

@router.message(F.chat.id == GROUP_ID)
async def handle_group_messages(message: Message):
    """Обробка повідомлень у групі"""
    user = message.from_user
    
    if not user:
        return
    
    if user.id in ADMIN_IDS:
        is_member = await GroupMembersManager.is_member(user.id)
        if not is_member:
            await GroupMembersManager.add_member(
                user_id=user.id,
                username=user.username or '',
                first_name=user.first_name or '',
                last_name=user.last_name
            )
        return
    
    is_member = await GroupMembersManager.is_member(user.id)
    
    if not is_member:
        await GroupMembersManager.add_member(
            user_id=user.id,
            username=user.username or '',
            first_name=user.first_name or '',
            last_name=user.last_name
        )
        logger.info(f"Додано учасника з групового повідомлення: {user.username} ({user.id})")

@router.message(Command("test"))
async def test_command(message: Message):
    """
    Тестова команда для перевірки роботи бота.
    Працює усюди, щоб можна було дізнатися ID чату.
    """
    is_correct_group = (message.chat.id == GROUP_ID)
    status_icon = "✅" if is_correct_group else "⚠️"
    
    await message.reply(
        f"🤖 **Бот на зв'язку!**\n\n"
        f"👤 Ти: {message.from_user.full_name}\n"
        f"🆔 ID цього чату: `{message.chat.id}`\n"
        f"⚙️ Налаштований GROUP_ID: `{GROUP_ID}`\n"
        f"{status_icon} Співпадіння: {is_correct_group}"
    )