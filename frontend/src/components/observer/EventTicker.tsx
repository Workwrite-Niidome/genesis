import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../services/api';
import type { WorldEvent } from '../../types/world';

const typeConfig: Record<string, { color: string; bg: string; icon: string; hex: string }> = {
  genesis:          { color: 'text-accent', bg: 'bg-accent-dim', icon: '✦', hex: '#7c5bf5' },
  ai_birth:         { color: 'text-green',  bg: 'bg-green-dim',  icon: '◈', hex: '#34d399' },
  ai_death:         { color: 'text-orange', bg: 'bg-orange-dim', icon: '◇', hex: '#fb923c' },
  concept_created:  { color: 'text-cyan',   bg: 'bg-cyan-dim',   icon: '△', hex: '#58d5f0' },
  interaction:      { color: 'text-rose',   bg: 'bg-rose-dim',   icon: '⟡', hex: '#f472b6' },
  god_message:      { color: 'text-accent', bg: 'bg-accent-dim', icon: '⊛', hex: '#7c5bf5' },
};

export default function EventTicker() {
  const { t } = useTranslation();
  const [events, setEvents] = useState<WorldEvent[]>([]);

  useEffect(() => {
    const load = () => api.history.getEvents(20).then(setEvents).catch(console.error);
    load();
    const interval = setInterval(load, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="absolute top-20 right-4 bottom-20 w-72 z-40 pointer-events-none">
      <div className="h-full flex flex-col pointer-events-auto">
        {/* Header */}
        <div className="glass rounded-t-xl px-3 py-2 border border-border border-b-0">
          <div className="flex items-center gap-2">
            <div className="w-1 h-1 rounded-full bg-accent pulse-glow" />
            <span className="text-[10px] font-medium tracking-[0.15em] text-text-3 uppercase">
              {t('live_events')}
            </span>
            {events.length > 0 && (
              <span className="text-[9px] mono text-text-3 ml-auto">{events.length}</span>
            )}
          </div>
        </div>

        {/* Events list */}
        <div className="flex-1 glass rounded-b-xl border border-border overflow-y-auto overflow-x-hidden">
          {events.length === 0 ? (
            <div className="text-center py-8">
              <div className="relative w-8 h-8 mx-auto mb-3">
                <div className="absolute inset-0 rounded-full border border-border/50 pulse-ring" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-1 h-1 rounded-full bg-text-3" />
                </div>
              </div>
              <p className="text-text-3 text-[10px]">{t('no_events')}</p>
            </div>
          ) : (
            <div className="p-2 space-y-1">
              {events.map((event) => (
                <EventItem key={event.id} event={event} t={t} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EventItem({ event, t }: { event: WorldEvent; t: (key: string) => string }) {
  const cfg = typeConfig[event.event_type] || { color: 'text-text-3', bg: 'bg-surface-3', icon: '·', hex: '#8a8694' };
  const label = t(`event_type_${event.event_type}`);

  return (
    <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04] slide-in-right group hover:bg-white/[0.04] transition-colors">
      <div className="flex items-center gap-1.5 mb-1">
        <span className={`text-[10px] ${cfg.color}`}>{cfg.icon}</span>
        <span className={`text-[9px] font-medium uppercase tracking-wider ${cfg.color}`}>
          {label}
        </span>
        <span className="text-[8px] mono text-text-3 ml-auto opacity-60">
          T:{event.tick_number}
        </span>
      </div>
      {/* Importance bar */}
      <div className="flex items-center gap-2 mt-1.5">
        <div className="flex-1 h-[2px] bg-white/[0.04] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{
              width: `${Math.min(100, event.importance * 100)}%`,
              backgroundColor: cfg.hex,
              opacity: 0.6,
            }}
          />
        </div>
      </div>
    </div>
  );
}
