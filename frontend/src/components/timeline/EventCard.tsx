import {
  Brain,
  Palette,
  Eye,
  Skull,
  Users,
  Swords,
  Building2,
  Zap,
  Sparkles,
  MessageCircle,
  Lightbulb,
} from 'lucide-react';
import { useDetailStore } from '../../stores/detailStore';

// ---------------------------------------------------------------------------
// Event type configuration
// ---------------------------------------------------------------------------

export const EVENT_TYPE_CONFIG: Record<
  string,
  { label: string; color: string; bgColor: string; borderColor: string; hex: string; icon: typeof Zap }
> = {
  entity_thought:       { label: 'Thought',          color: 'text-blue-400',   bgColor: 'bg-blue-400/10',   borderColor: 'border-blue-400/20',   hex: '#60a5fa', icon: Brain },
  artifact_created:     { label: 'Artifact Created', color: 'text-purple-400', bgColor: 'bg-purple-400/10', borderColor: 'border-purple-400/20', hex: '#c084fc', icon: Palette },
  god_observation:      { label: 'God Observation',  color: 'text-amber-400',  bgColor: 'bg-amber-400/10',  borderColor: 'border-amber-400/20',  hex: '#fbbf24', icon: Eye },
  god_message:          { label: 'God Message',      color: 'text-amber-300',  bgColor: 'bg-amber-300/10',  borderColor: 'border-amber-300/20',  hex: '#fcd34d', icon: Eye },
  entity_died:          { label: 'Entity Died',      color: 'text-red-400',    bgColor: 'bg-red-400/10',    borderColor: 'border-red-400/20',    hex: '#f87171', icon: Skull },
  ai_death:             { label: 'Entity Died',      color: 'text-red-400',    bgColor: 'bg-red-400/10',    borderColor: 'border-red-400/20',    hex: '#f87171', icon: Skull },
  organization_formed:  { label: 'Organization',     color: 'text-green-400',  bgColor: 'bg-green-400/10',  borderColor: 'border-green-400/20',  hex: '#4ade80', icon: Users },
  conflict:             { label: 'Conflict',         color: 'text-orange-400', bgColor: 'bg-orange-400/10', borderColor: 'border-orange-400/20', hex: '#fb923c', icon: Swords },
  building:             { label: 'Building',         color: 'text-gray-400',   bgColor: 'bg-gray-400/10',   borderColor: 'border-gray-400/20',   hex: '#9ca3af', icon: Building2 },
  ai_birth:             { label: 'Entity Born',      color: 'text-emerald-400', bgColor: 'bg-emerald-400/10', borderColor: 'border-emerald-400/20', hex: '#34d399', icon: Sparkles },
  interaction:          { label: 'Interaction',      color: 'text-pink-400',   bgColor: 'bg-pink-400/10',   borderColor: 'border-pink-400/20',   hex: '#f472b6', icon: MessageCircle },
  concept_created:      { label: 'Concept Created',  color: 'text-cyan-400',   bgColor: 'bg-cyan-400/10',   borderColor: 'border-cyan-400/20',   hex: '#22d3ee', icon: Lightbulb },
};

const DEFAULT_CONFIG = {
  label: 'Event',
  color: 'text-gray-400',
  bgColor: 'bg-gray-400/10',
  borderColor: 'border-gray-400/20',
  hex: '#9ca3af',
  icon: Zap,
};

export function getEventConfig(eventType: string) {
  return EVENT_TYPE_CONFIG[eventType] || DEFAULT_CONFIG;
}

// ---------------------------------------------------------------------------
// EventCard component
// ---------------------------------------------------------------------------

export interface WorldEventData {
  id: number | string;
  tick: number;
  actor_id?: string | null;
  actor_name?: string | null;
  event_type: string;
  action: string;
  params?: Record<string, any>;
  result?: string;
  reason?: string | null;
  position?: { x: number; y: number; z: number } | null;
  importance: number;
  created_at?: string | null;
}

interface EventCardProps {
  event: WorldEventData;
  compact?: boolean;
  style?: React.CSSProperties;
}

export default function EventCard({ event, compact = false, style }: EventCardProps) {
  const openDetail = useDetailStore((s) => s.openDetail);
  const config = getEventConfig(event.event_type);
  const Icon = config.icon;

  const handleClick = () => {
    openDetail('event', {
      id: String(event.id),
      event_type: event.event_type,
      title: event.action,
      description: event.reason || event.action,
      tick_number: event.tick,
      importance: event.importance,
      created_at: event.created_at || '',
      metadata_: {
        actor_id: event.actor_id,
        actor_name: event.actor_name,
        params: event.params,
        result: event.result,
        position: event.position,
      },
    });
  };

  if (compact) {
    return (
      <button
        onClick={handleClick}
        className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/[0.04] transition-colors text-left group"
        style={style}
      >
        <div
          className="w-1.5 h-1.5 rounded-full flex-shrink-0"
          style={{ backgroundColor: config.hex }}
        />
        <Icon size={11} className={`flex-shrink-0 ${config.color}`} />
        <span className="text-[11px] text-text-2 truncate flex-1">
          {event.action}
        </span>
        {event.actor_name && (
          <span className="text-[10px] text-text-3 truncate max-w-[80px]">
            {event.actor_name}
          </span>
        )}
        <span className="text-[10px] mono text-text-3 opacity-60 flex-shrink-0">
          T:{event.tick}
        </span>
      </button>
    );
  }

  return (
    <button
      onClick={handleClick}
      className={`w-full text-left p-3 rounded-xl border transition-all duration-200 cursor-pointer
        bg-white/[0.02] ${config.borderColor} hover:bg-white/[0.05] hover:border-white/[0.1]`}
      style={style}
    >
      {/* Header row */}
      <div className="flex items-center gap-2 mb-1.5">
        <div className={`flex-shrink-0 p-1 rounded-md ${config.bgColor}`}>
          <Icon size={12} className={config.color} />
        </div>
        <span className={`text-[10px] font-semibold uppercase tracking-wider ${config.color}`}>
          {config.label}
        </span>
        {event.actor_name && (
          <span className="text-[11px] text-text-2 truncate">
            &mdash; {event.actor_name}
          </span>
        )}
        <span className="ml-auto text-[10px] mono text-text-3 opacity-60 flex-shrink-0">
          T:{event.tick}
        </span>
      </div>

      {/* Action text */}
      <p className="text-[12px] font-medium text-text leading-relaxed mb-1">
        {event.action}
      </p>

      {/* Reason / description if present */}
      {event.reason && (
        <p className="text-[11px] text-text-2 leading-relaxed line-clamp-2 mb-1.5">
          {event.reason}
        </p>
      )}

      {/* Footer: importance bar + result */}
      <div className="flex items-center gap-2 mt-1.5">
        <div className="flex-1 h-[2px] bg-white/[0.04] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.min(100, event.importance * 100)}%`,
              backgroundColor: config.hex,
              opacity: 0.6,
            }}
          />
        </div>
        <span className="text-[9px] mono text-text-3 opacity-50 flex-shrink-0">
          {(event.importance * 100).toFixed(0)}%
        </span>
        {event.result && event.result !== 'accepted' && (
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-orange-400/10 text-orange-400 border border-orange-400/20">
            {event.result}
          </span>
        )}
      </div>
    </button>
  );
}
