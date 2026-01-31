import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../services/api';
import type { WorldEvent } from '../../types/world';

const typeColors: Record<string, string> = {
  genesis: '#ce93d8',
  ai_birth: '#81c784',
  ai_death: '#ff8a65',
  concept_created: '#4fc3f7',
  interaction: '#f48fb1',
};

export default function EventsPanel() {
  const { t } = useTranslation();
  const [events, setEvents] = useState<WorldEvent[]>([]);

  useEffect(() => {
    api.history.getEvents(30).then(setEvents).catch(console.error);
    const interval = setInterval(() => {
      api.history.getEvents(30).then(setEvents).catch(console.error);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-3 fade-in">
      <h3 className="text-sm font-medium text-glow-cyan">{t('events_panel')}</h3>

      {events.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-2xl mb-3 text-text-dim">○</div>
          <p className="text-text-secondary text-xs">{t('no_events')}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {events.map((event) => (
            <div
              key={event.id}
              className="p-2.5 rounded-lg bg-void-lighter border-l-2 fade-in"
              style={{ borderColor: typeColors[event.event_type] || '#5a5470' }}
            >
              <div className="flex items-center justify-between mb-1">
                <span
                  className="text-[10px] font-mono uppercase tracking-wider"
                  style={{ color: typeColors[event.event_type] || '#9e98b0' }}
                >
                  {event.event_type}
                </span>
                <span className="text-[10px] text-text-dim">
                  T:{event.tick_number}
                </span>
              </div>
              <div className="text-xs text-text-primary">{event.title}</div>
              {event.description && (
                <div className="text-[11px] text-text-secondary mt-0.5 line-clamp-2">
                  {event.description}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
