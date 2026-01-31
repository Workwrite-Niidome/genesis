import { useEffect } from 'react';
import './services/i18n';
import MainLayout from './components/layout/MainLayout';
import { useWorldStore } from './stores/worldStore';
import { useAIStore } from './stores/aiStore';

function App() {
  const fetchState = useWorldStore((s) => s.fetchState);
  const fetchAIs = useAIStore((s) => s.fetchAIs);

  useEffect(() => {
    // Initial fetch
    fetchState();
    fetchAIs();

    // Poll for updates
    const interval = setInterval(() => {
      fetchState();
      fetchAIs();
    }, 3000);

    return () => clearInterval(interval);
  }, [fetchState, fetchAIs]);

  return <MainLayout />;
}

export default App;
