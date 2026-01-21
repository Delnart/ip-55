import { useState, useEffect } from 'react';
import { api } from '../utils/api';

export default function Schedule({ onNavigate }) {
  const [schedule, setSchedule] = useState(null);
  const [week, setWeek] = useState(1);

  useEffect(() => {
    api.get('/schedule').then(setSchedule);
  }, []);

  if (!schedule) return <div>Завантаження...</div>;

  const weekKey = week === 1 ? 'scheduleFirstWeek' : 'scheduleSecondWeek';
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
  const dayNames = { Monday: 'Понеділок', Tuesday: 'Вівторок', Wednesday: 'Середа', Thursday: 'Четвер', Friday: "П'ятниця" };

  return (
    <div className="p-4 pb-24">
      <div className="flex bg-gray-200 rounded-lg p-1 mb-6">
        <button onClick={() => setWeek(1)} className={`flex-1 py-2 rounded-md font-medium text-sm transition ${week === 1 ? 'bg-white shadow-sm' : 'text-gray-500'}`}>Перший тиждень</button>
        <button onClick={() => setWeek(2)} className={`flex-1 py-2 rounded-md font-medium text-sm transition ${week === 2 ? 'bg-white shadow-sm' : 'text-gray-500'}`}>Другий тиждень</button>
      </div>

      <div className="space-y-6">
        {days.map(dayCode => {
          const dayData = schedule[weekKey].find(d => d.day === dayCode);
          if (!dayData?.pairs?.length) return null;

          return (
            <div key={dayCode}>
              <h3 className="text-gray-400 font-bold uppercase text-xs mb-3 tracking-wider">{dayNames[dayCode]}</h3>
              <div className="space-y-3">
                {dayData.pairs.map((pair, idx) => {
                  const isLecture = pair.type.includes('Лек');
                  const cardColor = isLecture ? 'bg-purple-50 border-purple-100' : 'bg-orange-50 border-orange-100';
                  const textColor = isLecture ? 'text-purple-700' : 'text-orange-700';
                  const badgeColor = isLecture ? 'bg-purple-200 text-purple-800' : 'bg-orange-200 text-orange-800';

                  return (
                    <div key={idx} className={`p-4 rounded-xl border-l-4 ${isLecture ? 'border-l-purple-500' : 'border-l-orange-500'} bg-white shadow-sm flex gap-4`}>
                      <div className="flex flex-col items-center justify-center min-w-[50px] border-r border-gray-100 pr-4">
                        <span className="font-bold text-gray-800 text-sm">{pair.time.substring(0, 5)}</span>
                        <span className="text-xs text-gray-400">Поч</span>
                      </div>
                      <div className="flex-1">
                        <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase mb-1 inline-block ${badgeColor}`}>
                          {pair.type}
                        </span>
                        <h4 className="font-bold text-gray-800 leading-tight mb-1">{pair.name}</h4>
                        <p className="text-xs text-gray-500 flex items-center gap-1">
                          👨‍🏫 {pair.teacherName}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}