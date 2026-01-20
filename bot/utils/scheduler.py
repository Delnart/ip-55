import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Optional
import pytz
from aiogram import Bot
from bot.utils.api import ScheduleAPI, get_class_end_time 
from database.models import LinksManager, SettingsManager
from config import GROUP_ID, NOTIFICATION_MINUTES_BEFORE, TIMEZONE

logger = logging.getLogger(__name__)

class NotificationScheduler:
    """Планувальник автоматичних повідомлень про пари"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        self.task = None
        self.last_gif_sent_date: Optional[date] = None 
    
    async def start(self):
        """Запуск планувальника"""
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self._schedule_loop())
            logger.info("Планувальник повідомлень запущено")
    
    async def stop(self):
        """Зупинка планувальника"""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Планувальник повідомлень зупинено")
    
    async def _schedule_loop(self):
        """Основний цикл планувальника"""
        while self.is_running:
            try:
                await self._check_upcoming_classes()
                await self._check_end_of_day_gif() 
                
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Помилка в планувальнику: {e}")
                await asyncio.sleep(60)
    
    async def _check_upcoming_classes(self):
        """Перевірка майбутніх пар та надсилання сповіщень"""
        try:
            notifications_enabled = await SettingsManager.get_setting("notifications_enabled", True)
            if not notifications_enabled:
                return
            schedule_data = await ScheduleAPI.get_schedule()
            if not schedule_data:
                return
            
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
                return
            
            week_schedule = schedule_data.get(week_key, [])
            today_classes = None
            
            for day_data in week_schedule:
                if day_data.get('day') == day_code:
                    today_classes = day_data.get('pairs', [])
                    break
            
            if not today_classes:
                return
            
            for class_data in today_classes:
                await self._check_class_notification(class_data, now)
                
        except Exception as e:
            logger.error(f"Помилка перевірки майбутніх пар: {e}")
    
    async def _check_class_notification(self, class_data: dict, current_time: datetime):
        """Перевірка конкретної пари на необхідність сповіщення"""
        try:
            class_time_str = class_data.get('time', '')
            if not class_time_str:
                return
            
            try:
                class_time = datetime.strptime(class_time_str, '%H:%M:%S').time()
            except ValueError:
                try:
                    class_time = datetime.strptime(class_time_str, '%H:%M').time()
                except ValueError:
                    logger.error(f"Не вдалося парсити час: {class_time_str}")
                    return
            
            kiev_tz = pytz.timezone(TIMEZONE)
            today = current_time.date()
            
            class_datetime_naive = datetime.combine(today, class_time)
            class_datetime = kiev_tz.localize(class_datetime_naive)
            
            notification_time = class_datetime - timedelta(minutes=NOTIFICATION_MINUTES_BEFORE)
            
            time_diff = (notification_time - current_time).total_seconds()
            
            if 0 <= time_diff <= 60:
                await self._send_class_notification(class_data)
                
        except Exception as e:
            logger.error(f"Помилка перевірки сповіщення для пари: {e}")
    
    async def _send_class_notification(self, class_data: dict):
        """Надсилання сповіщення про пару"""
        try:
            subject_name = class_data.get('name', '')
            teacher_name = class_data.get('teacherName', '')
            class_type = class_data.get('type', '')
            class_time = class_data.get('time', '')
            place = class_data.get('place', '')
            
            link_data = await LinksManager.get_link(subject_name, teacher_name, class_type)
            
            if not link_data:
                logger.info(f"Посилання не знайдено для: {subject_name} - {teacher_name} ({class_type})")
                return
            
            message = f"🔔 **Нагадування про пару через {NOTIFICATION_MINUTES_BEFORE} хвилин!**\n\n"
            message += f"⏰ **Час:** {class_time}\n"
            message += f"📚 **Предмет:** {subject_name}\n"
            message += f"👨‍🏫 **Викладач:** {teacher_name}\n"
            message += f"📝 **Тип:** {class_type}\n"
            
            if place:
                message += f"📍 **Місце:** {place}\n"
            
            message += "\n"
            
            meet_link = link_data.get('meet_link')
            classroom_link = link_data.get('classroom_link')
            
            if meet_link:
                message += f"🔗 [Приєднатися до зустрічі]({meet_link})\n"
            
            if classroom_link:
                message += f"📖 [Google Classroom]({classroom_link})\n"
            
            await self.bot.send_message(
                chat_id=GROUP_ID,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info(f"Надіслано сповіщення про пару: {subject_name} - {teacher_name}")
            
        except Exception as e:
            logger.error(f"Помилка надсилання сповіщення: {e}")

    async def _check_end_of_day_gif(self):
        """Перевірка закінчення останньої пари для надсилання GIF"""
        try:
            kiev_tz = pytz.timezone(TIMEZONE)
            now = datetime.now(kiev_tz)
            today = now.date()

            if self.last_gif_sent_date == today:
                return 
            
            schedule_data = await ScheduleAPI.get_schedule()
            if not schedule_data:
                return

            week_number = ScheduleAPI.get_week_number(now)
            week_key = 'scheduleFirstWeek' if week_number == 1 else 'scheduleSecondWeek'
            
            day_mapping = {
                'Monday': 'Пн', 'Tuesday': 'Вв', 'Wednesday': 'Ср',
                'Thursday': 'Чт', 'Friday': 'Пт', 'Saturday': 'Сб'
            }
            day_code = day_mapping.get(now.strftime('%A'))
            if not day_code:
                return 

            week_schedule = schedule_data.get(week_key, [])
            today_classes = None
            for day_data in week_schedule:
                if day_data.get('day') == day_code:
                    today_classes = day_data.get('pairs', [])
                    break
            
            if not today_classes:
                return 

            last_class_data = today_classes[-1]
            
            start_time_str = last_class_data.get('time')
            if not start_time_str:
                return

            end_time_str = get_class_end_time(start_time_str)
            if not end_time_str:
                logger.warning(f"Не вдалося знайти час закінчення для пари {start_time_str}")
                return
            
            try:
                end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
            except ValueError:
                logger.error(f"Не вдалося парсити час закінчення: {end_time_str}")
                return

            end_datetime_naive = datetime.combine(today, end_time)
            end_datetime = kiev_tz.localize(end_datetime_naive)
            
            time_diff_seconds = (now - end_datetime).total_seconds()

            if 0 <= time_diff_seconds < 60:
                logger.info(f"Кінець навчального дня. Надсилаємо GIF.")
                gif_url = "https://i.ibb.co/JR3Qqvfc/b9d7a780-7a1b-45e6-99e3-3f1d9c259d90.gif" 
                
                try:
                    await self.bot.send_animation(
                        chat_id=GROUP_ID,
                        animation=gif_url,
                        caption="🎉 Пари закінчились! Час відпочивати!"
                    )
                    
                    self.last_gif_sent_date = today
                    
                except Exception as e:
                    logger.error(f"Помилка надсилання GIF: {e}")

        except Exception as e:
            logger.error(f"Помилка перевірки кінця дня (GIF): {e}")