import { useUIStore } from '../../stores/uiStore';
import Header from './Header';
import Sidebar from './Sidebar';
import WorldCanvas from '../world/WorldCanvas';
import ChatPanel from '../chat/ChatPanel';
import TimelineBar from '../timeline/TimelineBar';

export default function MainLayout() {
  const { sidebarOpen, chatOpen } = useUIStore();

  return (
    <div className="h-screen w-screen flex flex-col bg-void overflow-hidden">
      <Header />

      <div className="flex-1 flex overflow-hidden relative">
        {/* World Canvas - main area */}
        <div className="flex-1 relative">
          <WorldCanvas />
        </div>

        {/* Sidebar */}
        <div
          className={`transition-all duration-300 ease-in-out ${
            sidebarOpen ? 'w-80' : 'w-0'
          } overflow-hidden`}
        >
          <div className="w-80 h-full">
            <Sidebar />
          </div>
        </div>
      </div>

      {/* Timeline */}
      <TimelineBar />

      {/* Chat Panel */}
      <div
        className={`absolute bottom-12 left-0 right-0 transition-all duration-300 ease-in-out z-40 ${
          chatOpen ? 'h-64' : 'h-0'
        } overflow-hidden`}
        style={{ right: sidebarOpen ? '320px' : '0' }}
      >
        <ChatPanel />
      </div>
    </div>
  );
}
