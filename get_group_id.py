"""
Скрипт для отримання правильного ID групи
Запустіть цей скрипт і додайте бота до групи, після чого напишіть будь-яке повідомлення
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

found_groups = set()

async def log_all_messages(message: Message):
    """Логування всіх повідомлень для знаходження GROUP_ID"""
    chat_id = message.chat.id
    chat_type = message.chat.type
    chat_title = getattr(message.chat, 'title', 'Немає назви')
    
    if chat_type in ['group', 'supergroup']:
        found_groups.add((chat_id, chat_title, chat_type))
        
        print(f"\n🎯 ЗНАЙДЕНО ГРУПУ!")
        print(f"📋 ID: {chat_id}")
        print(f"📝 Назва: {chat_title}")
        print(f"🏷 Тип: {chat_type}")
        print(f"👤 Від: {message.from_user.first_name} (@{message.from_user.username})")
        print(f"💬 Текст: {message.text}")
        print("=" * 50)
        
        logger.info(f"Група знайдена: {chat_id} - {chat_title}")

async def log_chat_member_updates(event: ChatMemberUpdated):
    """Логування оновлень учасників для знаходження GROUP_ID"""
    chat_id = event.chat.id
    chat_type = event.chat.type
    chat_title = getattr(event.chat, 'title', 'Немає назви')
    
    if chat_type in ['group', 'supergroup']:
        found_groups.add((chat_id, chat_title, chat_type))
        
        print(f"\n🔔 ОНОВЛЕННЯ УЧАСНИКА ГРУПИ!")
        print(f"📋 ID: {chat_id}")
        print(f"📝 Назва: {chat_title}")
        print(f"🏷 Тип: {chat_type}")
        print(f"👤 Користувач: {event.new_chat_member.user.first_name}")
        print("=" * 50)
        
        logger.info(f"Оновлення в групі: {chat_id} - {chat_title}")

async def find_group_id():
    """Головна функція для пошуку ID групи"""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не встановлено!")
        return
    
    print("🔍 Запуск пошуку GROUP_ID...")
    print("📋 Інструкція:")
    print("1. Додайте бота до вашої групи")
    print("2. Надайте боту права адміністратора (опціонально)")
    print("3. Напишіть будь-яке повідомлення в групі")
    print("4. GROUP_ID буде показано тут")
    print("\n⏳ Очікування повідомлень...\n")
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Реєструємо обробники для всіх типів повідомлень
    dp.message.register(log_all_messages)
    dp.chat_member.register(
    log_chat_member_updates,
    ChatMemberUpdatedFilter(member_status_changed=True)
)

    
    try:
        # Отримуємо інформацію про бота
        bot_info = await bot.get_me()
        print(f"🤖 Бот: @{bot_info.username}")
        print(f"🆔 ID бота: {bot_info.id}")
        
        # Запускаємо polling
        print("\n✅ Бот запущено і очікує повідомлення...")
        print("💡 Натисніть Ctrl+C для зупинки\n")
        
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        print("\n🛑 Зупинка бота...")
        
        if found_groups:
            print(f"\n📊 ЗНАЙДЕНО ГРУП: {len(found_groups)}")
            print("=" * 60)
            
            for i, (group_id, title, group_type) in enumerate(found_groups, 1):
                print(f"\n{i}. Група: {title}")
                print(f"   ID: {group_id}")
                print(f"   Тип: {group_type}")
                print(f"   Для .env файлу: GROUP_ID={group_id}")
            
            print("\n📝 Скопіюйте потрібний GROUP_ID у ваш .env файл")
        else:
            print("\n❌ Жодної групи не знайдено")
            print("💡 Перевірте:")
            print("   - Чи доданий бот до групи")
            print("   - Чи написали ви повідомлення в групі після запуску скрипта")
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(find_group_id())