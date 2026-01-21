from aiogram import Router, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import GROUP_ID

router = Router()

WEBAPP_URL = "https://your-mini-app-url.com"

@router.message(Command("app", "webapp"))
async def cmd_webapp(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Відкрити додаток",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]
    ])
    
    await message.answer(
        "🎓 **Університетський помічник**\n\n"
        "Відкрийте міні-додаток для доступу до:\n"
        "• 📅 Розкладу занять\n"
        "• 👥 Черг на здачу лаб\n"
        "• 📚 Тем рефератів\n"
        "• 📝 Домашніх завдань",
        reply_markup=keyboard
    )

@router.message(Command("queues"))
async def cmd_queues(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="👥 Відкрити черги",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?tab=queues")
        )]
    ])
    
    await message.answer(
        "👥 **Черги на здачу**\n\n"
        "Переглядайте та записуйтесь в черги на здачу лабораторних робіт",
        reply_markup=keyboard
    )

@router.message(Command("topics"))
async def cmd_topics(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📚 Відкрити теми",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?tab=topics")
        )]
    ])
    
    await message.answer(
        "📚 **Теми рефератів**\n\n"
        "Виберіть тему для реферату або презентації",
        reply_markup=keyboard
    )

@router.message(Command("hw", "homework"))
async def cmd_homework(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📝 Відкрити домашку",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?tab=homework")
        )]
    ])
    
    await message.answer(
        "📝 **Домашні завдання**\n\n"
        "Переглядайте та додавайте домашні завдання",
        reply_markup=keyboard
    )

@router.message(F.chat.id == GROUP_ID, Command("app", "webapp"))
async def group_webapp(message: Message):
    await cmd_webapp(message)