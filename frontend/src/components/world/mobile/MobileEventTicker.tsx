/**
 * MobileEventTicker — Compact floating event feed for the mobile World tab.
 *
 * Shows the 3 most recent events as small translucent cards overlaying
 * the 3D canvas. Auto-fades older events. Positioned top-left below the top bar.
 */
import { Swords, MessageCircle, Skull, Zap, Eye, Crown } from 'lucide-react';
import type { WorldEvent } from '../../../stores/worldStoreV3';

const iconMap: Record<WorldEvent['type'], typeof Swords> = {
  conflict: Swords,
  speech: MessageCircle,
  death: Skull,
  god_crisis: Zap,
  god_observation: Eye,
  god_succession: Crown,
};

const colorMap: Record<WorldEvent['type'], string> = {
  conflict: 'text-orange-400',
  speech: 'text-blue-400',
  death: 'text-gray-400',
  god_crisis: 'text-purple-400',
  god_observation: 'text-amber-400',
  god_succession: 'text-purple-400',
};

function summariseShort(event: WorldEvent): string {
  const d = event.data;
  switch (event.type) {
    case 'conflict': {
      const winner = d.winner ?? '?';
      const loser = d.loser ?? '?';
      return `${winner} vs ${loser}`;
    }
    case 'speech': {
      const name = d.entityName ?? d.name ?? '?';
      const text = (d.text ?? '').slice(0, 40);
      return `${name}: ${text}${(d.text ?? '').length > 40 ? '...' : ''}`;
    }
    case 'death':
      return `${d.name ?? d.entityName ?? 'Entity'} died`;
    case 'god_crisis':
      return (d.crisis_name ?? d.description ?? 'Crisis').slice(0, 50);
    case 'god_observation':
      return (d.excerpt ?? d.content ?? 'God speaks...').slice(0, 50);
    case 'god_succession':
      return `${d.new_god ?? 'New'} ascends`;
    default:
      return event.type;
  }
}

interface MobileEventTickerProps {
  events: WorldEvent[];
}

export function MobileEventTicker({ events }: MobileEventTickerProps) {
  const latest = events.slice(-3).reverse();

  return (
    <div className="absolute left-2 right-16 z-10 pointer-events-none space-y-1" style={{ top: 56 }}>
      {latest.map((event, idx) => {
        const Icon = iconMap[event.type] || Zap;
        const color = colorMap[event.type] || 'text-white/50';
        const opacity = idx === 0 ? 'opacity-90' : idx === 1 ? 'opacity-60' : 'opacity-35';

        return (
          <div
            key={event.id}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-black/50 backdrop-blur-sm ${opacity} transition-opacity duration-500`}
          >
            <Icon size={11} className={`${color} flex-shrink-0`} />
            <span className="text-[11px] text-white/70 truncate">
              {summariseShort(event)}
            </span>
            {event.tick > 0 && (
              <span className="text-[10px] font-mono text-white/25 ml-auto flex-shrink-0">
                T:{event.tick}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
