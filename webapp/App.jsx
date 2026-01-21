import { useState, useEffect } from 'react';
import Home from './components/Home';
import Schedule from './components/Schedule';
import QueueView from './components/QueueView';
import SubjectView from './components/SubjectView';
import Homework from './components/Homework'; // Assuming existing
import TopicsView from './components/TopicsView'; // Assuming existing
import { Icons } from './utils/icons';

export default function App() {
  const [view, setView] = useState('home'); // home, schedule, homework
  const [stack, setStack] = useState([]); // Navigation stack for nested views
  const [user, setUser] = useState(null);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
        tg.ready();
        tg.expand();
        // Capture full name logic
        const u = tg.initDataUnsafe?.user;
        if(u) {
            setUser({
                id: u.id,
                fullName: `${u.first_name} ${u.last_name || ''}`.trim(),
                username: u.username
            });
            // Update user in backend to ensure name is fresh
            fetch('/api/users/update', {
                method: 'POST',
                body: JSON.stringify({ telegramId: u.id, fullName: `${u.first_name} ${u.last_name || ''}`.trim(), username: u.username })
            });
        }
    }
  }, []);

  const navigate = (viewName, data = null) => {
    setStack([...stack, { view: viewName, data }]);
  };

  const goBack = () => {
    setStack(stack.slice(0, -1));
  };

  const currentView = stack.length > 0 ? stack[stack.length - 1] : { view: view };

  // Render Logic
  const renderContent = () => {
    switch (currentView.view) {
      case 'home': return <Home user={user} onNavigate={navigate} />;
      case 'schedule': return <Schedule onNavigate={navigate} />;
      case 'homework': return <Homework user={user} />;
      
      // Nested Views
      case 'subject': return <SubjectView subject={currentView.data} user={user} onNavigate={navigate} onBack={goBack} />;
      case 'queue': return <QueueView subject={currentView.data} user={user} onBack={goBack} />;
      case 'topics': return <TopicsView subject={currentView.data} user={user} onBack={goBack} />;
      default: return <Home user={user} onNavigate={navigate} />;
    }
  };

  // Bottom Navigation (Hidden when deep in stack)
  const showNav = stack.length === 0;

  return (
    <div className="max-w-md mx-auto min-h-screen bg-gray-50 font-sans">
      {renderContent()}
      
      {showNav && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t flex justify-around p-2 pb-4 safe-area-bottom">
          <NavBtn icon={<Icons.Home />} label="Предмети" active={view === 'home'} onClick={() => setView('home')} />
          <NavBtn icon={<Icons.Calendar />} label="Розклад" active={view === 'schedule'} onClick={() => setView('schedule')} />
          <NavBtn icon={<Icons.Clipboard />} label="ДЗ" active={view === 'homework'} onClick={() => setView('homework')} />
        </div>
      )}
    </div>
  );
}

const NavBtn = ({ icon, label, active, onClick }) => (
  <button onClick={onClick} className={`flex flex-col items-center p-2 rounded-xl transition ${active ? 'text-blue-600 bg-blue-50' : 'text-gray-400'}`}>
    {icon}
    <span className="text-[10px] font-bold mt-1">{label}</span>
  </button>
);