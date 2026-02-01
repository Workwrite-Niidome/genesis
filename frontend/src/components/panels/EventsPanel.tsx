import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../services/api';
import type { WorldEvent } from '../../types/world';

const typeConfig: Record<string, { color: string; bg: string }> = {
  genesis: { color: 'text-accent', bg: 'bg-accent-dim' },
  ai_birth: { color: 'text-green', bg: 'bg-green-dim' },
  ai_death: { color: 'text-orange', bg: 'bg-orange-dim' },
  concept_created: { color: 'text-cyan', bg: 'bg-cyan-dim' },
  interaction: { color: 'text-rose', bg: 'bg-rose-dim' },
};

export default function EventsPanel() {
  const { t } = useTranslation();
  const [events, setEvents] = useState<WorldEvent[]>([]);

  useEffect(() => {
    const load = () => api.history.getEvents(30).then(setEvents).catch(console.error);
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-3 fade-in">
      <h3 className="text-xs font-medium text-text">{t('events_panel')}</h3>

      {events.length === 0 ? (
        <div className="text-center py-12">
          <div className="w-10 h-10 rounded-full border border-border mx-auto mb-4 flex items-center justify-center">
            <div className="w-1 h-1 rounded-full bg-text-3" />
          </div>
          <p className="text-text-3 text-[11px]">{t('no_events')}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {events.map((event) => {
            const cfg = typeConfig[event.event_type] || { color: 'text-text-3', bg: 'bg-surface-3' };
            return (
              <div
                key={event.id}
                className="p-3 rounded-lg bg-surface-2 border border-border fade-in"
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span className={`badge ${cfg.bg} ${cfg.color} text-[9px]`}>
                    {event.event_type.replace('_', ' ')}
                  </span>
                  <span className="text-[10px] mono text-text-3 ml-auto">
                    T:{event.tick_number}
                  </span>
                </div>
                <div className="text-[11px] text-text leading-relaxed">{event.title}</div>
                {event.description && (
                  <div className="text-[11px] text-text-3 mt-1 line-clamp-2 leading-relaxed">
                    {event.description}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
