import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from database.connection import db
from bot.handlers import admin, schedule, group
from bot.middlewares.auth import AuthMiddleware
from bot.utils.scheduler import NotificationScheduler
from config import BOT_TOKEN

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

async def main():
    """Головна функція запуску бота"""
    try:
        # Ініціалізація бота
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        
        dp = Dispatcher()
        
        # Підключення middleware
        dp.message.middleware(AuthMiddleware())
        dp.callback_query.middleware(AuthMiddleware())
        
        # Підключення handlers
        dp.include_router(admin.router)
        dp.include_router(schedule.router)
        dp.include_router(group.router)
        
        # Підключення до бази даних
        await db.connect()
        logger.info("Підключення до бази даних встановлено")
        
        # Запуск планувальника повідомлень
        scheduler = NotificationScheduler(bot)
        await scheduler.start()
        logger.info("Планувальник повідомлень запущено")
        
        # Запуск бота
        logger.info("Бот запущено!")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Критична помилка: {e}")
    finally:
        # Відключення від бази даних
        await db.disconnect()
        logger.info("Бот зупинено")

if __name__ == "__main__":
    asyncio.run(main())