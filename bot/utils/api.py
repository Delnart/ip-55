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
        if date.tzinfo is not None:
            date = date.replace(tzinfo=None)
        year = date.year
        if date.month < 9: year -= 1
        start_of_year = datetime(year, 9, 1)
        days_since_monday = start_of_year.weekday()
        first_monday = start_of_year - timedelta(days=days_since_monday)
        weeks_diff = (date - first_monday).days // 7
        return (weeks_diff % 2) + 1
    
    @staticmethod
    async def get_schedule() -> Optional[Dict[str, Any]]:
        """Отримання розкладу з API з розширеним логуванням"""
        try:
            logger.info(f"Запит розкладу: {KPI_API_URL}")
            async with aiohttp.ClientSession() as session:
                async with session.get(KPI_API_URL) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'data' in data and 'scheduleFirstWeek' not in data:
                            data = data['data']
                            
                        if not data.get('scheduleFirstWeek') and not data.get('scheduleSecondWeek'):
                            logger.warning("Отримано порожній розклад! Перевірте KPI_GROUP_ID.")
                        else:
                            logger.info("Розклад успішно завантажено")
                            
                        return data
                    else:
                        logger.error(f"API повернув помилку: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Помилка отримання розкладу: {e}")
            return None
    
    @staticmethod
    async def format_class_info(class_data: Dict[str, Any]) -> str:
        from database.models import LinksManager
        
        class_type = CLASS_TYPES.get(class_data.get('type', ''), class_data.get('type', ''))
        start_time = class_data.get('time', '')
        end_time_str = get_class_end_time(start_time)

        if end_time_str:
            time_display = f"⏰ {start_time[:5]} - {end_time_str[:5]}"
        else:
            time_display = f"⏰ {start_time}"

        name = class_data.get('name', '')
        teacher = class_data.get('teacherName', '')
        place = class_data.get('place', '')
        
        info = f"{class_type}\n{time_display}\n📖 {name}\n👨‍🏫 {teacher}\n"
        if place: info += f"📍 {place}\n"
        
        link_data = await LinksManager.get_link(name, teacher, class_data.get('type', ''))
        
        if link_data:
            meet_link = link_data.get('meet_link')
            cls_link = link_data.get('classroom_link')
            if meet_link: info += f"🔗 [Приєднатися]({meet_link})\n"
            if cls_link: info += f"📖 [Classroom]({cls_link})\n"
        else:
            info += f"⚠️ Посилання не додані\n"
        
        return info
    
    @staticmethod
    async def get_current_class_info() -> Optional[Dict[str, Any]]:
        try:
            schedule_data = await ScheduleAPI.get_schedule()
            if not schedule_data: return None
            
            kiev_tz = pytz.timezone(TIMEZONE)
            now = datetime.now(kiev_tz)
            week_number = ScheduleAPI.get_week_number(now)
            week_key = 'scheduleFirstWeek' if week_number == 1 else 'scheduleSecondWeek'
            
            day_mapping = {'Monday':'Пн', 'Tuesday':'Вв', 'Wednesday':'Ср', 'Thursday':'Чт', 'Friday':'Пт', 'Saturday':'Сб'}
            day_code = day_mapping.get(now.strftime('%A'))
            if not day_code: return None
            
            week_schedule = schedule_data.get(week_key, [])
            today_classes = next((d['pairs'] for d in week_schedule if d['day'] == day_code), [])

            for class_data in today_classes:
                start = class_data.get('time')
                end = get_class_end_time(start)
                if not start or not end: continue
                
                s_dt = kiev_tz.localize(datetime.combine(now.date(), datetime.strptime(start, '%H:%M:%S').time()))
                e_dt = kiev_tz.localize(datetime.combine(now.date(), datetime.strptime(end, '%H:%M:%S').time()))
                
                if s_dt <= now <= e_dt:
                    class_data['end_datetime'] = e_dt
                    return class_data
            return None
        except Exception: return None

    @staticmethod
    async def get_today_schedule() -> str:
        schedule = await ScheduleAPI.get_schedule()
        if not schedule: return "❌ Помилка розкладу"
        
        now = datetime.now(pytz.timezone(TIMEZONE))
        day_map = {'Monday':'Пн', 'Tuesday':'Вв', 'Wednesday':'Ср', 'Thursday':'Чт', 'Friday':'Пт', 'Saturday':'Сб'}
        day_code = day_map.get(now.strftime('%A'))
        if not day_code: return "📅 Сьогодні вихідний"
        
        week = ScheduleAPI.get_week_number(now)
        key = 'scheduleFirstWeek' if week == 1 else 'scheduleSecondWeek'
        pairs = next((d['pairs'] for d in schedule.get(key, []) if d['day'] == day_code), [])
        
        if not pairs: return f"📅 Сьогодні ({DAYS_TRANSLATION[day_code]}) пар немає"
        
        res = f"📅 Розклад на сьогодні ({DAYS_TRANSLATION[day_code]}):\n\n"
        for i, p in enumerate(pairs, 1):
            res += f"**{i} пара**\n" + await ScheduleAPI.format_class_info(p) + "\n"
        return res

    @staticmethod
    async def get_tomorrow_schedule() -> str:
        schedule = await ScheduleAPI.get_schedule()
        if not schedule: return "❌ Помилка розкладу"
        
        now = datetime.now(pytz.timezone(TIMEZONE)) + timedelta(days=1)
        day_map = {'Monday':'Пн', 'Tuesday':'Вв', 'Wednesday':'Ср', 'Thursday':'Чт', 'Friday':'Пт', 'Saturday':'Сб', 'Sunday':'Пн'}
        day_code = day_map.get(now.strftime('%A'))
        if now.weekday() == 6: now += timedelta(days=1) # Якщо неділя, показуємо понеділок
        
        week = ScheduleAPI.get_week_number(now)
        key = 'scheduleFirstWeek' if week == 1 else 'scheduleSecondWeek'
        pairs = next((d['pairs'] for d in schedule.get(key, []) if d['day'] == day_code), [])
        
        if not pairs: return f"📅 На завтра ({DAYS_TRANSLATION.get(day_code, day_code)}) пар немає"
        
        res = f"📅 Розклад на завтра:\n\n"
        for i, p in enumerate(pairs, 1):
            res += f"**{i} пара**\n" + await ScheduleAPI.format_class_info(p) + "\n"
        return res

    @staticmethod
    async def get_week_schedule(week_offset: int = 0) -> str:
        schedule = await ScheduleAPI.get_schedule()
        if not schedule: return "❌ Помилка"
        
        now = datetime.now(pytz.timezone(TIMEZONE)) + timedelta(weeks=week_offset)
        week = ScheduleAPI.get_week_number(now)
        key = 'scheduleFirstWeek' if week == 1 else 'scheduleSecondWeek'
        
        res = f"📅 Розклад ({'Поточний' if week_offset==0 else 'Наступний'} тиждень):\n\n"
        for day in schedule.get(key, []):
            d_name = DAYS_TRANSLATION.get(day['day'], day['day'])
            res += f"📌 **{d_name}**:\n"
            for i, p in enumerate(day['pairs'], 1):
                res += f"_{i} пара_: {p['name']} ({p['type']})\n"
            res += "\n"
        return res