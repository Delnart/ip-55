import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from database.connection import db
from bot.handlers import admin, schedule, group
from bot.middlewares.auth import AuthMiddleware
from bot.utils.scheduler import NotificationScheduler
from config import BOT_TOKEN, GROUP_ID

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def debug_message(message):
    """Діагностична функція для логування всіх повідомлень"""
    logger.info(f"📨 Повідомлення: '{message.text}' від {message.from_user.username} в чаті {message.chat.id} (тип: {message.chat.type})")
    logger.info(f"🔍 Очікуваний GROUP_ID: {GROUP_ID}")
    logger.info(f"✅ Співпадає: {message.chat.id == GROUP_ID}")

async def main():
    """Головна функція запуску бота"""
    try:
        # Ініціалізація бота
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        
        dp = Dispatcher()
        
        # ДІАГНОСТИКА: Додаємо логування всіх повідомлень
        @dp.message()
        async def log_all_messages(message):
            await debug_message(message)
        
        # Підключення handlers в правильному порядку
        dp.include_router(group.router)  # Групові команди обробляються першими
        
        # Middleware тільки для не-групових повідомлень
        dp.include_router(admin.router)
        admin.router.message.middleware(AuthMiddleware())
        admin.router.callback_query.middleware(AuthMiddleware())
        
        dp.include_router(schedule.router)
        schedule.router.message.middleware(AuthMiddleware())
        schedule.router.callback_query.middleware(AuthMiddleware())
        
        # Підключення до бази даних
        await db.connect()
        logger.info("Підключення до бази даних встановлено")
        
        # Запуск планувальника повідомлень
        scheduler = NotificationScheduler(bot)
        await scheduler.start()
        logger.info("Планувальник повідомлень запущено")
        
        logger.info(f"🔧 Налаштований GROUP_ID: {GROUP_ID}")
        logger.info("🤖 Бот запущено з діагностикою!")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Критична помилка: {e}")
    finally:
        # Відключення від бази даних
        await db.disconnect()
        if 'scheduler' in locals():
            await scheduler.stop()
        logger.info("Бот зупинено")

if __name__ == "__main__":
    asyncio.run(main())