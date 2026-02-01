import { useTranslation } from 'react-i18next';
import { Info, Zap, BarChart2, Sparkles } from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import InfoPanel from '../panels/InfoPanel';
import EventsPanel from '../panels/EventsPanel';
import StatsPanel from '../panels/StatsPanel';
import GodAIConsole from '../admin/GodAIConsole';

const tabs = [
  { id: 'info' as const, icon: Info, labelKey: 'info_panel' },
  { id: 'events' as const, icon: Zap, labelKey: 'events_panel' },
  { id: 'stats' as const, icon: BarChart2, labelKey: 'stats_panel' },
  { id: 'god' as const, icon: Sparkles, labelKey: 'god_console' },
];

export default function Sidebar() {
  const { t } = useTranslation();
  const { activePanel, setPanel } = useUIStore();

  return (
    <div className="h-full flex flex-col bg-surface border-l border-border">
      {/* Tabs */}
      <div className="flex border-b border-border relative">
        {tabs.map(({ id, icon: Icon, labelKey }) => (
          <button
            key={id}
            onClick={() => setPanel(id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-3 text-[11px] font-medium transition-all duration-200 relative ${
              activePanel === id
                ? 'text-text'
                : 'text-text-3 hover:text-text-2'
            }`}
          >
            <Icon size={13} className={activePanel === id ? 'text-accent' : ''} />
            <span className="hidden lg:inline">{t(labelKey)}</span>
            {activePanel === id && (
              <div className="absolute bottom-0 left-3 right-3 h-[2px] bg-accent rounded-full
                            shadow-[0_0_8px_rgba(124,91,245,0.4)]" />
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activePanel === 'info' && <InfoPanel />}
        {activePanel === 'events' && <EventsPanel />}
        {activePanel === 'stats' && <StatsPanel />}
        {activePanel === 'god' && <GodAIConsole />}
      </div>
    </div>
  );
}
