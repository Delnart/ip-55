export const CONFIG = {
  API_URL: process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000/api',
  
  KPI_API_URL: 'https://api.campus.kpi.ua/schedule/lessons',
  
  KPI_GROUP_ID: process.env.REACT_APP_KPI_GROUP_ID || 'ec73a1ae-3542-4009-832e-2cc033ffe14b',
  
  QUEUE_REFRESH_INTERVAL: 5000,
  
  MAX_TOPICS_PER_USER: 2,
  
  DAYS_TRANSLATION: {
    'Пн': 'Понеділок',
    'Вв': 'Вівторок',
    'Ср': 'Середа',
    'Чт': 'Четвер',
    'Пт': "П'ятниця",
    'Сб': 'Субота'
  },
  
  CLASS_TYPES: {
    'Лек': '📚 Лекція',
    'Прак': '💻 Практика',
    'Лаб': '🔬 Лабораторна'
  },
  
  QUEUE_STATUSES: {
    'waiting': { label: 'В черзі', color: 'blue', icon: '⏳' },
    'preparing': { label: 'Готується', color: 'yellow', icon: '⏰' },
    'defending': { label: 'Здає', color: 'green', icon: '▶️' },
    'completed': { label: 'Здав', color: 'blue', icon: '✅' },
    'failed': { label: 'Не здав', color: 'red', icon: '❌' },
    'skipped': { label: 'Пропустив', color: 'gray', icon: '⏭️' }
  },
  
  DEFAULT_QUEUE_CONFIG: {
    maxSlots: 31,
    minMaxRule: true,
    priorityMove: true,
    maxAttempts: 3
  }
};

export const getApiUrl = (endpoint) => {
  return `${CONFIG.API_URL}${endpoint}`;
};

export const getKpiScheduleUrl = () => {
  return `${CONFIG.KPI_API_URL}?groupId=${CONFIG.KPI_GROUP_ID}`;
};