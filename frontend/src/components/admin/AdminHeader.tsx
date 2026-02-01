import { useTranslation } from 'react-i18next';
import { MessageSquare, PanelRight, Eye, Grid3x3 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useWorldStore } from '../../stores/worldStore';
import { useUIStore } from '../../stores/uiStore';

export default function AdminHeader() {
  const { t } = useTranslation();
  const { tickNumber, aiCount, conceptCount, godAiPhase } = useWorldStore();
  const { sidebarOpen, toggleSidebar, toggleChat, showGrid, toggleGrid } = useUIStore();

  return (
    <header className="h-11 flex items-center justify-between px-5 border-b border-border bg-surface/80 backdrop-blur-xl z-50 select-none glow-line">
      {/* Left: Logo + Admin badge */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div className="w-1.5 h-1.5 rounded-full bg-accent" />
            <div className="absolute inset-0 w-1.5 h-1.5 rounded-full bg-accent pulse-glow" />
          </div>
          <span className="text-sm font-semibold tracking-[0.2em] text-text">GENESIS</span>
        </div>
        <span className="badge bg-orange-dim text-orange text-[9px] tracking-[0.1em] uppercase font-semibold">
          {t('admin')}
        </span>
        <div className="w-px h-3.5 bg-border hidden sm:block" />
        <span className="text-[10px] text-text-3 hidden sm:block tracking-wide">{t('app_subtitle')}</span>
      </div>

      {/* Center: Stats */}
      <div className="flex items-center gap-5">
        <Stat label={t('tick')} value={tickNumber.toLocaleString()} color="text-cyan" />
        <Stat label={t('ais')} value={String(aiCount)} color="text-green" />
        <Stat label={t('concepts')} value={String(conceptCount)} color="text-accent" />
        <div className="badge bg-surface-3 text-text-2 text-[10px]">
          <div className={`w-1 h-1 rounded-full ${godAiPhase === 'post_genesis' ? 'bg-green' : 'bg-orange'}`} />
          {godAiPhase === 'pre_genesis' ? t('pre_genesis') : t('post_genesis')}
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-0.5">
        <Link
          to="/"
          className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-text-3 hover:text-text-2 hover:bg-surface-3/60 transition-all duration-150"
          title={t('observer_view')}
        >
          <Eye size={13} />
          <span className="text-[10px]">{t('observer_view')}</span>
        </Link>
        <HeaderBtn onClick={toggleGrid} title="Toggle grid">
          <Grid3x3 size={13} className={showGrid ? 'text-accent' : ''} />
        </HeaderBtn>
        <HeaderBtn onClick={toggleChat} title={t('chat')}>
          <MessageSquare size={13} />
        </HeaderBtn>
        <HeaderBtn onClick={toggleSidebar}>
          <PanelRight size={13} className={sidebarOpen ? 'text-accent' : ''} />
        </HeaderBtn>
      </div>
    </header>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex items-center gap-1.5 text-[11px]">
      <span className="text-text-3">{label}</span>
      <span className={`mono font-medium ${color}`}>{value}</span>
    </div>
  );
}

function HeaderBtn({ children, onClick, title }: { children: React.ReactNode; onClick: () => void; title?: string }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-text-3 hover:text-text-2 hover:bg-surface-3/60 transition-all duration-150"
    >
      {children}
    </button>
  );
}
