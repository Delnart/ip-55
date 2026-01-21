import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = '/api';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' }
});

export default function QueueSettings({ queueId, onClose, onSave }) {
  const [config, setConfig] = useState({
    maxSlots: 31,
    minMaxRule: true,
    priorityMove: true,
    maxAttempts: 3
  });

  useEffect(() => {
    fetchConfig();
  }, [queueId]);

  const fetchConfig = async () => {
    try {
      const res = await api.get(`/queues/${queueId}/config`);
      if (res.data) {
        setConfig(res.data);
      }
    } catch (e) {
      console.error("Config fetch error:", e);
    }
  };

  const handleSave = async () => {
    try {
      await api.patch(`/queues/${queueId}/config`, config);
      if (onSave) onSave();
      if (onClose) onClose();
    } catch (e) {
      alert('Помилка збереження налаштувань');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-2xl animate-in zoom-in-95 duration-200" onClick={e => e.stopPropagation()}>
        <h2 className="font-bold text-xl mb-4">Налаштування черги</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Максимум місць
            </label>
            <input
              type="number"
              min="1"
              max="100"
              value={config.maxSlots}
              onChange={e => setConfig({ ...config, maxSlots: Number(e.target.value) })}
              className="w-full p-3 bg-gray-50 rounded-lg border border-gray-200"
            />
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-sm">Правило мін-макс</p>
              <p className="text-xs text-gray-500">Макс = Мін + 2</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={config.minMaxRule}
                onChange={e => setConfig({ ...config, minMaxRule: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-300 peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-sm">Пріоритетний рух</p>
              <p className="text-xs text-gray-500">Дозволити міняти місцями</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={config.priorityMove}
                onChange={e => setConfig({ ...config, priorityMove: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-300 peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Максимум спроб
            </label>
            <input
              type="number"
              min="1"
              max="10"
              value={config.maxAttempts}
              onChange={e => setConfig({ ...config, maxAttempts: Number(e.target.value) })}
              className="w-full p-3 bg-gray-50 rounded-lg border border-gray-200"
            />
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 bg-gray-100 text-gray-700 py-3 rounded-xl font-bold"
          >
            Скасувати
          </button>
          <button
            onClick={handleSave}
            className="flex-1 bg-blue-600 text-white py-3 rounded-xl font-bold"
          >
            Зберегти
          </button>
        </div>
      </div>
    </div>
  );
}