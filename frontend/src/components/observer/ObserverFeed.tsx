import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Brain, Radio, Eye, Lightbulb, MessageCircle, Compass } from 'lucide-react';
import { useThoughtStore } from '../../stores/thoughtStore';
import { useAIStore } from '../../stores/aiStore';
import { useDetailStore } from '../../stores/detailStore';
import { api } from '../../services/api';
import type { AIThought, WorldEvent } from '../../types/world';

type Tab = 'thoughts' | 'events';

const thoughtIcons: Record<string, typeof Brain> = {
  reflection: Brain,
  reaction: MessageCircle,
  intention: Lightbulb,
  observation: Eye,
};

const thoughtColors: Record<string, string> = {
  reflection: 'text-accent',
  reaction: 'text-rose',
  intention: 'text-cyan',
  observation: 'text-green',
};

const eventConfig: Record<string, { color: string; icon: string; hex: string }> = {
  genesis:              { color: 'text-accent', icon: '✦', hex: '#7c5bf5' },
  ai_birth:             { color: 'text-green',  icon: '◈', hex: '#34d399' },
  ai_death:             { color: 'text-orange', icon: '◇', hex: '#fb923c' },
  concept_created:      { color: 'text-cyan',   icon: '△', hex: '#58d5f0' },
  interaction:          { color: 'text-rose',   icon: '⟡', hex: '#f472b6' },
  god_message:          { color: 'text-accent', icon: '⊛', hex: '#7c5bf5' },
  god_observation:      { color: 'text-accent', icon: '👁', hex: '#7c5bf5' },
  god_succession:       { color: 'text-accent', icon: '♛', hex: '#ffd700' },
  evolution_milestone:  { color: 'text-cyan',   icon: '⬆', hex: '#58d5f0' },
  group_gathering:      { color: 'text-accent', icon: '⊕', hex: '#a78bfa' },
  artifact_created:     { color: 'text-cyan',   icon: '✧', hex: '#67e8f9' },
  organization_formed:  { color: 'text-green',  icon: '⬡', hex: '#4ade80' },
};

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSec = Math.floor((now - then) / 1000);
  if (diffSec < 10) return 'now';
  if (diffSec < 60) return `${diffSec}s`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m`;
  const diffHr = Math.floor(diffMin / 60);
  return `${diffHr}h`;
}

/** Extracted feed content for reuse in mobile MobileFeedView */
export function FeedContent({ tab, fullScreen }: { tab: Tab; fullScreen?: boolean }) {
  const { t } = useTranslation();
  const { thoughts, startPolling, stopPolling } = useThoughtStore();
  const [events, setEvents] = useState<WorldEvent[]>([]);

  useEffect(() => {
    startPolling();
    return () => stopPolling();
  }, [startPolling, stopPolling]);

  useEffect(() => {
    const load = () => api.history.getEvents(30).then(setEvents).catch(console.error);
    load();
    const interval = setInterval(load, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`p-2 space-y-1.5 ${fullScreen ? '' : ''}`}>
      {tab === 'thoughts' ? (
        thoughts.length === 0 ? (
          <EmptyState message={t('no_thoughts')} />
        ) : (
          thoughts.map((thought) => (
            <ThoughtEntry key={thought.id} thought={thought} />
          ))
        )
      ) : events.length === 0 ? (
        <EmptyState message={t('no_events')} />
      ) : (
        events.map((event) => (
          <EventEntry key={event.id} event={event} t={t} />
        ))
      )}
    </div>
  );
}

export default function ObserverFeed() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>('thoughts');
  const { thoughts } = useThoughtStore();
  const [events, setEvents] = useState<WorldEvent[]>([]);

  useEffect(() => {
    const load = () => api.history.getEvents(30).then(setEvents).catch(console.error);
    load();
    const interval = setInterval(load, 4000);
    return () => clearInterval(interval);
  }, []);

  const thoughtCount = thoughts.length;
  const eventCount = events.length;

  return (
    <div className="absolute top-20 right-4 z-40 w-72 pointer-events-auto">
      <div className="glass rounded-2xl border border-border shadow-[0_8px_40px_rgba(0,0,0,0.5)] fade-in overflow-hidden flex flex-col max-h-[calc(100vh-160px)]">
        {/* Tab bar */}
        <div className="flex border-b border-white/[0.04]">
          <button
            onClick={() => setTab('thoughts')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-[10px] font-medium uppercase tracking-wider transition-colors ${
              tab === 'thoughts'
                ? 'text-accent border-b-2 border-accent bg-white/[0.02]'
                : 'text-text-3 hover:text-text-2'
            }`}
          >
            <Brain size={11} />
            {t('thoughts')}
            {thoughtCount > 0 && (
              <span className="text-[8px] opacity-60">{thoughtCount}</span>
            )}
          </button>
          <button
            onClick={() => setTab('events')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-[10px] font-medium uppercase tracking-wider transition-colors ${
              tab === 'events'
                ? 'text-cyan border-b-2 border-cyan bg-white/[0.02]'
                : 'text-text-3 hover:text-text-2'
            }`}
          >
            <Radio size={11} />
            {t('live_events')}
            {eventCount > 0 && (
              <span className="text-[8px] opacity-60">{eventCount}</span>
            )}
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          <FeedContent tab={tab} />
        </div>
      </div>
    </div>
  );
}

function ThoughtEntry({ thought }: { thought: AIThought }) {
  const openDetail = useDetailStore((s) => s.openDetail);
  const Icon = thoughtIcons[thought.thought_type] || Compass;
  const colorClass = thoughtColors[thought.thought_type] || 'text-text-3';

  return (
    <button
      onClick={() => openDetail('thought', thought)}
      className="w-full text-left p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-all duration-200 group cursor-pointer"
    >
      <div className="flex items-start gap-2">
        <div className={`mt-0.5 flex-shrink-0 ${colorClass}`}>
          <Icon size={12} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-[11px] font-medium text-accent group-hover:text-text transition-colors truncate">
              {thought.ai_name || 'Unknown'}
            </span>
            <span className="text-[8px] text-text-3 flex-shrink-0">
              {formatRelativeTime(thought.created_at)}
            </span>
          </div>
          <p className="text-[10px] text-text-2 leading-relaxed line-clamp-2">
            {thought.content}
          </p>
        </div>
      </div>
    </button>
  );
}

function EventEntry({ event, t }: { event: WorldEvent; t: (key: string) => string }) {
  const openDetail = useDetailStore((s) => s.openDetail);
  const cfg = eventConfig[event.event_type] || { color: 'text-text-3', icon: '·', hex: '#8a8694' };
  const label = t(`event_type_${event.event_type}`);

  return (
    <button
      onClick={() => openDetail('event', event)}
      className="w-full text-left p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-colors cursor-pointer"
    >
      <div className="flex items-center gap-1.5 mb-1">
        <span className={`text-[10px] ${cfg.color}`}>{cfg.icon}</span>
        <span className={`text-[9px] font-medium uppercase tracking-wider ${cfg.color}`}>
          {label}
        </span>
        <span className="text-[8px] mono text-text-3 ml-auto opacity-60">
          T:{event.tick_number}
        </span>
      </div>
      {event.description && (
        <p className="text-[9px] text-text-2 leading-relaxed line-clamp-2 mt-0.5 mb-1">
          {event.description}
        </p>
      )}
      <div className="flex items-center gap-2 mt-1">
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
    </button>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-8">
      <div className="relative w-8 h-8 mx-auto mb-3">
        <div className="absolute inset-0 rounded-full border border-border/50 pulse-ring" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-1 h-1 rounded-full bg-text-3" />
        </div>
      </div>
      <p className="text-text-3 text-[10px]">{message}</p>
    </div>
  );
}
