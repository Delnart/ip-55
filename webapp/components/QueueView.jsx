import { useState, useEffect } from 'react';
import { api } from '../utils/api';
import { Icons } from '../utils/icons';

const STATUSES = {
  preparing: { label: 'Готується', color: 'bg-yellow-100 text-yellow-700 border-yellow-200', icon: '⏰' },
  defending: { label: 'Здає', color: 'bg-green-100 text-green-700 border-green-200', icon: '▶️' },
  completed: { label: 'Здав', color: 'bg-blue-100 text-blue-700 border-blue-200', icon: '✅' },
  failed: { label: 'Не здав', color: 'bg-red-100 text-red-700 border-red-200', icon: '❌' },
  waiting: { label: 'В черзі', color: 'bg-white border-gray-200', icon: '' }
};

export default function QueueView({ subject, user, onBack }) {
  const [queue, setQueue] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [labNum, setLabNum] = useState('');
  const [showConfig, setShowConfig] = useState(false);

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 4000);
    return () => clearInterval(interval);
  }, []);

  const fetchQueue = async () => {
    // Logic to get existing queue or create default on fly if missing
    let data = await api.get(`/queues/subject/${subject._id}`);
    if (!data) data = await api.post('/queues', { subjectId: subject._id });
    setQueue(data);
  };

  const handleJoin = async (slot) => {
    if (!labNum) return alert("Введіть номер лабораторної");
    try {
      await api.post('/queues/join', {
        queueId: queue._id,
        telegramId: user.id,
        labNumber: parseInt(labNum),
        position: slot
      });
      setSelectedSlot(null);
      setLabNum('');
      fetchQueue();
    } catch (e) {
      alert(e.response?.data?.detail || "Помилка");
    }
  };

  const handleStatusChange = async (targetUserId, status) => {
    try {
      await api.patch('/queues/status', {
        queueId: queue._id,
        userId: targetUserId,
        status,
        adminId: user.id
      });
      fetchQueue();
      setSelectedSlot(null);
    } catch (e) {
      alert("Немає прав");
    }
  };

  if (!queue) return <div className="p-10 text-center">Завантаження...</div>;

  const isAdmin = [/* Admin IDs */].includes(user.id); // Or check queue.config.activeAssistants

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <div className="bg-white p-4 sticky top-0 z-20 shadow-sm flex justify-between items-center">
        <div className="flex items-center gap-2">
           <button onClick={onBack}><Icons.ArrowLeft /></button>
           <div>
             <h2 className="font-bold leading-none">{subject.name}</h2>
             <span className={`text-xs ${queue.isActive ? 'text-green-500' : 'text-red-500'}`}>
               {queue.isActive ? 'Відкрито' : 'Закрито'}
             </span>
           </div>
        </div>
        {isAdmin && <button onClick={() => setShowConfig(!showConfig)}><Icons.Settings /></button>}
      </div>

      {isAdmin && showConfig && (
         <div className="bg-gray-100 p-4 border-b">
            <h3 className="font-bold text-sm mb-2">Налаштування адміна</h3>
            <div className="flex gap-2">
              <button onClick={() => api.post('/queues/toggle', { queueId: queue._id, adminId: user.id })} 
                className="bg-white px-3 py-1 rounded shadow text-sm">
                {queue.isActive ? 'Закрити чергу' : 'Відкрити чергу'}
              </button>
              {/* Add Toggle Min/Max rule button here */}
            </div>
         </div>
      )}

      <div className="p-3 grid grid-cols-3 gap-2">
        {Array.from({ length: 31 }, (_, i) => i + 1).map(slot => {
          const entry = queue.entries.find(e => e.position === slot);
          const statusStyle = entry ? STATUSES[entry.status].color : 'border-dashed border-gray-300';
          
          return (
            <div key={slot} onClick={() => setSelectedSlot({ slot, entry })}
              className={`relative min-h-[100px] rounded-xl border-2 flex flex-col items-center justify-center p-1 transition-all active:scale-95 cursor-pointer ${statusStyle}`}>
              
              <span className="absolute top-1 left-2 text-[10px] text-gray-400 font-bold">#{slot}</span>
              
              {entry ? (
                <>
                  <div className="w-8 h-8 rounded-full bg-gray-200 mb-1 overflow-hidden">
                     {/* Avatar placeholder or initials */}
                     <div className="w-full h-full flex items-center justify-center text-xs font-bold">
                       {entry.user.fullName?.[0]}
                     </div>
                  </div>
                  <span className="text-[10px] font-bold text-center leading-tight line-clamp-2">
                    {entry.user.fullName}
                  </span>
                  <div className="mt-1 flex items-center gap-1 bg-white/50 px-1.5 rounded-md">
                    <span className="text-[10px] font-bold">Лаб {entry.labNumber}</span>
                    <span className="text-[10px]">{STATUSES[entry.status].icon}</span>
                  </div>
                </>
              ) : (
                <span className="text-2xl text-gray-300">+</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Booking/Management Modal */}
      {selectedSlot && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelectedSlot(null)}>
          <div className="bg-white w-full max-w-xs rounded-2xl p-5" onClick={e => e.stopPropagation()}>
            <h3 className="text-xl font-bold mb-1">Місце #{selectedSlot.slot}</h3>
            
            {!selectedSlot.entry ? (
              // Join Mode
              <>
                <p className="text-gray-500 mb-4 text-sm">Вільне місце. Введіть номер лабораторної:</p>
                <input type="number" className="w-full bg-gray-100 p-3 rounded-xl mb-4 text-center font-bold text-lg" 
                  value={labNum} onChange={e => setLabNum(e.target.value)} autoFocus />
                <button onClick={() => handleJoin(selectedSlot.slot)} 
                  className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold shadow-lg shadow-blue-200">
                  Зайняти
                </button>
              </>
            ) : (
              // Manage Mode
              <>
                <p className="font-bold mb-4 text-center">{selectedSlot.entry.user.fullName}</p>
                {isAdmin ? (
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(STATUSES).map(([key, val]) => (
                      <button key={key} onClick={() => handleStatusChange(selectedSlot.entry.userId, key)}
                        className={`p-2 rounded-lg text-xs font-bold border ${val.color.replace('bg-', 'hover:bg-')}`}>
                        {val.icon} {val.label}
                      </button>
                    ))}
                    <button onClick={() => api.post('/queues/kick', { queueId: queue._id, targetUserId: selectedSlot.entry.userId, adminTgId: user.id }).then(fetchQueue)} 
                       className="col-span-2 mt-2 bg-red-50 text-red-600 py-2 rounded-lg font-bold">
                       Видалити з черги
                    </button>
                  </div>
                ) : (
                  selectedSlot.entry.user.telegramId === user.id && (
                    <button onClick={() => api.post('/queues/leave', { queueId: queue._id, telegramId: user.id }).then(() => { fetchQueue(); setSelectedSlot(null); })}
                      className="w-full bg-red-100 text-red-600 py-3 rounded-xl font-bold">
                      Вийти з черги
                    </button>
                  )
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}