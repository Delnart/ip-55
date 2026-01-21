from aiogram import Router, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import WEBAPP_URL

router = Router()

@router.message(Command("app", "webapp"))
async def cmd_webapp(message: Message):
    """Команда /app працює і в ЛС, і в групах"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Відкрити додаток",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]
    ])
    
    await message.answer(
        "🎓 **Університетський помічник**\n\n"
        "Натисніть кнопку нижче, щоб відкрити додаток:",
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
        "👥 **Черги на здачу**",
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
        "📚 **Теми рефератів**",
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
        "📝 **Домашні завдання**",
        reply_markup=keyboard
    )