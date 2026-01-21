import asyncio
import logging
import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Імпортуємо router з api/routes.py
from api.routes import router as api_router 
from database.connection import db
from bot.handlers import admin, schedule, group, webapp
from bot.middlewares.auth import AuthMiddleware
from bot.utils.scheduler import NotificationScheduler
from config import BOT_TOKEN, GROUP_ID

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ініціалізація бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# Підключаємо роутери бота
dp.include_router(webapp.router)
dp.include_router(admin.router)
admin.router.message.middleware(AuthMiddleware())
admin.router.callback_query.middleware(AuthMiddleware())
dp.include_router(group.router)
dp.include_router(schedule.router)
schedule.router.message.middleware(AuthMiddleware())
schedule.router.callback_query.middleware(AuthMiddleware())

# --- Налаштування Web (FastAPI + React) ---
app = FastAPI()

# Додаємо CORS для уникнення проблем з доступом (опціонально, але корисно)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ПІДКЛЮЧАЄМО API РОУТЕР З ПРЕФІКСОМ /api
# Це найважливіша частина: запит /api/subjects тепер піде сюди
app.include_router(api_router, prefix="/api")

# Монтуємо папку webapp як статичні файли
if os.path.exists("webapp"):
    app.mount("/", StaticFiles(directory="webapp", html=True), name="webapp")
else:
    logger.error("Папка 'webapp' не знайдена!")

# Події старту
@app.on_event("startup")
async def on_startup():
    await db.connect()
    logger.info("БД підключено")
    
    # Запуск планувальника
    scheduler = NotificationScheduler(bot)
    await scheduler.start()
    
    # Запуск бота в фоновому режимі (polling)
    asyncio.create_task(dp.start_polling(bot))
    logger.info("Бот запущено в фоні")

@app.on_event("shutdown")
async def on_shutdown():
    await db.disconnect()
    logger.info("Бот зупинено")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)