import { useUIStore } from '../stores/uiStore';
import { useAuthStore } from '../stores/authStore';
import AdminHeader from '../components/admin/AdminHeader';
import AdminLoginForm from '../components/admin/AdminLoginForm';
import Sidebar from '../components/layout/Sidebar';
import WorldCanvas from '../components/world/WorldCanvas';
import ChatPanel from '../components/chat/ChatPanel';
import TimelineBar from '../components/timeline/TimelineBar';

export default function AdminView() {
  const { sidebarOpen, chatOpen } = useUIStore();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (!isAuthenticated) {
    return <AdminLoginForm />;
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-bg overflow-hidden">
      {/* Film grain / noise */}
      <div className="noise-overlay" />

      <AdminHeader />

      <div className="flex-1 flex overflow-hidden relative">
        {/* Canvas */}
        <div className="flex-1 relative">
          <WorldCanvas showGenesis={true} />

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
