import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from config import KPI_API_URL, DAYS_TRANSLATION, CLASS_TYPES, TIMEZONE
import pytz
import logging

logger = logging.getLogger(__name__)

CLASS_TIMINGS = {
    "08:30:00": "10:05:00",
    "10:25:00": "12:00:00",
    "12:20:00": "13:55:00",
    "14:15:00": "15:50:00",
    "16:10:00": "17:45:00",
    "18:30:00": "20:05:00",
    "20:20:00": "21:55:00"
}

def get_class_end_time(start_time: str) -> Optional[str]:
    """Повертає час закінчення пари за її початком"""
    if len(start_time.split(':')) == 2:
        start_time += ':00'
    return CLASS_TIMINGS.get(start_time)


class ScheduleAPI:
    """Клас для роботи з API розкладу КПІ"""
    
    @staticmethod
    def get_week_number(date: datetime) -> int:
        """Отримання номера навчального тижня (1 - перший, 2 - другий)"""
        if date.tzinfo is not None:
            date = date.replace(tzinfo=None)
        
        year = date.year
        if date.month < 9: 
            year -= 1
        
        start_of_year = datetime(year, 9, 1)
        
        days_since_monday = start_of_year.weekday()
        first_monday = start_of_year - timedelta(days=days_since_monday)
        
        weeks_diff = (date - first_monday).days // 7
        
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
        """Форматування інформації про пару з посиланнями та часом закінчення"""
        from database.models import LinksManager
        
        class_type = CLASS_TYPES.get(class_data.get('type', ''), class_data.get('type', ''))
        start_time = class_data.get('time', '')
        end_time_str = get_class_end_time(start_time)

        if end_time_str:
            start_time_short = start_time[:5]
            end_time_short = end_time_str[:5]
            time_display = f"⏰ {start_time_short} - {end_time_short}"
        else:
            time_display = f"⏰ {start_time}"

        name = class_data.get('name', '')
        teacher = class_data.get('teacherName', '')
        place = class_data.get('place', '')
        
        info = f"{class_type}\n"
        info += f"{time_display}\n"
        info += f"📖 {name}\n"
        info += f"👨‍🏫 {teacher}\n"
        
        if place:
            info += f"📍 {place}\n"
        
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
    async def get_current_class_info() -> Optional[Dict[str, Any]]:
        """Отримання інформації про поточну пару"""
        try:
            schedule_data = await ScheduleAPI.get_schedule()
            if not schedule_data:
                return None
            
            kiev_tz = pytz.timezone(TIMEZONE)
            now = datetime.now(kiev_tz)
            
            week_number = ScheduleAPI.get_week_number(now)
            week_key = 'scheduleFirstWeek' if week_number == 1 else 'scheduleSecondWeek'
            
            day_mapping = {
                'Monday': 'Пн', 'Tuesday': 'Вв', 'Wednesday': 'Ср',
                'Thursday': 'Чт', 'Friday': 'Пт', 'Saturday': 'Сб'
            }
            day_code = day_mapping.get(now.strftime('%A'))
            if not day_code:
                return None
            
            week_schedule = schedule_data.get(week_key, [])
            today_classes = None
            for day_data in week_schedule:
                if day_data.get('day') == day_code:
                    today_classes = day_data.get('pairs', [])
                    break
            
            if not today_classes:
                return None

            for class_data in today_classes:
                start_time_str = class_data.get('time')
                end_time_str = get_class_end_time(start_time_str)

                if not start_time_str or not end_time_str:
                    continue

                try:
                    start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
                    end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
                except ValueError:
                    continue

                start_datetime = kiev_tz.localize(datetime.combine(now.date(), start_time))
                end_datetime = kiev_tz.localize(datetime.combine(now.date(), end_time))

                if start_datetime <= now <= end_datetime:
                    class_data['end_datetime'] = end_datetime
                    return class_data

            return None
        except Exception as e:
            logger.error(f"Помилка отримання поточної пари: {e}")
            return None

    @staticmethod
    async def get_today_schedule() -> str:
        """Розклад на сьогодні з посиланнями"""
        try:
            schedule_data = await ScheduleAPI.get_schedule()
            if not schedule_data:
                return "❌ Не вдалося отримати розклад"
            
            kiev_tz = pytz.timezone(TIMEZONE)
            now = datetime.now(kiev_tz)
            today = now.strftime('%A')
            
            week_number = ScheduleAPI.get_week_number(now)
            week_key = 'scheduleFirstWeek' if week_number == 1 else 'scheduleSecondWeek'
            
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
            
            week_schedule = schedule_data.get(week_key, [])
            today_classes = None
            
            for day_data in week_schedule:
                if day_data.get('day') == day_code:
                    today_classes = day_data.get('pairs', [])
                    break
            
            if not today_classes:
                return f"📅 На сьогодні ({DAYS_TRANSLATION[day_code]}) пар немає"
            
            week_name = "1-й тиждень" if week_number == 1 else "2-й тиждень"
            result = f"📅 Розклад на сьогодні ({DAYS_TRANSLATION[day_code]}, {week_name}):\n\n"
            
            for i, class_data in enumerate(today_classes, 1):
                class_info = await ScheduleAPI.format_class_info(class_data)
                result += f"**{i} пара**\n{class_info}\n"
            
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
            
            kiev_tz = pytz.timezone(TIMEZONE)
            tomorrow = datetime.now(kiev_tz) + timedelta(days=1)
            tomorrow_day = tomorrow.strftime('%A')
            
            week_number = ScheduleAPI.get_week_number(tomorrow)
            week_key = 'scheduleFirstWeek' if week_number == 1 else 'scheduleSecondWeek'
            
            day_mapping = {
                'Monday': 'Пн',
                'Tuesday': 'Вв',
                'Wednesday': 'Ср',
                'Thursday': 'Чт',
                'Friday': 'Пт',
                'Saturday': 'Сб',
                'Sunday': 'Пн'  
            }
            
            day_code = day_mapping.get(tomorrow_day)
            if not day_code:
                return "❌ Не вдалося визначити день тижня"
            
            if tomorrow_day == 'Sunday':
                tomorrow = tomorrow + timedelta(days=1)
                week_number = ScheduleAPI.get_week_number(tomorrow)
                week_key = 'scheduleFirstWeek' if week_number == 1 else 'scheduleSecondWeek'
            
            week_schedule = schedule_data.get(week_key, [])
            tomorrow_classes = None
            
            for day_data in week_schedule:
                if day_data.get('day') == day_code:
                    tomorrow_classes = day_data.get('pairs', [])
                    break
            
            if not tomorrow_classes:
                return f"📅 На завтра ({DAYS_TRANSLATION[day_code]}) пар немає"
            
            week_name = "1-й тиждень" if week_number == 1 else "2-й тиждень"
            result = f"📅 Розклад на завтра ({DAYS_TRANSLATION[day_code]}, {week_name}):\n\n"
            
            for i, class_data in enumerate(tomorrow_classes, 1):
                class_info = await ScheduleAPI.format_class_info(class_data)
                result += f"**{i} пара**\n{class_info}\n"
            
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
            
            kiev_tz = pytz.timezone(TIMEZONE)
            target_date = datetime.now(kiev_tz) + timedelta(weeks=week_offset)
            
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
                    result += f"📌 **{day_name}**:\n"
                    for i, class_data in enumerate(pairs, 1):
                        class_info = await ScheduleAPI.format_class_info(class_data)
                        result += f"_{i} пара_\n{class_info}\n"
                    result += "\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Помилка отримання розкладу на тиждень: {e}")
            return "❌ Помилка отримання розкладу"