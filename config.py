import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

# ID групи та адміна
GROUP_ID = int(os.getenv('GROUP_ID'))
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# MongoDB
MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/university_bot')

# API КПІ
KPI_GROUP_ID = os.getenv('KPI_GROUP_ID')
KPI_API_URL = f"https://api.campus.kpi.ua/schedule/lessons?groupId={KPI_GROUP_ID}"

# Часова зона (Київ)
TIMEZONE = 'Europe/Kiev'

# За скільки хвилин до пари надсилати повідомлення
NOTIFICATION_MINUTES_BEFORE = 10

# Словник для перекладу днів тижня
DAYS_TRANSLATION = {
    'Пн': 'Понеділок',
    'Вв': 'Вівторок', 
    'Ср': 'Середа',
    'Чт': 'Четвер',
    'Пт': "П'ятниця",
    'Сб': 'Субота'
}

# Словник для перекладу типів занять
CLASS_TYPES = {
    'Лек': '📚 Лекція',
    'Прак': '💻 Практика',
    'Лаб': '🔬 Лабораторна'
}