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
        
        # ВИПРАВЛЕННЯ: У групі дозволяємо всім користувачам без перевірки
        if is_group_message:
            # Адмін має адмінські права
            if user.id == ADMIN_ID:
                data['is_admin'] = True
                data['is_group_member'] = True
            else:
                data['is_admin'] = False
                data['is_group_member'] = True
                
                # Автоматично додаємо користувача до бази (без блокування команди)
                try:
                    is_member = await GroupMembersManager.is_member(user.id)
                    if not is_member:
                        await GroupMembersManager.add_member(
                            user_id=user.id,
                            username=user.username or '',
                            first_name=user.first_name or '',
                            last_name=user.last_name
                        )
                        logger.info(f"Додано нового учасника з групи: {user.username} ({user.id})")
                except Exception as e:
                    logger.error(f"Помилка додавання учасника: {e}")
                    # Навіть якщо помилка - не блокуємо команду в групі
                    pass
            
            return await handler(event, data)
        
        # Для приватних повідомлень - строга перевірка
        # Адмін завжди має доступ в приватних повідомленнях
        if user.id == ADMIN_ID:
            data['is_admin'] = True
            data['is_group_member'] = True
            return await handler(event, data)
        
        # Для не-адмінів в приватних повідомленнях перевіряємо членство
        is_member = await GroupMembersManager.is_member(user.id)
        
        if not is_member:
            # У приватних повідомленнях відхиляємо доступ
            if isinstance(event, Message):
                await event.answer(
                    "❌ У вас немає доступу до цього бота.\n"
                    "Цей бот доступний тільки учасникам групи.\n\n"
                    "Щоб отримати доступ, приєднайтесь до групи та напишіть там будь-яке повідомлення."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ У вас немає доступу до цього бота.", show_alert=True)
            return
        
        data['is_admin'] = False
        data['is_group_member'] = is_member
        
        return await handler(event, data)