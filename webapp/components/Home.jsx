import { useState, useEffect } from 'react';
import { Icons } from '../utils/icons';
import { api } from '../utils/api';

export default function Home({ user, onNavigate }) {
  const [subjects, setSubjects] = useState([]);
  const [isAdmin, setIsAdmin] = useState(false); // Check admin logic based on user.id
  const [isEditing, setIsEditing] = useState(false);
  const [newSubject, setNewSubject] = useState({ name: '', type: 'exam', teacherLecture: '' });

  useEffect(() => {
    loadSubjects();
    // Hardcoded admin check or from API
    if (user?.id) setIsAdmin([/*ADMIN_IDS_HERE*/].includes(user.id));
  }, [user]);

  const loadSubjects = async () => {
    const data = await api.get('/subjects');
    setSubjects(data);
  };

  const handleAddSubject = async () => {
    await api.post('/subjects', newSubject);
    setIsEditing(false);
    loadSubjects();
  };

  return (
    <div className="p-4 pb-24">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Мої предмети</h1>
          <p className="text-gray-500 text-sm">Оберіть дисципліну</p>
        </div>
        {isAdmin && (
          <button onClick={() => setIsEditing(!isEditing)} className="p-2 bg-gray-100 rounded-full">
            <Icons.Settings className="w-6 h-6 text-gray-600" />
          </button>
        )}
      </div>

      {isEditing && (
        <div className="bg-white p-4 rounded-xl shadow-lg mb-6 border border-blue-100 animate-in fade-in">
          <h3 className="font-bold mb-3">Додати предмет</h3>
          <input placeholder="Назва" className="w-full p-3 bg-gray-50 rounded-lg mb-2" 
            value={newSubject.name} onChange={e => setNewSubject({...newSubject, name: e.target.value})} />
          <input placeholder="Викладач (Лектор)" className="w-full p-3 bg-gray-50 rounded-lg mb-2"
            value={newSubject.teacherLecture} onChange={e => setNewSubject({...newSubject, teacherLecture: e.target.value})} />
          <button onClick={handleAddSubject} className="w-full bg-blue-600 text-white py-3 rounded-lg font-bold">Зберегти</button>
        </div>
      )}

      <div className="grid gap-3">
        {subjects.map(subject => (
          <div key={subject._id} onClick={() => onNavigate('subject', subject)}
            className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 active:scale-[0.98] transition-transform cursor-pointer flex justify-between items-center">
            <div>
              <h3 className="font-bold text-lg text-gray-800">{subject.name}</h3>
              <p className="text-sm text-gray-500">{subject.teacherLecture}</p>
            </div>
            <div className="w-8 h-8 bg-gray-50 rounded-full flex items-center justify-center">
              <Icons.ChevronRight className="w-5 h-5 text-gray-400" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}