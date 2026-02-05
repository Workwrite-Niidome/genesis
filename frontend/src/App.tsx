import { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import './services/i18n';
import { useWorldStore } from './stores/worldStore';
import { useAIStore } from './stores/aiStore';
import { connectSocket, disconnectSocket } from './services/socket';
import ObserverView from './pages/ObserverView';
import AdminView from './pages/AdminView';
import { WorldViewV3 } from './components/world/WorldViewV3';

function App() {
  const fetchState = useWorldStore((s) => s.fetchState);
  const fetchAIs = useAIStore((s) => s.fetchAIs);

  useEffect(() => {
    // Initial fetch
    fetchState();
    fetchAIs();

    // Connect WebSocket for real-time updates
    try {
      connectSocket();
    } catch (e) {
      console.warn('WebSocket connection failed, using polling fallback:', e);
    }

    // Poll for updates (fallback + supplementary)
    const interval = setInterval(() => {
      fetchState();
      fetchAIs();
    }, 3000);

    return () => {
      clearInterval(interval);
      disconnectSocket();
    };
  }, [fetchState, fetchAIs]);

  return (
    <Routes>
      <Route path="/" element={<ObserverView />} />
      <Route path="/admin" element={<AdminView />} />
      <Route path="/v3" element={
        <div className="w-screen h-screen">
          <WorldViewV3 />
        </div>
      } />
    </Routes>
  );
}

export default App;
