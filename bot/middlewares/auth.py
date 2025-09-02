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
        
        # Адмін завжди має доступ
        if user.id == ADMIN_ID:
            data['is_admin'] = True
            data['is_group_member'] = True
            return await handler(event, data)
        
        # Перевіряємо чи користувач є учасником групи
        is_member = await GroupMembersManager.is_member(user.id)
        
        if not is_member:
            # Якщо це повідомлення з групи - додаємо користувача
            if hasattr(event, 'chat') and event.chat.id == GROUP_ID:
                await GroupMembersManager.add_member(
                    user_id=user.id,
                    username=user.username or '',
                    first_name=user.first_name or '',
                    last_name=user.last_name
                )
                is_member = True
                logger.info(f"Додано нового учасника: {user.username} ({user.id})")
            else:
                # У приватних повідомленнях відхиляємо доступ
                if isinstance(event, Message):
                    await event.answer(
                        "❌ У вас немає доступу до цього бота.\n"
                        "Цей бот доступний тільки учасникам групи."
                    )
                return
        
        data['is_admin'] = False
        data['is_group_member'] = is_member
        
        return await handler(event, data)