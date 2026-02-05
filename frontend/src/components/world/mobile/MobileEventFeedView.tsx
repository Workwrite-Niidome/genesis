/**
 * MobileEventFeedView — Full-height event feed for mobile (Events tab).
 *
 * Event rows: 48px+ height
 * Text: 12px labels, 14px summaries (up from 9-10px desktop)
 * Live indicator, auto-scroll on new events
 */
import { useEffect, useRef } from 'react';
import { Swords, MessageCircle, Skull, Zap, Eye, Crown } from 'lucide-react';
import { useWorldStoreV3 } from '../../../stores/worldStoreV3';
import type { WorldEvent } from '../../../stores/worldStoreV3';

const eventConfig: Record<
  WorldEvent['type'],
  { icon: typeof Swords; color: string; bg: string; border: string; label: string }
> = {
  conflict: {
    icon: Swords,
    color: 'text-orange-400',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/20',
    label: 'Conflict',
  },
  speech: {
    icon: MessageCircle,
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20',
    label: 'Speech',
  },
  death: {
    icon: Skull,
    color: 'text-gray-400',
    bg: 'bg-gray-500/10',
    border: 'border-gray-500/20',
    label: 'Death',
  },
  god_crisis: {
    icon: Zap,
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/20',
    label: 'God Crisis',
  },
  god_observation: {
    icon: Eye,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/20',
    label: 'God',
  },
  god_succession: {
    icon: Crown,
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/20',
    label: 'Succession',
  },
};

function summarise(event: WorldEvent): string {
  const d = event.data;
  switch (event.type) {
    case 'conflict': {
      const winner = d.winner ?? 'unknown';
      const loser = d.loser ?? 'unknown';
      const kind = d.type ?? 'conflict';
      return `${winner} defeated ${loser} in a ${kind}`;
    }
    case 'speech': {
      const name = d.entityName ?? d.name ?? 'Entity';
      const text = d.text ?? '';
      return `${name}: ${text}`;
    }
    case 'death': {
      const name = d.name ?? d.entityName ?? 'An entity';
      return `${name} has died`;
    }
    case 'god_crisis': {
      return d.description ?? d.crisis_name ?? 'A divine crisis occurred';
    }
    case 'god_observation': {
      return d.excerpt ?? d.content ?? 'God speaks...';
    }
    default:
      return JSON.stringify(d).slice(0, 80);
  }
}

export function MobileEventFeedView() {
  const recentEvents = useWorldStoreV3(s => s.recentEvents);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to top (newest first) on new events
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [recentEvents.length]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/[0.06] flex-shrink-0">
        <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
        <span className="text-[12px] font-medium tracking-[0.12em] text-white/60 uppercase">
          Live Events
        </span>
        <span className="text-[12px] font-mono text-white/30 ml-auto">
          {recentEvents.length}
        </span>
      </div>

      {/* Event list */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto overflow-x-hidden p-3 space-y-1.5">
        {recentEvents.length === 0 ? (
          <div className="text-center py-16">
            <div className="relative w-8 h-8 mx-auto mb-3">
              <div className="absolute inset-0 rounded-full border border-white/10 animate-ping opacity-30" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-white/30" />
              </div>
            </div>
            <p className="text-white/30 text-[13px]">Waiting for events...</p>
          </div>
        ) : (
          recentEvents
            .slice()
            .reverse()
            .map((event) => {
              const cfg = eventConfig[event.type];
              const Icon = cfg.icon;
              const text = summarise(event);

              return (
                <div
                  key={event.id}
                  className={`p-3 rounded-lg ${cfg.bg} border ${cfg.border}`}
                  style={{ minHeight: 48 }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Icon size={13} className={cfg.color} />
                    <span className={`text-[12px] font-medium uppercase tracking-wider ${cfg.color}`}>
                      {cfg.label}
                    </span>
                    {event.tick > 0 && (
                      <span className="text-[11px] font-mono text-white/30 ml-auto">
                        T:{event.tick}
                      </span>
                    )}
                  </div>
                  <p className="text-[14px] text-white/70 leading-relaxed line-clamp-3">
                    {text}
                  </p>
                </div>
              );
            })
        )}
      </div>
    </div>
  );
}
