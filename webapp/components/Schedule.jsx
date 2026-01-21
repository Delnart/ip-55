import { useState, useEffect } from 'react';
import { scheduleApi } from '../utils/api';
import { CONFIG } from '../config';

export default function Schedule() {
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedWeek, setSelectedWeek] = useState(1);
  const [selectedDay, setSelectedDay] = useState(null);

  useEffect(() => {
    loadSchedule();
  }, []);

  const loadSchedule = async () => {
    setLoading(true);
    const data = await scheduleApi.getSchedule();
    setSchedule(data);
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-gray-500">Завантаження розкладу...</p>
        </div>
      </div>
    );
  }

  if (!schedule) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="text-center">
          <p className="text-gray-500 mb-4">Не вдалося завантажити розклад</p>
          <button
            onClick={loadSchedule}
            className="bg-blue-600 text-white px-6 py-3 rounded-xl font-bold"
          >
            Спробувати ще раз
          </button>
        </div>
      </div>
    );
  }

  const weekKey = selectedWeek === 1 ? 'scheduleFirstWeek' : 'scheduleSecondWeek';
  const weekSchedule = schedule[weekKey] || [];

  const days = [
    { code: 'Пн', name: 'Понеділок' },
    { code: 'Вв', name: 'Вівторок' },
    { code: 'Ср', name: 'Середа' },
    { code: 'Чт', name: 'Четвер' },
    { code: 'Пт', name: "П'ятниця" },
    { code: 'Сб', name: 'Субота' }
  ];

  if (selectedDay) {
    const dayData = weekSchedule.find(d => d.day === selectedDay);
    const dayName = days.find(d => d.code === selectedDay)?.name;

    return (
      <div className="min-h-screen bg-gray-50 pb-4">
        <div className="bg-white p-4 shadow-sm sticky top-0 z-10">
          <button
            onClick={() => setSelectedDay(null)}
            className="text-blue-600 mb-2 flex items-center gap-2"
          >
            ← Назад
          </button>
          <h1 className="font-bold text-xl">{dayName}</h1>
          <p className="text-sm text-gray-500">{selectedWeek} тиждень</p>
        </div>

        <div className="p-4">
          {dayData?.pairs?.length > 0 ? (
            <div className="space-y-3">
              {dayData.pairs.map((pair, idx) => {
                const info = scheduleApi.formatClassInfo(pair);
                return (
                  <div key={idx} className="bg-white rounded-xl shadow-sm p-4 border-l-4 border-blue-500">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-bold text-lg">{info.name}</h3>
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded font-medium">
                        {info.time}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-1">{info.type}</p>
                    <p className="text-sm text-gray-700 font-medium mb-1">{info.teacher}</p>
                    {info.place && (
                      <p className="text-xs text-gray-500">📍 {info.place}</p>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm p-8 text-center">
              <p className="text-gray-400">Вихідний день</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-4">
      <div className="bg-white p-4 shadow-sm sticky top-0 z-10">
        <h1 className="font-bold text-2xl mb-3">Розклад</h1>
        
        <div className="flex gap-2">
          <button
            onClick={() => setSelectedWeek(1)}
            className={`flex-1 py-2 rounded-lg font-medium transition ${
              selectedWeek === 1
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            1 тиждень
          </button>
          <button
            onClick={() => setSelectedWeek(2)}
            className={`flex-1 py-2 rounded-lg font-medium transition ${
              selectedWeek === 2
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            2 тиждень
          </button>
        </div>
      </div>

      <div className="p-4 space-y-3">
        {days.map(day => {
          const dayData = weekSchedule.find(d => d.day === day.code);
          const pairsCount = dayData?.pairs?.length || 0;

          return (
            <button
              key={day.code}
              onClick={() => setSelectedDay(day.code)}
              className="w-full bg-white rounded-xl shadow-sm p-4 text-left hover:shadow-md transition"
            >
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="font-bold text-lg">{day.name}</h3>
                  <p className="text-sm text-gray-500">
                    {pairsCount > 0 ? `${pairsCount} ${pairsCount === 1 ? 'пара' : 'пари'}` : 'Вихідний'}
                  </p>
                </div>
                <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>

              {pairsCount > 0 && (
                <div className="mt-3 flex gap-2 flex-wrap">
                  {dayData.pairs.slice(0, 3).map((pair, idx) => (
                    <span key={idx} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
                      {pair.time}
                    </span>
                  ))}
                  {pairsCount > 3 && (
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                      +{pairsCount - 3}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}