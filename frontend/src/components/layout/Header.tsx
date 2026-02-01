import { useTranslation } from 'react-i18next';
import { Globe, MessageSquare, PanelRight } from 'lucide-react';
import { useWorldStore } from '../../stores/worldStore';
import { useUIStore } from '../../stores/uiStore';

export default function Header() {
  const { t, i18n } = useTranslation();
  const { tickNumber, aiCount, conceptCount, godAiPhase } = useWorldStore();
  const { sidebarOpen, toggleSidebar, toggleChat, language, setLanguage } = useUIStore();

  const toggleLang = () => {
    const next = language === 'en' ? 'ja' : 'en';
    setLanguage(next);
    i18n.changeLanguage(next);
  };

  return (
    <header className="h-11 flex items-center justify-between px-5 border-b border-border bg-surface/80 backdrop-blur-xl z-50 select-none">
      {/* Left: Logo */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-accent pulse-glow" />
          <span className="text-sm font-semibold tracking-[0.2em] text-text">GENESIS</span>
        </div>
        <span className="text-[11px] text-text-3 hidden sm:block">{t('app_subtitle')}</span>
      </div>

      {/* Center: Stats */}
      <div className="flex items-center gap-5">
        <Stat label={t('tick')} value={tickNumber.toLocaleString()} color="text-cyan" />
        <Stat label={t('ais')} value={String(aiCount)} color="text-green" />
        <Stat label={t('concepts')} value={String(conceptCount)} color="text-accent" />
        <div className="badge bg-surface-3 text-text-2">
          <div className={`w-1 h-1 rounded-full ${godAiPhase === 'post_genesis' ? 'bg-green' : 'bg-orange'}`} />
          {godAiPhase === 'pre_genesis' ? t('pre_genesis') : t('post_genesis')}
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-1">
        <HeaderBtn onClick={toggleLang} title={t('language')}>
          <Globe size={14} />
          <span className="text-[10px] uppercase">{language}</span>
        </HeaderBtn>
        <HeaderBtn onClick={toggleChat} title={t('chat')}>
          <MessageSquare size={14} />
        </HeaderBtn>
        <HeaderBtn onClick={toggleSidebar}>
          <PanelRight size={14} className={sidebarOpen ? 'text-accent' : ''} />
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
      className="flex items-center gap-1 px-2 py-1 rounded-md text-text-2 hover:text-text hover:bg-surface-3 transition-colors duration-150"
    >
      {children}
    </button>
  );
}
