import { useState } from 'react';
import { Icons } from '../utils/icons';

export default function SubjectView({ subject, user, onNavigate, onBack }) {
  
  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <div className="bg-white p-4 shadow-sm sticky top-0 z-10 flex items-center gap-3">
        <button onClick={onBack} className="p-2 -ml-2 text-gray-600"><Icons.ArrowLeft /></button>
        <h1 className="font-bold text-xl truncate">{subject.name}</h1>
      </div>

      <div className="p-4 space-y-4">
        {/* Info Card */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
          <div className="flex items-start gap-3 mb-4">
            <div className="p-3 bg-blue-50 rounded-xl text-blue-600"><Icons.Info /></div>
            <div>
              <p className="text-sm text-gray-500">Лектор</p>
              <p className="font-semibold">{subject.teacherLecture || 'Не вказано'}</p>
              <p className="text-sm text-gray-500 mt-2">Практик</p>
              <p className="font-semibold">{subject.teacherPractice || 'Не вказано'}</p>
            </div>
          </div>
          {subject.links && subject.links.map((link, i) => (
             <a key={i} href={link.url} target="_blank" className="block text-blue-600 text-sm mb-1 underline">{link.name}</a>
          ))}
        </div>

        {/* Action Grid */}
        <div className="grid grid-cols-2 gap-3">
          <button onClick={() => onNavigate('queue', subject)} 
            className="p-4 bg-white rounded-2xl shadow-sm border border-gray-100 flex flex-col items-center justify-center gap-2 hover:bg-gray-50 transition">
            <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center text-purple-600">
              <Icons.Users className="w-6 h-6" />
            </div>
            <span className="font-bold text-gray-700">Черга</span>
            <span className="text-xs text-gray-400">Здача лаб</span>
          </button>

          <button onClick={() => onNavigate('topics', subject)}
            className="p-4 bg-white rounded-2xl shadow-sm border border-gray-100 flex flex-col items-center justify-center gap-2 hover:bg-gray-50 transition">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center text-green-600">
              <Icons.Book className="w-6 h-6" />
            </div>
            <span className="font-bold text-gray-700">Теми</span>
            <span className="text-xs text-gray-400">Реферати</span>
          </button>
        </div>
      </div>
    </div>
  );
}