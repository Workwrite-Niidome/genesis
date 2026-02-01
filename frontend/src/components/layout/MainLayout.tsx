import { useUIStore } from '../../stores/uiStore';
import Header from './Header';
import Sidebar from './Sidebar';
import WorldCanvas from '../world/WorldCanvas';
import ChatPanel from '../chat/ChatPanel';
import TimelineBar from '../timeline/TimelineBar';

export default function MainLayout() {
  const { sidebarOpen, chatOpen } = useUIStore();

  return (
    <div className="h-screen w-screen flex flex-col bg-bg overflow-hidden">
      {/* Film grain / noise */}
      <div className="noise-overlay" />

      <Header />

      <div className="flex-1 flex overflow-hidden relative">
        {/* Canvas */}
        <div className="flex-1 relative">
          <WorldCanvas />

          {/* Chat overlay at bottom */}
          <div
            className={`absolute bottom-0 left-0 right-0 transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] z-40 ${
              chatOpen ? 'h-72 opacity-100' : 'h-0 opacity-0 pointer-events-none'
            } overflow-hidden`}
          >
            <ChatPanel />
          </div>
        </div>

        {/* Sidebar */}
        <div
          className={`transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] overflow-hidden ${
            sidebarOpen ? 'w-[340px]' : 'w-0'
          }`}
        >
          <div className="w-[340px] h-full">
            <Sidebar />
          </div>
        </div>
      </div>

      <TimelineBar />
    </div>
  );
}
