from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.models import GroupMembersManager
from config import ADMIN_ID, GROUP_ID
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseMiddleware):
    """Middleware для перевірки доступу до бота"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        
        if not user:
            return
        
        # Визначаємо чи це повідомлення в групі
        is_group_message = False
        if hasattr(event, 'chat'):
            is_group_message = event.chat.id == GROUP_ID
        elif hasattr(event, 'message') and hasattr(event.message, 'chat'):
            is_group_message = event.message.chat.id == GROUP_ID
        
        # Адмін завжди має доступ
        if user.id == ADMIN_ID:
            data['is_admin'] = True
            data['is_group_member'] = True
            return await handler(event, data)
        
        # Якщо це повідомлення в групі - дозволяємо всім учасникам групи
        if is_group_message:
            # Додаємо користувача до бази якщо його немає
            is_member = await GroupMembersManager.is_member(user.id)
            if not is_member:
                await GroupMembersManager.add_member(
                    user_id=user.id,
                    username=user.username or '',
                    first_name=user.first_name or '',
                    last_name=user.last_name
                )
                logger.info(f"Додано нового учасника з групи: {user.username} ({user.id})")
            
            data['is_admin'] = False
            data['is_group_member'] = True
            return await handler(event, data)
        
        # Для приватних повідомлень перевіряємо членство в групі
        is_member = await GroupMembersManager.is_member(user.id)
        
        if not is_member:
            # У приватних повідомленнях відхиляємо доступ
            if isinstance(event, Message):
                await event.answer(
                    "❌ У вас немає доступу до цього бота.\n"
                    "Цей бот доступний тільки учасникам групи.\n\n"
                    "Щоб отримати доступ, приєднайтесь до групи та напишіть там будь-яке повідомлення."
                )
            return
        
        data['is_admin'] = False
        data['is_group_member'] = is_member
        
        return await handler(event, data)