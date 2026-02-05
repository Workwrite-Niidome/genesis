/**
 * EventFeed — Real-time event log for the GENESIS v3 observer view.
 *
 * Displays conflict, speech, death, god_crisis, and god_observation events
 * as they stream in via Socket.IO, stored in worldStoreV3.recentEvents.
 */
import { useEffect, useRef } from 'react';
import { Swords, MessageCircle, Skull, Zap, Eye } from 'lucide-react';
import { useWorldStoreV3 } from '../../stores/worldStoreV3';
import type { WorldEvent } from '../../stores/worldStoreV3';

// ── Per-type visual config ──────────────────────────────────
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
};

// ── Summary text per event type ─────────────────────────────
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

// ── Component ───────────────────────────────────────────────
export function EventFeed() {
  const recentEvents = useWorldStoreV3((s) => s.recentEvents);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [recentEvents.length]);

  return (
    <div className="absolute top-14 left-4 w-80 max-h-[calc(100vh-160px)] flex flex-col bg-black/60 backdrop-blur-sm rounded-lg border border-white/[0.06] z-10 pointer-events-auto">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[0.06]">
        <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
        <span className="text-[10px] font-medium tracking-[0.15em] text-white/60 uppercase">
          Live Events
        </span>
        <span className="text-[9px] font-mono text-white/30 ml-auto">
          {recentEvents.length}
        </span>
      </div>

      {/* Event list */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto overflow-x-hidden p-2 space-y-1">
        {recentEvents.length === 0 ? (
          <div className="text-center py-6">
            <div className="relative w-6 h-6 mx-auto mb-2">
              <div className="absolute inset-0 rounded-full border border-white/10 animate-ping opacity-30" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-1 h-1 rounded-full bg-white/30" />
              </div>
            </div>
            <p className="text-white/30 text-[10px]">Waiting for events...</p>
          </div>
        ) : (
          recentEvents
            .slice()
            .reverse()
            .map((event) => <EventItem key={event.id} event={event} />)
        )}
      </div>
    </div>
  );
}

function EventItem({ event }: { event: WorldEvent }) {
  const cfg = eventConfig[event.type];
  const Icon = cfg.icon;
  const text = summarise(event);

  return (
    <div
      className={`p-2 rounded-lg ${cfg.bg} border ${cfg.border} transition-colors hover:bg-white/[0.04]`}
    >
      <div className="flex items-center gap-1.5 mb-0.5">
        <Icon size={11} className={cfg.color} />
        <span className={`text-[9px] font-medium uppercase tracking-wider ${cfg.color}`}>
          {cfg.label}
        </span>
        {event.tick > 0 && (
          <span className="text-[8px] font-mono text-white/30 ml-auto">
            T:{event.tick}
          </span>
        )}
      </div>
      <p className="text-[10px] text-white/70 leading-relaxed line-clamp-2">
        {text}
      </p>
    </div>
  );
}
