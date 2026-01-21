import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

# Використовуємо 'or', щоб якщо в .env пусто, бралось дефолтне значення
GROUP_ID = int(os.getenv('GROUP_ID') or '-4956301173')

admin_env = os.getenv('ADMIN_ID', '')
ADMIN_IDS = [int(id_str.strip()) for id_str in admin_env.split(',') if id_str.strip()]

MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/university_bot')

# ВАЖЛИВО: Тут виправлено логіку пріоритету
KPI_GROUP_ID = os.getenv('KPI_GROUP_ID') or 'ec73a1ae-3542-4009-832e-2cc033ffe14b'
KPI_API_URL = f"https://api.campus.kpi.ua/schedule/lessons?groupId={KPI_GROUP_ID}"

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