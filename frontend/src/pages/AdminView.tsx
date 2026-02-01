import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { useUIStore } from '../stores/uiStore';
import { useAuthStore } from '../stores/authStore';
import { useIsMobile } from '../hooks/useIsMobile';
import AdminHeader from '../components/admin/AdminHeader';
import AdminLoginForm from '../components/admin/AdminLoginForm';
import Sidebar from '../components/layout/Sidebar';
import WorldCanvas from '../components/world/WorldCanvas';
import ChatPanel from '../components/chat/ChatPanel';
import TimelineBar from '../components/timeline/TimelineBar';

export default function AdminView() {
  const { sidebarOpen, chatOpen, toggleSidebar } = useUIStore();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isMobile = useIsMobile();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  if (!isAuthenticated) {
    return <AdminLoginForm />;
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-bg overflow-hidden">
      {/* Film grain / noise */}
      <div className="noise-overlay" />

      <AdminHeader
        onMenuToggle={isMobile ? () => setMobileSidebarOpen(!mobileSidebarOpen) : undefined}
        isMobile={isMobile}
      />

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

        {/* Sidebar - desktop */}
        {!isMobile && (
          <div
            className={`transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] overflow-hidden ${
              sidebarOpen ? 'w-[340px]' : 'w-0'
            }`}
          >
            <div className="w-[340px] h-full">
              <Sidebar />
            </div>
          </div>
        )}

        {/* Sidebar - mobile overlay */}
        {isMobile && mobileSidebarOpen && (
          <>
            <div
              className="fixed inset-0 bg-black/60 z-50"
              onClick={() => setMobileSidebarOpen(false)}
            />
            <div className="fixed top-0 right-0 bottom-0 w-[300px] z-50 bg-surface border-l border-border shadow-[−8px_0_40px_rgba(0,0,0,0.5)] fade-in">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <span className="text-[12px] font-semibold text-text tracking-wider">PANELS</span>
                <button
                  onClick={() => setMobileSidebarOpen(false)}
                  className="p-1.5 rounded-lg hover:bg-white/[0.08] text-text-3"
                >
                  <X size={16} />
                </button>
              </div>
              <div className="h-[calc(100%-48px)]">
                <Sidebar />
              </div>
            </div>
          </>
        )}
      </div>

      <TimelineBar />
    </div>
  );
}
