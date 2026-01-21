import { useEffect, useState } from 'react';
import axios from 'axios';

const API_URL = '/api';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' }
});

export default function TopicsView({ subjectId, user, onBack }) {
  const [topics, setTopics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedTopic, setSelectedTopic] = useState(null);

  const MAX_TOPICS = topics?.maxTopics || 30;

  const fetchTopics = async () => {
    try {
      const res = await api.get(`/topics/subject/${subjectId}`);
      if (res.data && typeof res.data === 'object') {
        setTopics(res.data);
      } else {
        setTopics(null);
      }
    } catch (e) {
      console.error("Topics fetch error:", e);
      setTopics(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTopics();
    const interval = setInterval(fetchTopics, 5000);
    return () => clearInterval(interval);
  }, [subjectId]);

  const handleCreateTopics = async () => {
    const maxTopicsInput = prompt("Скільки тем максимум?", "30");
    if (!maxTopicsInput) return;
    
    const maxTopics = Number(maxTopicsInput);
    if (maxTopics < 1) {
      alert("Має бути більше 0");
      return;
    }

    try {
      await api.post('/topics', { subjectId, maxTopics });
      fetchTopics();
    } catch (e) {
      alert('Помилка створення списку тем');
    }
  };

  const handleClaimTopic = async (topicNumber) => {
    if (!topics || !user) return;

    const userEntries = topics.entries?.filter(e => e.user?.telegramId === user.id) || [];
    
    if (userEntries.length >= 2) {
      alert("Ви вже зайняли максимум 2 теми");
      return;
    }

    try {
      await api.post('/topics/claim', {
        subjectId: topics._id,
        telegramId: user.id,
        topicNumber
      });
      fetchTopics();
    } catch (e) {
      alert(e.response?.data?.message || 'Помилка');
    }
  };

  const handleReleaseTopic = async (topicNumber) => {
    if (!topics || !user) return;
    
    if (!confirm('Відмовитись від теми?')) return;

    try {
      await api.post('/topics/release', {
        subjectId: topics._id,
        telegramId: user.id,
        topicNumber
      });
      fetchTopics();
    } catch (e) {
      alert('Помилка');
    }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-500">Завантаження...</div>;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col relative">
      <div className="bg-white p-4 shadow-sm flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 text-gray-600 active:bg-gray-100 rounded-full transition">←</button>
          <div>
            <h1 className="font-bold text-lg leading-none">Теми рефератів</h1>
            <span className="text-xs text-gray-500">Можна обрати до 2 тем</span>
          </div>
        </div>
        <button onClick={fetchTopics} className="p-2 text-blue-600 bg-blue-50 rounded-full hover:bg-blue-100 transition">
          🔄
        </button>
      </div>

      <div className="flex-1 p-3 overflow-y-auto">
        {!topics ? (
          <div className="text-center mt-20">
            <p className="text-gray-400 mb-4">Список тем ще не створено</p>
            <button onClick={handleCreateTopics} className="bg-blue-600 text-white px-6 py-3 rounded-xl font-bold flex items-center gap-2 mx-auto shadow-lg shadow-blue-200 active:scale-95 transition">
              Створити список тем
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 pb-6">
            <h3 className="mb-4 font-bold text-gray-700 flex justify-between items-center">
              <span>Оберіть тему</span>
              <span className="text-xs font-normal text-gray-400">Всього: {MAX_TOPICS}</span>
            </h3>

            <div className="grid grid-cols-2 gap-3">
              {Array.from({ length: MAX_TOPICS }, (_, i) => i + 1).map((topicNumber) => {
                const entry = topics.entries?.find(e => e.topicNumber === topicNumber);
                const isMyTopic = entry?.user?.telegramId === user?.id;

                return (
                  <div
                    key={topicNumber}
                    onClick={() => {
                      if (!entry) handleClaimTopic(topicNumber);
                      else if (isMyTopic) handleReleaseTopic(topicNumber);
                      else setSelectedTopic(entry);
                    }}
                    className={`
                      relative p-4 rounded-xl border-2 text-center min-h-[100px] flex flex-col items-center justify-center transition-all duration-200 cursor-pointer
                      ${entry ? (isMyTopic ? 'bg-blue-50 border-blue-500 ring-2 ring-blue-200' : 'bg-gray-100 border-gray-300') : 'border-dashed border-gray-300 hover:border-blue-400 hover:bg-blue-50'}
                    `}
                  >
                    <span className={`absolute top-2 left-2 text-xs font-bold ${entry ? 'text-gray-500' : 'text-gray-300'}`}>
                      #{topicNumber}
                    </span>

                    {entry ? (
                      <>
                        <div className="w-12 h-12 rounded-full bg-gray-200 mb-2 flex items-center justify-center font-bold text-lg text-gray-500">
                          {entry.user?.fullName?.charAt(0) || '?'}
                        </div>
                        <span className="text-xs font-bold text-gray-800 line-clamp-2">
                          {entry.user?.fullName || 'Студент'}
                        </span>
                        {isMyTopic && (
                          <span className="text-xs bg-blue-500 text-white px-2 py-0.5 rounded mt-2">Ваша тема</span>
                        )}
                      </>
                    ) : (
                      <div className="flex flex-col items-center opacity-50">
                        <span className="text-green-500 font-bold text-2xl mb-1">+</span>
                        <span className="text-xs text-gray-400">Вільна</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {selectedTopic && selectedTopic.user && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelectedTopic(null)}>
          <div className="bg-white rounded-2xl w-full max-w-xs p-6 shadow-2xl animate-in zoom-in-95 duration-200" onClick={e => e.stopPropagation()}>
            <div className="text-center mb-4">
              <div className="w-20 h-20 rounded-full bg-gray-200 mx-auto mb-3 flex items-center justify-center font-bold text-2xl text-gray-500">
                {selectedTopic.user.fullName[0]}
              </div>
              <h3 className="font-bold text-xl">{selectedTopic.user.fullName}</h3>
              <p className="text-sm text-gray-500 mt-1">Тема №{selectedTopic.topicNumber}</p>
            </div>

            <button onClick={() => setSelectedTopic(null)} className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold">
              Закрити
            </button>
          </div>
        </div>
      )}
    </div>
  );
}