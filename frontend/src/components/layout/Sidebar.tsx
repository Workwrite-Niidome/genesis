import { useTranslation } from 'react-i18next';
import { Info, Zap, BarChart3, Sparkles } from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import InfoPanel from '../panels/InfoPanel';
import EventsPanel from '../panels/EventsPanel';
import StatsPanel from '../panels/StatsPanel';
import GodAIConsole from '../admin/GodAIConsole';

const tabs = [
  { id: 'info' as const, icon: Info, labelKey: 'info_panel' },
  { id: 'events' as const, icon: Zap, labelKey: 'events_panel' },
  { id: 'stats' as const, icon: BarChart3, labelKey: 'stats_panel' },
  { id: 'god' as const, icon: Sparkles, labelKey: 'god_console' },
];

export default function Sidebar() {
  const { t } = useTranslation();
  const { activePanel, setPanel } = useUIStore();

  return (
    <div className="h-full flex flex-col glass-panel rounded-none border-y-0 border-r-0">
      {/* Tab bar */}
      <div className="flex border-b border-panel-border">
        {tabs.map(({ id, icon: Icon, labelKey }) => (
          <button
            key={id}
            onClick={() => setPanel(id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs transition-all ${
              activePanel === id
                ? 'text-glow-cyan border-b-2 border-glow-cyan bg-panel-hover'
                : 'text-text-secondary hover:text-text-primary hover:bg-panel-hover'
            }`}
            title={t(labelKey)}
          >
            <Icon size={14} />
            <span className="hidden xl:inline">{t(labelKey)}</span>
          </button>
        ))}
      </div>

      {/* Panel content */}
      <div className="flex-1 overflow-y-auto p-3">
        {activePanel === 'info' && <InfoPanel />}
        {activePanel === 'events' && <EventsPanel />}
        {activePanel === 'stats' && <StatsPanel />}
        {activePanel === 'god' && <GodAIConsole />}
      </div>
    </div>
  );
}
