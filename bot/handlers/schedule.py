from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from bot.utils.api import ScheduleAPI
from bot.keyboards.user import get_schedule_inline_keyboard, get_main_keyboard
from database.models import LinksManager
from config import GROUP_ID
from database.models import LinksManager, SettingsManager
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, is_admin: bool):
    """Обробка команди /start (тільки в приватних повідомленнях)"""
    if message.chat.id == GROUP_ID:
        return
        
    welcome_text = "👋 Привіт! Я бот-помічник для твоєї групи.\n\n"
    
    if is_admin:
        welcome_text += "🔧 Ви маєте права адміністратора.\n"
        welcome_text += "Використовуйте /admin для доступу до панелі управління.\n\n"
    
    welcome_text += "📚 Доступні команди:\n"
    welcome_text += "• Розклад на сьогодні/завтра\n"
    welcome_text += "• Розклад на поточний/наступний тиждень\n"
    welcome_text += "• Посилання на пари\n\n"
    welcome_text += "Використовуйте кнопки нижче або команди в меню."
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@router.message(Command("help"), ~F.chat.id.in_({GROUP_ID}))
async def cmd_help(message: Message):
    """Обробка команди /help в приватних повідомленнях"""
    help_text = """
📖 Довідка по боту:

📅 **Розклад:**
• "Розклад на сьогодні" - пари на поточний день
• "Розклад на завтра" - пари на завтрашній день  
• "Поточний тиждень" - розклад на весь поточний тиждень
• "Наступний тиждень" - розклад на наступний тиждень

🔗 **Посилання:**
• "Посилання на пари" - отримати всі збережені посилання
• Бот автоматично надсилає посилання за 10 хвилин до початку пари

⏰ **Автоматичні повідомлення:**
Бот надсилає в групу посилання на зустрічі за 10 хвилин до початку кожної пари.

❓ Якщо виникли питання, зверніться до адміністратора групи.
    """
    
    await message.answer(help_text)

@router.message(F.text == "📅 Розклад на сьогодні", ~F.chat.id.in_({GROUP_ID}))
async def get_today_schedule(message: Message):
    """Розклад на сьогодні (тільки приватні повідомлення)"""
    schedule = await ScheduleAPI.get_today_schedule()
    await message.answer(schedule)

@router.message(F.text == "📅 Розклад на завтра", ~F.chat.id.in_({GROUP_ID}))  
async def get_tomorrow_schedule(message: Message):
    """Розклад на завтра (тільки приватні повідомлення)"""
    schedule = await ScheduleAPI.get_tomorrow_schedule()
    await message.answer(schedule)

@router.message(F.text == "📄 Поточний тиждень", ~F.chat.id.in_({GROUP_ID}))
async def get_current_week_schedule(message: Message):
    """Розклад на поточний тиждень (тільки приватні повідомлення)"""
    schedule = await ScheduleAPI.get_week_schedule(0)
    await message.answer(schedule)

@router.message(F.text == "📄 Наступний тиждень", ~F.chat.id.in_({GROUP_ID}))
async def get_next_week_schedule(message: Message):
    """Розклад на наступний тиждень (тільки приватні повідомлення)"""
    schedule = await ScheduleAPI.get_week_schedule(1)
    await message.answer(schedule)

@router.message(F.text == "🔗 Посилання на пари", ~F.chat.id.in_({GROUP_ID}))
async def get_all_links(message: Message):
    """Отримання всіх посилань на пари (тільки приватні повідомлення)"""
    links = await LinksManager.get_all_links()
    
    if not links:
        await message.answer("📭 Посилання на пари ще не додано.")
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
        response += f"🔗 [Приєднатися до зустрічі]({meet_link})\n"
        
        if classroom_link:
            response += f"📖 [Google Classroom]({classroom_link})\n"
        
        response += "\n"
    
    await message.answer(response, parse_mode="Markdown", disable_web_page_preview=True)

@router.callback_query(F.data.startswith("schedule_"), ~F.message.chat.id.in_({GROUP_ID}))
async def process_schedule_callback(callback: CallbackQuery):
    """Обробка інлайн кнопок розкладу в приватних повідомленнях"""
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

@router.message(Command("schedule"), ~F.chat.id.in_({GROUP_ID}))
async def cmd_schedule(message: Message):
    """Команда /schedule з інлайн кнопками в приватних повідомленнях"""
    await message.answer(
        "📅 Оберіть розклад:",
        reply_markup=get_schedule_inline_keyboard()
    )