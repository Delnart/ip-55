from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from typing import Union

class AdminFilter(BaseFilter):
    """Фільтр для перевірки адміністраторських прав"""
    
    async def __call__(self, obj: Union[Message, CallbackQuery], is_admin: bool = False) -> bool:
        if not is_admin:
            if isinstance(obj, Message):
                await obj.answer("❌ Ця команда доступна тільки адміністратору.")
            elif isinstance(obj, CallbackQuery):
                await obj.answer("❌ Ця команда доступна тільки адміністратору.", show_alert=True)
            return False
        return True