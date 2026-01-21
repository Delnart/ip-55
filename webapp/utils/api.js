import { CONFIG } from '../config';

class ApiClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'API request failed');
      }

      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  }

  post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  patch(endpoint, data) {
    return this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
}

export const api = new ApiClient(CONFIG.API_URL);

export const userApi = {
  update: (data) => api.post('/users/update', data),
  get: (telegramId) => api.get(`/users/${telegramId}`),
};

export const subjectApi = {
  create: (data) => api.post('/subjects', data),
  getAll: () => api.get('/subjects'),
};

export const queueApi = {
  create: (subjectId) => api.post('/queues', { subjectId }),
  getBySubject: (subjectId) => api.get(`/queues/subject/${subjectId}`),
  join: (data) => api.post('/queues/join', data),
  leave: (data) => api.post('/queues/leave', data),
  kick: (data) => api.post('/queues/kick', data),
  toggle: (queueId) => api.post('/queues/toggle', { queueId }),
  updateStatus: (data) => api.patch('/queues/status', data),
  getConfig: (queueId) => api.get(`/queues/${queueId}/config`),
  updateConfig: (queueId, config) => api.patch(`/queues/${queueId}/config`, config),
  move: (data) => api.post('/queues/move', data),
};

export const topicsApi = {
  create: (data) => api.post('/topics', data),
  getBySubject: (subjectId) => api.get(`/topics/subject/${subjectId}`),
  claim: (data) => api.post('/topics/claim', data),
  release: (data) => api.post('/topics/release', data),
};

export const homeworkApi = {
  create: (data) => api.post('/homework', data),
  getAll: () => api.get('/homework'),
  update: (hwId, data) => api.patch(`/homework/${hwId}`, data),
  delete: (hwId) => api.delete(`/homework/${hwId}`),
};

export const scheduleApi = {
  getSchedule: async () => {
    try {
      const response = await fetch(`${CONFIG.KPI_API_URL}?groupId=${CONFIG.KPI_GROUP_ID}`);
      if (!response.ok) throw new Error('Schedule fetch failed');
      return await response.json();
    } catch (error) {
      console.error('Schedule Error:', error);
      return null;
    }
  },
  
  getCurrentWeekNumber: () => {
    const now = new Date();
    const year = now.getMonth() < 8 ? now.getFullYear() - 1 : now.getFullYear();
    const startOfYear = new Date(year, 8, 1);
    const daysSinceMonday = startOfYear.getDay() === 0 ? 6 : startOfYear.getDay() - 1;
    const firstMonday = new Date(startOfYear.getTime() - daysSinceMonday * 86400000);
    const weeksDiff = Math.floor((now - firstMonday) / (7 * 86400000));
    return (weeksDiff % 2) + 1;
  },
  
  formatClassInfo: (classData) => {
    const type = CONFIG.CLASS_TYPES[classData.type] || classData.type;
    const time = classData.time || '';
    const name = classData.name || '';
    const teacher = classData.teacherName || '';
    const place = classData.place || '';
    
    return { type, time, name, teacher, place };
  },
};