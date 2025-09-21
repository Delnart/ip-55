# database/homework.py - НОВИЙ ФАЙЛ

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from .connection import db
import logging

logger = logging.getLogger(__name__)

class HomeworkManager:
    """Клас для роботи з домашніми завданнями"""
    
    @staticmethod
    async def create_homework(subject_name: str, title: str, description: str, 
                            deadline: datetime, created_by: int) -> Optional[str]:
        """Створення нового домашнього завдання"""
        try:
            homework_data = {
                "subject_name": subject_name,
                "title": title,
                "description": description,
                "deadline": deadline,
                "created_by": created_by,
                "created_at": datetime.utcnow(),
                "is_active": True,
                "submissions": []  # Список здачі
            }
            
            result = await db.db.homework.insert_one(homework_data)
            homework_id = str(result.inserted_id)
            
            logger.info(f"Створено нове ДЗ: {title} по {subject_name}")
            return homework_id
            
        except Exception as e:
            logger.error(f"Помилка створення ДЗ: {e}")
            return None
    
    @staticmethod
    async def get_active_homework() -> List[Dict[str, Any]]:
        """Отримання всіх активних домашніх завдань"""
        try:
            cursor = db.db.homework.find({
                "is_active": True,
                "deadline": {"$gte": datetime.utcnow()}
            }).sort("deadline", 1)
            
            homework_list = await cursor.to_list(length=None)
            return homework_list
        except Exception as e:
            logger.error(f"Помилка отримання активних ДЗ: {e}")
            return []
    
    @staticmethod
    async def get_homework_by_id(homework_id: str) -> Optional[Dict[str, Any]]:
        """Отримання ДЗ по ID"""
        try:
            from bson import ObjectId
            homework = await db.db.homework.find_one({"_id": ObjectId(homework_id)})
            return homework
        except Exception as e:
            logger.error(f"Помилка отримання ДЗ по ID: {e}")
            return None
    
    @staticmethod
    async def submit_homework(homework_id: str, user_id: int, username: str, 
                            full_name: str, file_ids: List[str] = None, 
                            text_answer: str = None) -> bool:
        """Здача домашнього завдання"""
        try:
            from bson import ObjectId
            
            submission_data = {
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "submitted_at": datetime.utcnow(),
                "file_ids": file_ids or [],
                "text_answer": text_answer,
                "status": "submitted"
            }
            
            # Перевіряємо чи вже здавав
            homework = await db.db.homework.find_one({"_id": ObjectId(homework_id)})
            if not homework:
                return False
            
            # Видаляємо попередню здачу якщо є
            await db.db.homework.update_one(
                {"_id": ObjectId(homework_id)},
                {"$pull": {"submissions": {"user_id": user_id}}}
            )
            
            # Додаємо нову здачу
            result = await db.db.homework.update_one(
                {"_id": ObjectId(homework_id)},
                {"$push": {"submissions": submission_data}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Помилка здачі ДЗ: {e}")
            return False
    
    @staticmethod
    async def get_user_submissions(user_id: int) -> List[Dict[str, Any]]:
        """Отримання всіх здач користувача"""
        try:
            cursor = db.db.homework.find({
                "submissions.user_id": user_id,
                "is_active": True
            })
            
            submissions = []
            async for homework in cursor:
                for submission in homework.get('submissions', []):
                    if submission['user_id'] == user_id:
                        submissions.append({
                            "homework_id": str(homework['_id']),
                            "subject_name": homework['subject_name'],
                            "title": homework['title'],
                            "deadline": homework['deadline'],
                            "submitted_at": submission['submitted_at'],
                            "status": submission['status']
                        })
            
            return submissions
        except Exception as e:
            logger.error(f"Помилка отримання здач користувача: {e}")
            return []
    
    @staticmethod
    async def get_homework_statistics(homework_id: str) -> Dict[str, Any]:
        """Статистика по конкретному ДЗ"""
        try:
            from bson import ObjectId
            homework = await db.db.homework.find_one({"_id": ObjectId(homework_id)})
            
            if not homework:
                return {}
            
            total_members = len(await db.db.group_members.find({"is_active": True}).to_list(length=None))
            submissions_count = len(homework.get('submissions', []))
            
            return {
                "homework": homework,
                "total_students": total_members,
                "submitted_count": submissions_count,
                "not_submitted_count": total_members - submissions_count,
                "submissions": homework.get('submissions', [])
            }
            
        except Exception as e:
            logger.error(f"Помилка отримання статистики ДЗ: {e}")
            return {}
    
    @staticmethod
    async def close_homework(homework_id: str) -> bool:
        """Закриття домашнього завдання"""
        try:
            from bson import ObjectId
            result = await db.db.homework.update_one(
                {"_id": ObjectId(homework_id)},
                {"$set": {"is_active": False, "closed_at": datetime.utcnow()}}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Помилка закриття ДЗ: {e}")
            return False

class StudentProfileManager:
    """Клас для роботи з профілями студентів"""
    
    @staticmethod
    async def set_student_name(user_id: int, full_name: str) -> bool:
        """Встановлення повного імені студента"""
        try:
            result = await db.db.group_members.update_one(
                {"user_id": user_id},
                {"$set": {"full_name": full_name, "name_set_at": datetime.utcnow()}}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Помилка встановлення імені: {e}")
            return False
    
    @staticmethod
    async def get_student_name(user_id: int) -> Optional[str]:
        """Отримання повного імені студента"""
        try:
            student = await db.db.group_members.find_one({"user_id": user_id})
            return student.get('full_name') if student else None
        except Exception as e:
            logger.error(f"Помилка отримання імені: {e}")
            return None
    
    @staticmethod
    async def get_students_without_names() -> List[Dict[str, Any]]:
        """Отримання студентів без встановленого повного імені"""
        try:
            cursor = db.db.group_members.find({
                "is_active": True,
                "$or": [
                    {"full_name": {"$exists": False}},
                    {"full_name": ""},
                    {"full_name": None}
                ]
            })
            
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Помилка отримання студентів без імен: {e}")
            return []

class FileManager:
    """Клас для роботи з файлами"""
    
    @staticmethod
    async def save_file_info(file_id: str, user_id: int, file_name: str, 
                           file_type: str, homework_id: str = None) -> bool:
        """Збереження інформації про файл"""
        try:
            file_data = {
                "file_id": file_id,
                "user_id": user_id,
                "file_name": file_name,
                "file_type": file_type,
                "homework_id": homework_id,
                "uploaded_at": datetime.utcnow()
            }
            
            await db.db.files.insert_one(file_data)
            return True
        except Exception as e:
            logger.error(f"Помилка збереження файлу: {e}")
            return False
    
    @staticmethod
    async def get_homework_files(homework_id: str) -> List[Dict[str, Any]]:
        """Отримання всіх файлів по ДЗ"""
        try:
            cursor = db.db.files.find({"homework_id": homework_id})
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Помилка отримання файлів ДЗ: {e}")
            return []