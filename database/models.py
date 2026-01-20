from datetime import datetime
from typing import Optional, List, Dict, Any
from .connection import db
import logging

logger = logging.getLogger(__name__)

class LinksManager:
    """Клас для роботи з посиланнями на пари"""
    
    @staticmethod
    async def add_link(subject_name: str, teacher_name: str, class_type: str, 
                      meet_link: str, classroom_link: Optional[str] = None) -> bool:
        """Додавання посилання на пару"""
        try:
            link_data = {
                "subject_name": subject_name,
                "teacher_name": teacher_name,
                "class_type": class_type,
                "meet_link": meet_link,
                "classroom_link": classroom_link,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await db.db.links.update_one(
                {
                    "subject_name": subject_name,
                    "teacher_name": teacher_name,
                    "class_type": class_type
                },
                {"$set": link_data},
                upsert=True
            )
            
            logger.info(f"Посилання додано/оновлено: {subject_name} - {teacher_name}")
            return True
            
        except Exception as e:
            logger.error(f"Помилка додавання посилання: {e}")
            return False
    
    @staticmethod
    async def get_link(subject_name: str, teacher_name: str, class_type: str) -> Optional[Dict[str, Any]]:
        """Отримання посилання на пару з гнучким пошуком"""
        try:
            link = await db.db.links.find_one({
                "subject_name": subject_name,
                "teacher_name": teacher_name,
                "class_type": class_type
            })
            
            if link:
                return link
            
            link = await db.db.links.find_one({
                "subject_name": subject_name,
                "teacher_name": teacher_name
            })
            
            if link:
                return link
            
            link = await db.db.links.find_one({
                "subject_name": subject_name
            })
            
            if link:
                return link
            
            link = await db.db.links.find_one({
                "subject_name": {"$regex": subject_name.replace(" ", ".*"), "$options": "i"}
            })
            
            if link:
                return link
            
            link = await db.db.links.find_one({
                "teacher_name": {"$regex": teacher_name.replace(" ", ".*"), "$options": "i"}
            })
            
            return link
            
        except Exception as e:
            logger.error(f"Помилка отримання посилання: {e}")
            return None
    
    @staticmethod
    async def get_all_links() -> List[Dict[str, Any]]:
        """Отримання всіх посилань"""
        try:
            cursor = db.db.links.find({})
            links = await cursor.to_list(length=None)
            return links
        except Exception as e:
            logger.error(f"Помилка отримання всіх посилань: {e}")
            return []
    
    @staticmethod
    async def delete_link(subject_name: str, teacher_name: str, class_type: str) -> bool:
        """Видалення посилання"""
        try:
            result = await db.db.links.delete_one({
                "subject_name": subject_name,
                "teacher_name": teacher_name,
                "class_type": class_type
            })
            
            if result.deleted_count > 0:
                logger.info(f"Посилання видалено: {subject_name} - {teacher_name}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Помилка видалення посилання: {e}")
            return False
    
    @staticmethod
    async def search_links_by_subject(subject_name: str) -> List[Dict[str, Any]]:
        """Пошук посилань по назві предмета (для діагностики)"""
        try:
            cursor = db.db.links.find({
                "subject_name": {"$regex": subject_name, "$options": "i"}
            })
            links = await cursor.to_list(length=None)
            return links
        except Exception as e:
            logger.error(f"Помилка пошуку посилань: {e}")
            return []

class GroupMembersManager:
    """Клас для роботи з учасниками групи"""
    
    @staticmethod
    async def add_member(user_id: int, username: str, first_name: str, 
                        last_name: Optional[str] = None) -> bool:
        """Додавання учасника групи"""
        try:
            member_data = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "joined_at": datetime.utcnow(),
                "is_active": True
            }
            
            result = await db.db.group_members.update_one(
                {"user_id": user_id},
                {"$set": member_data},
                upsert=True
            )
            
            logger.info(f"Учасника додано: {username} ({user_id})")
            return True
            
        except Exception as e:
            logger.error(f"Помилка додавання учасника: {e}")
            return False
    
    @staticmethod
    async def is_member(user_id: int) -> bool:
        """Перевірка чи є користувач учасником групи"""
        try:
            member = await db.db.group_members.find_one({
                "user_id": user_id,
                "is_active": True
            })
            return member is not None
        except Exception as e:
            logger.error(f"Помилка перевірки учасника: {e}")
            return False
    
    @staticmethod
    async def get_all_members() -> List[Dict[str, Any]]:
        """Отримання всіх активних учасників"""
        try:
            cursor = db.db.group_members.find({"is_active": True})
            members = await cursor.to_list(length=None)
            return members
        except Exception as e:
            logger.error(f"Помилка отримання учасників: {e}")
            return []
    
    @staticmethod
    async def remove_member(user_id: int) -> bool:
        """Видалення учасника (позначення як неактивний)"""
        try:
            result = await db.db.group_members.update_one(
                {"user_id": user_id},
                {"$set": {"is_active": False}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Учасника деактивовано: {user_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Помилка видалення учасника: {e}")
            return False