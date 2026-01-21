import { useEffect, useState } from 'react';
import axios from 'axios';

const API_URL = 'https://your-backend-url.com/api';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' }
});

export default function QueueView({ subjectId, user, onBack }) {
  const [queue, setQueue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [labNum, setLabNum] = useState('');
  const [isJoining, setIsJoining] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState(null);

  const MAX_SLOTS = queue?.config?.maxSlots || 31;
  const myEntry = queue?.entries?.find(e => e.user?.telegramId === user?.id);

  const fetchQueue = async () => {
    try {
      const res = await api.get(`/queues/subject/${subjectId}`);
      if (res.data && typeof res.data === 'object') {
        setQueue(res.data);
      } else {
        setQueue(null);
      }
    } catch (e) {
      console.error("Queue fetch error:", e);
      setQueue(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 5000);
    return () => clearInterval(interval);
  }, [subjectId]);

  const handleJoin = async (slotNum) => {
    if (!queue || !user) return;

    const positionToTake = slotNum || 1;
    let labToTake = labNum ? Number(labNum) : 0;

    if (labNum && labToTake < 1) {
      alert("Номер лабораторної не може бути менше 1");
      setLabNum('1');
      return;
    }

    if (!labToTake) {
      const promptVal = prompt("Яку лабу здаємо? (Введіть номер)", "1");
      if (!promptVal) return;
      labToTake = Number(promptVal);
      if (labToTake < 1) {
        alert("Номер має бути більше 0");
        return;
      }
    }

    try {
      await api.post('/queues/join', {
        queueId: queue._id,
        telegramId: user.id,
        labNumber: labToTake,
        position: positionToTake
      });
      setLabNum('');
      setIsJoining(false);
      fetchQueue();
    } catch (e) {
      alert(e.response?.data?.message || 'Помилка');
    }
  };

  const handleLeave = async () => {
    if (!queue || !user) return;
    if (confirm('Вийти з черги?')) {
      await api.post('/queues/leave', { queueId: queue._id, telegramId: user.id });
      fetchQueue();
    }
  };

  const handleCreateQueue = async () => {
    try {
      await api.post('/queues', { subjectId });
      fetchQueue();
    } catch (e) {
      alert('Помилка створення черги');
    }
  };

  const handleKick = async (targetUserId) => {
    if (!queue || !user) return;
    await api.post('/queues/kick', { queueId: queue._id, adminTgId: user.id, targetUserId });
    fetchQueue();
    setSelectedEntry(null);
  };

  const handleToggle = async () => {
    if (!queue) return;
    await api.post('/queues/toggle', { queueId: queue._id });
    fetchQueue();
  };

  const handleChangeStatus = async (targetUserId, newStatus) => {
    if (!queue) return;
    try {
      await api.patch('/queues/status', {
        queueId: queue._id,
        userId: targetUserId,
        status: newStatus
      });
      fetchQueue();
      setSelectedEntry(null);
    } catch (e) {
      console.error(e);
      alert('Не вдалося змінити статус');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'defending': return 'border-green-500 bg-green-50 ring-2 ring-green-200';
      case 'preparing': return 'border-yellow-400 bg-yellow-50 ring-2 ring-yellow-200';
      case 'completed': return 'border-blue-500 bg-blue-50 opacity-60';
      case 'failed': return 'border-red-500 bg-red-50';
      case 'skipped': return 'border-gray-400 bg-gray-100 opacity-50';
      case 'waiting': return 'border-blue-200 bg-white';
      default: return 'border-gray-200 bg-gray-50';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'defending': return '▶️';
      case 'preparing': return '⏰';
      case 'completed': return '✅';
      case 'failed': return '❌';
      default: return null;
    }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-500">Завантаження...</div>;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col relative">
      <div className="bg-white p-4 shadow-sm flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 text-gray-600 active:bg-gray-100 rounded-full transition">←</button>
          <div>
            <h1 className="font-bold text-lg leading-none">Черга</h1>
            {queue && (
              <span className={`text-xs ${queue.isActive ? 'text-green-600' : 'text-red-500'}`}>
                {queue.isActive ? '🟢 Відкрито' : '🔴 Закрито'}
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {queue && (
            <button onClick={handleToggle} className="p-2 text-gray-500 bg-gray-100 rounded-full hover:bg-gray-200 transition">
              {queue.isActive ? '🔓' : '🔒'}
            </button>
          )}
          <button onClick={fetchQueue} className="p-2 text-blue-600 bg-blue-50 rounded-full hover:bg-blue-100 transition">
            🔄
          </button>
        </div>
      </div>

      <div className="flex-1 p-3 overflow-y-auto">
        {!queue ? (
          <div className="text-center mt-20">
            <p className="text-gray-400 mb-4">Чергу ще не створено</p>
            <button onClick={handleCreateQueue} className="bg-blue-600 text-white px-6 py-3 rounded-xl font-bold flex items-center gap-2 mx-auto shadow-lg shadow-blue-200 active:scale-95 transition">
              Відкрити чергу
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 pb-20">
            <h3 className="mb-4 font-bold text-gray-700 flex justify-between items-center">
              <span>Місця в черзі</span>
              <span className="text-xs font-normal text-gray-400">Всього: {MAX_SLOTS}</span>
            </h3>

            <div className="grid grid-cols-3 gap-2">
              {Array.from({ length: MAX_SLOTS }, (_, i) => i + 1).map((slotNumber) => {
                const entry = queue.entries?.find(e => e.position === slotNumber);
                const isMyEntry = entry?.user?.telegramId === user?.id;

                const statusClass = entry ? getStatusColor(entry.status) : 'border-dashed border-gray-300 hover:border-blue-400 hover:bg-blue-50 cursor-pointer';
                const activeClass = isMyEntry ? 'ring-2 ring-blue-500 shadow-md transform scale-[1.02]' : '';

                return (
                  <div
                    key={slotNumber}
                    className={`
                      relative p-2 rounded-xl border-2 text-center min-h-[110px] flex flex-col items-center justify-center transition-all duration-200
                      ${statusClass} ${activeClass}
                    `}
                    onClick={() => {
                      if (!entry) handleJoin(slotNumber);
                      else if (entry.user) setSelectedEntry(entry);
                    }}
                  >
                    <span className={`absolute top-1 left-2 text-[10px] font-bold ${entry ? 'text-gray-500' : 'text-gray-300'}`}>
                      #{slotNumber}
                    </span>

                    {entry ? (
                      <>
                        <div className="w-10 h-10 rounded-full bg-gray-200 mb-1 overflow-hidden shadow-sm border border-white flex items-center justify-center text-gray-500 font-bold text-sm">
                          {entry.user?.fullName?.charAt(0) || '?'}
                        </div>

                        <span className="text-[11px] font-bold text-gray-800 leading-tight line-clamp-2 h-7 flex items-center justify-center">
                          {entry.user?.fullName || 'Студент'}
                        </span>

                        <div className="flex items-center gap-1 mt-1">
                          <span className="text-[10px] bg-white/80 px-1.5 py-0.5 rounded text-gray-600 font-medium border border-gray-100">
                            Лаб {entry.labNumber}
                          </span>
                          {getStatusIcon(entry.status)}
                        </div>
                      </>
                    ) : (
                      <div className="flex flex-col items-center opacity-50">
                        <span className="text-blue-500 font-bold text-xl mb-[-4px]">+</span>
                        <span className="text-[9px] text-gray-400">Вільно</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {queue && (
        <div className="p-4 bg-white border-t sticky bottom-0 z-20 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
          {!queue.isActive && !myEntry ? (
            <div className="w-full py-4 bg-gray-100 text-gray-500 rounded-xl font-bold text-center flex items-center justify-center gap-2">
              🔒 Запис закрито
            </div>
          ) : myEntry ? (
            <div className="flex gap-2">
              <div className="flex-1 bg-blue-50 text-blue-800 p-3 rounded-xl flex items-center justify-between px-4 border border-blue-100">
                <span className="text-xs font-bold text-blue-400 uppercase">Ваше місце</span>
                <span className="text-2xl font-black">{myEntry.position}</span>
              </div>
              <button
                onClick={handleLeave}
                className="px-6 bg-red-100 text-red-600 rounded-xl font-bold active:scale-95 transition flex items-center justify-center"
              >
                ✕
              </button>
            </div>
          ) : isJoining ? (
            <div className="flex gap-2 animate-in slide-in-from-bottom duration-300">
              <input
                type="number"
                min="1"
                placeholder="№ лаби"
                className="w-24 p-3 bg-gray-100 rounded-xl text-center font-bold outline-none focus:ring-2 focus:ring-blue-500 text-lg"
                value={labNum}
                onChange={e => setLabNum(e.target.value)}
                autoFocus
              />
              <button
                onClick={() => handleJoin()}
                className="flex-1 bg-green-600 text-white font-bold rounded-xl shadow-lg shadow-green-200 active:scale-95 transition"
              >
                Зайняти місце
              </button>
              <button onClick={() => setIsJoining(false)} className="px-4 bg-gray-100 rounded-xl text-gray-500 hover:bg-gray-200">✕</button>
            </div>
          ) : (
            <button
              onClick={() => setIsJoining(true)}
              className="w-full bg-blue-600 text-white py-4 rounded-xl font-bold shadow-lg shadow-blue-200 active:scale-95 transition flex items-center justify-center gap-2 text-lg"
            >
              Записатись в чергу
            </button>
          )}
        </div>
      )}

      {selectedEntry && selectedEntry.user && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelectedEntry(null)}>
          <div className="bg-white rounded-2xl w-full max-w-xs p-4 shadow-2xl animate-in zoom-in-95 duration-200" onClick={e => e.stopPropagation()}>
            <div className="text-center mb-4">
              <div className="w-16 h-16 rounded-full bg-gray-200 mx-auto mb-2 overflow-hidden flex items-center justify-center font-bold text-xl text-gray-500">
                {selectedEntry.user.fullName[0]}
              </div>
              <h3 className="font-bold text-lg">{selectedEntry.user.fullName}</h3>
              <p className="text-sm text-gray-500">Лабораторна робота №{selectedEntry.labNumber}</p>
            </div>

            <div className="grid grid-cols-2 gap-2 mb-4">
              <button onClick={() => handleChangeStatus(selectedEntry.user._id, 'preparing')} className="p-3 rounded-xl bg-yellow-50 text-yellow-700 font-bold border border-yellow-200 flex flex-col items-center gap-1 hover:bg-yellow-100">
                ⏰ Готується
              </button>
              <button onClick={() => handleChangeStatus(selectedEntry.user._id, 'defending')} className="p-3 rounded-xl bg-green-50 text-green-700 font-bold border border-green-200 flex flex-col items-center gap-1 hover:bg-green-100">
                ▶️ Здає
              </button>
              <button onClick={() => handleChangeStatus(selectedEntry.user._id, 'completed')} className="p-3 rounded-xl bg-blue-50 text-blue-700 font-bold border border-blue-200 flex flex-col items-center gap-1 hover:bg-blue-100">
                ✅ Здав
              </button>
              <button onClick={() => handleChangeStatus(selectedEntry.user._id, 'failed')} className="p-3 rounded-xl bg-red-50 text-red-700 font-bold border border-red-200 flex flex-col items-center gap-1 hover:bg-red-100">
                ❌ Не здав
              </button>
              <button onClick={() => handleChangeStatus(selectedEntry.user._id, 'waiting')} className="col-span-2 p-2 rounded-xl bg-gray-50 text-gray-600 text-sm font-medium border border-gray-200">
                Скинути статус (В чергу)
              </button>
            </div>

            <div className="border-t pt-3 flex justify-between items-center">
              <button
                onClick={() => handleKick(selectedEntry.user._id)}
                className="text-red-500 flex items-center gap-2 p-2 rounded-lg hover:bg-red-50 transition"
              >
                🗑️ Видалити
              </button>
              <button onClick={() => setSelectedEntry(null)} className="text-gray-400 p-2">Закрити</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}