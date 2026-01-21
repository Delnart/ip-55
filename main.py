import asyncio
import logging
import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from api.routes import app 
from database.connection import db
from bot.handlers import admin, schedule, group, webapp
from bot.middlewares.auth import AuthMiddleware
from bot.utils.scheduler import NotificationScheduler
from config import BOT_TOKEN, GROUP_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

dp.include_router(webapp.router)
dp.include_router(admin.router)
admin.router.message.middleware(AuthMiddleware())
admin.router.callback_query.middleware(AuthMiddleware())
dp.include_router(group.router)
dp.include_router(schedule.router)
schedule.router.message.middleware(AuthMiddleware())
schedule.router.callback_query.middleware(AuthMiddleware())

app.mount("/static", StaticFiles(directory="webapp"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('webapp/index.html')

@app.on_event("startup")
async def on_startup():
    await db.connect()
    logger.info("БД підключено")
    scheduler = NotificationScheduler(bot)
    await scheduler.start()
    asyncio.create_task(dp.start_polling(bot))
    logger.info("Бот запущено в фоні")

@app.on_event("shutdown")
async def on_shutdown():
    await db.disconnect()
    logger.info("Бот зупинено")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)