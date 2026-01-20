from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None
    
    async def connect(self):
        """Підключення до MongoDB"""
        try:
            self.client = AsyncIOMotorClient(MONGODB_URL)
            self.db = self.client.university_bot
            
            await self.client.admin.command('ismaster')
            logger.info("Успішно підключено до MongoDB")
            
            await self.create_indexes()
            
        except Exception as e:
            logger.error(f"Помилка підключення до MongoDB: {e}")
            raise
    
    async def create_indexes(self):
        """Створення індексів для оптимізації"""
        try:
            await self.db.links.create_index([
                ("subject_name", 1),
                ("teacher_name", 1),
                ("class_type", 1)
            ], unique=True)
            
            await self.db.group_members.create_index("user_id", unique=True)
            
            logger.info("Індекси створено успішно")
            
        except Exception as e:
            logger.error(f"Помилка створення індексів: {e}")
    
    async def disconnect(self):
        """Відключення від MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Відключено від MongoDB")

db = Database()