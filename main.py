import asyncio
import logging
import sys
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from database.connection import db
from bot.handlers import admin, schedule, group
from bot.middlewares.auth import AuthMiddleware
from bot.utils.scheduler import NotificationScheduler
from config import BOT_TOKEN, GROUP_ID

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def debug_message(message):
    """Діагностична функція для логування всіх повідомлень"""
    logger.info(f"MESSAGE: '{message.text}' from {message.from_user.username} in chat {message.chat.id} (type: {message.chat.type})")
    logger.info(f"EXPECTED GROUP_ID: {GROUP_ID}")
    logger.info(f"MATCH: {message.chat.id == GROUP_ID}")
    
    print(f"\n=== ПОВІДОМЛЕННЯ ===")
    print(f"Текст: {message.text}")
    print(f"Chat ID: {message.chat.id}")
    print(f"Очікуваний GROUP_ID: {GROUP_ID}")
    print(f"Співпадає: {message.chat.id == GROUP_ID}")
    print(f"Тип чату: {message.chat.type}")
    print("===================\n")

async def handle(request):
    return web.Response(text="Bot is running!")
async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def main():
    """Головна функція запуску бота"""
    try:
        await start_web_server()
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        
        dp = Dispatcher()
        
        dp.include_router(group.router)  
        dp.include_router(admin.router)
        admin.router.message.middleware(AuthMiddleware())
        admin.router.callback_query.middleware(AuthMiddleware())
        
        dp.include_router(schedule.router)
        schedule.router.message.middleware(AuthMiddleware())
        schedule.router.callback_query.middleware(AuthMiddleware())
        
        await db.connect()
        logger.info("Підключення до бази даних встановлено")
        
        scheduler = NotificationScheduler(bot)
        await scheduler.start()
        logger.info("Планувальник повідомлень запущено")
        
        logger.info(f"Налаштований GROUP_ID: {GROUP_ID}")
        logger.info("Бот запущено!")
        
        bot_info = await bot.get_me()
        logger.info(f"Бот: @{bot_info.username}")
        
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Критична помилка: {e}")
    finally:
        await db.disconnect()
        if 'scheduler' in locals():
            await scheduler.stop()
        logger.info("Бот зупинено")

if __name__ == "__main__":
    asyncio.run(main())