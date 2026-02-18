import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

GROUP_ID = int(os.getenv('GROUP_ID'))

admin_env = os.getenv('ADMIN_ID', '')
ADMIN_IDS = [int(id_str.strip()) for id_str in admin_env.split(',') if id_str.strip()]

MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/university_bot')

KPI_GROUP_ID = os.getenv('KPI_GROUP_ID')
KPI_API_URL = f"https://api.campus.kpi.ua/schedule/lessons?groupId={KPI_GROUP_ID}"
WEBAPP_URL = "https://ip-55.onrender.com"
TIMEZONE = 'Europe/Kiev'

NOTIFICATION_MINUTES_BEFORE = 10

DAYS_TRANSLATION = {
    'Пн': 'Понеділок',
    'Вв': 'Вівторок', 
    'Ср': 'Середа',
    'Чт': 'Четвер',
    'Пт': "П'ятниця",
    'Сб': 'Субота'
}

CLASS_TYPES = {
    'Лек': '📚 Лекція',
    'Прак': '💻 Практика',
    'Лаб': '🔬 Лабораторна'
}
