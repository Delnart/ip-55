import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from config import KPI_API_URL, DAYS_TRANSLATION, CLASS_TYPES, TIMEZONE
import pytz
import logging

logger = logging.getLogger(__name__)

class ScheduleAPI:
    """Клас для роботи з API розкладу КПІ"""
    
    @staticmethod
    def get_week_number(date: datetime) -> int:
        """Отримання номера навчального тижня (1 - перший, 2 - другий)"""
        # Конвертуємо в naive datetime для обчислень
        if date.tzinfo is not None:
            date = date.replace(tzinfo=None)
        
        # Початок навчального року (1 вересня поточного року)
        year = date.year
        if date.month < 9:  # Якщо до вересня - беремо попередній рік
            year -= 1
        
        # 1 вересня як початок навчального року
        start_of_year = datetime(year, 9, 1)
        
        # Знаходимо перший понеділок навчального року
        days_since_monday = start_of_year.weekday()
        first_monday = start_of_year - timedelta(days=days_since_monday)
        
        # Різниця в тижнях від початку навчального року
        weeks_diff = (date - first_monday).days // 7
        
        # Повертаємо 1 або 2 (перший або другий тиждень)
        return (weeks_diff % 2) + 1
    
    @staticmethod
    async def get_schedule() -> Optional[Dict[str, Any]]:
        """Отримання розкладу з API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(KPI_API_URL) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.error(f"API повернув статус {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Помилка отримання розкладу з API: {e}")
            return None
    
    @staticmethod
    async def format_class_info(class_data: Dict[str, Any]) -> str:
        """Форматування інформації про пару з посиланнями"""
        from database.models import LinksManager
        
        class_type = CLASS_TYPES.get(class_data.get('type', ''), class_data.get('type', ''))
        time = class_data.get('time', '')
        name = class_data.get('name', '')
        teacher = class_data.get('teacherName', '')
        place = class_data.get('place', '')
        
        info = f"{class_type} {time}\n"
        info += f"📖 {name}\n"
        info += f"👨‍🏫 {teacher}\n"
        
        if place:
            info += f"📍 {place}\n"
        
        # НОВЕ: Шукаємо посилання для цієї пари
        link_data = await LinksManager.get_link(name, teacher, class_data.get('type', ''))
        
        if link_data:
            meet_link = link_data.get('meet_link')
            classroom_link = link_data.get('classroom_link')
            
            if meet_link:
                info += f"🔗 [Приєднатися до зустрічі]({meet_link})\n"
            
            if classroom_link:
                info += f"📖 [Google Classroom]({classroom_link})\n"
        else:
            info += f"⚠️ Посилання не додані\n"
        
        return info
    
    @staticmethod
    async def get_today_schedule() -> str:
        """Розклад на сьогодні з посиланнями"""
        try:
            schedule_data = await ScheduleAPI.get_schedule()
            if not schedule_data:
                return "❌ Не вдалося отримати розклад"
            
            # Визначаємо поточний день та тиждень
            kiev_tz = pytz.timezone(TIMEZONE)
            now = datetime.now(kiev_tz)
            today = now.strftime('%A')
            
            # Використовуємо нову функцію для визначення тижня
            week_number = ScheduleAPI.get_week_number(now)
            week_key = 'scheduleFirstWeek' if week_number == 1 else 'scheduleSecondWeek'
            
            # Перекладаємо назву дня
            day_mapping = {
                'Monday': 'Пн',
                'Tuesday': 'Вв',
                'Wednesday': 'Ср',
                'Thursday': 'Чт',
                'Friday': 'Пт',
                'Saturday': 'Сб'
            }
            
            day_code = day_mapping.get(today)
            if not day_code:
                return "❌ Не вдалося визначити день тижня"
            
            # Шукаємо розклад на сьогодні
            week_schedule = schedule_data.get(week_key, [])
            today_classes = None
            
            for day_data in week_schedule:
                if day_data.get('day') == day_code:
                    today_classes = day_data.get('pairs', [])
                    break
            
            if not today_classes:
                return f"📅 На сьогодні ({DAYS_TRANSLATION[day_code]}) пар немає"
            
            # Форматуємо розклад з посиланнями
            week_name = "1-й тиждень" if week_number == 1 else "2-й тиждень"
            result = f"📅 Розклад на сьогодні ({DAYS_TRANSLATION[day_code]}, {week_name}):\n\n"
            
            for i, class_data in enumerate(today_classes, 1):
                class_info = await ScheduleAPI.format_class_info(class_data)
                result += f"{i}. {class_info}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Помилка отримання розкладу на сьогодні: {e}")
            return "❌ Помилка отримання розкладу"
    
    @staticmethod
    async def get_tomorrow_schedule() -> str:
        """Розклад на завтра з посиланнями"""
        try:
            schedule_data = await ScheduleAPI.get_schedule()
            if not schedule_data:
                return "❌ Не вдалося отримати розклад"
            
            # Визначаємо завтрашній день
            kiev_tz = pytz.timezone(TIMEZONE)
            tomorrow = datetime.now(kiev_tz) + timedelta(days=1)
            tomorrow_day = tomorrow.strftime('%A')
            
            # Використовуємо нову функцію для визначення тижня
            week_number = ScheduleAPI.get_week_number(tomorrow)
            week_key = 'scheduleFirstWeek' if week_number == 1 else 'scheduleSecondWeek'
            
            # Перекладаємо назву дня
            day_mapping = {
                'Monday': 'Пн',
                'Tuesday': 'Вв',
                'Wednesday': 'Ср',
                'Thursday': 'Чт',
                'Friday': 'Пт',
                'Saturday': 'Сб',
                'Sunday': 'Пн'  # Неділя -> показуємо наступний понеділок
            }
            
            day_code = day_mapping.get(tomorrow_day)
            if not day_code:
                return "❌ Не вдалося визначити день тижня"
            
            # Якщо завтра неділя, показуємо понеділок
            if tomorrow_day == 'Sunday':
                tomorrow = tomorrow + timedelta(days=1)
                week_number = ScheduleAPI.get_week_number(tomorrow)
                week_key = 'scheduleFirstWeek' if week_number == 1 else 'scheduleSecondWeek'
            
            # Шукаємо розклад на завтра
            week_schedule = schedule_data.get(week_key, [])
            tomorrow_classes = None
            
            for day_data in week_schedule:
                if day_data.get('day') == day_code:
                    tomorrow_classes = day_data.get('pairs', [])
                    break
            
            if not tomorrow_classes:
                return f"📅 На завтра ({DAYS_TRANSLATION[day_code]}) пар немає"
            
            # Форматуємо розклад з посиланнями
            week_name = "1-й тиждень" if week_number == 1 else "2-й тиждень"
            result = f"📅 Розклад на завтра ({DAYS_TRANSLATION[day_code]}, {week_name}):\n\n"
            
            for i, class_data in enumerate(tomorrow_classes, 1):
                class_info = await ScheduleAPI.format_class_info(class_data)
                result += f"{i}. {class_info}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Помилка отримання розкладу на завтра: {e}")
            return "❌ Помилка отримання розкладу"
    
    @staticmethod
    async def get_week_schedule(week_offset: int = 0) -> str:
        """Розклад на тиждень з посиланнями (0 - поточний, 1 - наступний)"""
        try:
            schedule_data = await ScheduleAPI.get_schedule()
            if not schedule_data:
                return "❌ Не вдалося отримати розклад"
            
            # Визначаємо тиждень
            kiev_tz = pytz.timezone(TIMEZONE)
            target_date = datetime.now(kiev_tz) + timedelta(weeks=week_offset)
            
            # Використовуємо нову функцію для визначення тижня
            week_number = ScheduleAPI.get_week_number(target_date)
            week_key = 'scheduleFirstWeek' if week_number == 1 else 'scheduleSecondWeek'
            
            week_name = "Поточний тиждень" if week_offset == 0 else "Наступний тиждень"
            week_type = "1-й тиждень" if week_number == 1 else "2-й тиждень"
            
            week_schedule = schedule_data.get(week_key, [])
            
            if not week_schedule:
                return f"❌ Розклад на {week_name.lower()} не знайдено"
            
            result = f"📅 {week_name} ({week_type}):\n\n"
            
            for day_data in week_schedule:
                day_code = day_data.get('day')
                day_name = DAYS_TRANSLATION.get(day_code, day_code)
                pairs = day_data.get('pairs', [])
                
                if pairs:
                    result += f"📌 {day_name}:\n"
                    for i, class_data in enumerate(pairs, 1):
                        class_info = await ScheduleAPI.format_class_info(class_data)
                        result += f"{i}. {class_info}\n"
                    result += "\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Помилка отримання розкладу на тиждень: {e}")
            return "❌ Помилка отримання розкладу"