import { useTranslation } from 'react-i18next';
import { Globe, Settings, MessageCircle, PanelRightOpen, PanelRightClose } from 'lucide-react';
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

  const phaseLabel =
    godAiPhase === 'pre_genesis' ? t('pre_genesis') : t('post_genesis');

  return (
    <header className="h-12 flex items-center justify-between px-4 glass-panel rounded-none border-t-0 border-x-0 z-50">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-bold tracking-widest glow-text text-glow-cyan">
          GENESIS
        </h1>
        <span className="text-xs text-text-secondary hidden sm:block">
          {t('app_subtitle')}
        </span>
      </div>

      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-4 text-text-secondary">
          <span>
            {t('tick')}:{' '}
            <span className="text-glow-cyan font-mono">{tickNumber.toLocaleString()}</span>
          </span>
          <span>
            {t('ais')}:{' '}
            <span className="text-glow-green font-mono">{aiCount}</span>
          </span>
          <span>
            {t('concepts')}:{' '}
            <span className="text-glow-purple font-mono">{conceptCount}</span>
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-void-lighter border border-panel-border">
            {phaseLabel}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={toggleLang}
          className="p-1.5 rounded-lg hover:bg-panel-hover transition-colors text-text-secondary hover:text-glow-cyan"
          title={t('language')}
        >
          <Globe size={16} />
          <span className="text-xs ml-1 uppercase">{language}</span>
        </button>
        <button
          onClick={toggleChat}
          className="p-1.5 rounded-lg hover:bg-panel-hover transition-colors text-text-secondary hover:text-glow-cyan"
          title={t('chat')}
        >
          <MessageCircle size={16} />
        </button>
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg hover:bg-panel-hover transition-colors text-text-secondary hover:text-glow-cyan"
        >
          {sidebarOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
        </button>
      </div>
    </header>
  );
}
