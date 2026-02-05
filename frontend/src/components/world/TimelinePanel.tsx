/**
 * TimelinePanel — Toggleable right-side panel for browsing world history.
 *
 * Three tabs:
 *  - Sagas: saga chapters from /api/saga/chapters
 *  - Events: significant events from /api/history/events with filtering
 *  - Stats: world statistics from /api/world/stats with CSS mini-charts
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Clock,
  BookOpen,
  Skull,
  Crown,
  Swords,
  Eye,
  Sparkles,
  X,
  ChevronDown,
  ChevronRight,
  Loader2,
  MessageCircle,
  Lightbulb,
  Users,
  Zap,
  BarChart3,
  Activity,
  Heart,
  Calendar,
} from 'lucide-react';
import { api } from '../../services/api';
import { useWorldStoreV3 } from '../../stores/worldStoreV3';
import type { SagaChapter } from '../../types/world';

// ── Types ──────────────────────────────────────────────────

type TabId = 'sagas' | 'events' | 'stats';
type EventFilter = 'all' | 'deaths' | 'god' | 'conflicts';

interface TimelineEvent {
  id: string;
  event_type: string;
  importance: number;
  title: string;
  description?: string;
  tick_number: number;
  created_at: string;
  metadata_?: Record<string, any>;
}

interface WorldStats {
  total_ticks: number;
  total_ais_born: number;
  total_ais_alive: number;
  total_concepts: number;
  total_interactions: number;
  total_events: number;
}

interface TickSnapshot {
  id: string;
  tick_number: number;
  ai_count: number;
  concept_count: number;
  significant_events: number;
  processing_time_ms: number;
  created_at: string;
}

// ── Event type configuration ───────────────────────────────

const eventTypeConfig: Record<string, { icon: typeof Skull; color: string; hex: string }> = {
  ai_death:            { icon: Skull,          color: 'text-orange-400',  hex: '#fb923c' },
  ai_birth:            { icon: Sparkles,       color: 'text-green-400',   hex: '#34d399' },
  god_observation:     { icon: Eye,            color: 'text-purple-400',  hex: '#a78bfa' },
  god_message:         { icon: Crown,          color: 'text-purple-400',  hex: '#a78bfa' },
  god_crisis:          { icon: Zap,            color: 'text-yellow-400',  hex: '#facc15' },
  interaction:         { icon: MessageCircle,  color: 'text-rose-400',    hex: '#f472b6' },
  conflict:            { icon: Swords,         color: 'text-red-400',     hex: '#f87171' },
  concept_created:     { icon: Lightbulb,      color: 'text-cyan-400',    hex: '#22d3ee' },
  artifact_created:    { icon: Sparkles,       color: 'text-cyan-300',    hex: '#67e8f9' },
  organization_formed: { icon: Users,          color: 'text-green-300',   hex: '#86efac' },
};

const defaultEventConfig = { icon: Zap, color: 'text-white/60', hex: '#8a8694' };

function getEventConfig(type: string) {
  return eventTypeConfig[type] || defaultEventConfig;
}

function normalizeEvent(raw: any): TimelineEvent {
  return {
    id: raw.id,
    event_type: raw.event_type || raw.type || 'unknown',
    importance: raw.importance ?? 0.5,
    title: raw.title || '',
    description: raw.description,
    tick_number: raw.tick_number ?? 0,
    created_at: raw.created_at || raw.timestamp || '',
    metadata_: raw.metadata_ || {},
  };
}

// ── Helpers ────────────────────────────────────────────────

function formatWorldAge(totalTicks: number): string {
  // Assume ~10 seconds per tick for display purposes
  const totalSeconds = totalTicks * 10;
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);

  const parts: string[] = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0 || parts.length === 0) parts.push(`${minutes}m`);
  return parts.join(' ');
}

function filterEvents(events: TimelineEvent[], filter: EventFilter): TimelineEvent[] {
  if (filter === 'all') return events;
  if (filter === 'deaths') return events.filter(e => e.event_type === 'ai_death');
  if (filter === 'god') return events.filter(e =>
    e.event_type === 'god_observation' ||
    e.event_type === 'god_message' ||
    e.event_type === 'god_crisis'
  );
  if (filter === 'conflicts') return events.filter(e =>
    e.event_type === 'conflict' ||
    e.event_type === 'interaction'
  );
  return events;
}

// ── Main Component ─────────────────────────────────────────

interface Props {
  visible: boolean;
  onClose: () => void;
}

export function TimelinePanel({ visible, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<TabId>('sagas');

  return (
    <>
      {/* Panel */}
      <div
        className={`absolute top-0 right-0 h-full z-20 transition-transform duration-300 ease-in-out ${
          visible ? 'translate-x-0' : 'translate-x-full'
        }`}
        style={{ width: 400 }}
      >
        <div className="h-full bg-black/75 backdrop-blur-md border-l border-white/[0.08] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] flex-shrink-0">
            <div className="flex items-center gap-2">
              <Clock size={14} className="text-purple-400" />
              <span className="text-[13px] font-semibold text-white/90 tracking-wide">Timeline</span>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md hover:bg-white/10 text-white/40 hover:text-white/80 transition-colors"
            >
              <X size={14} />
            </button>
          </div>

          {/* Tab bar */}
          <div className="flex border-b border-white/[0.06] flex-shrink-0">
            {(['sagas', 'events', 'stats'] as TabId[]).map((tab) => {
              const icons: Record<TabId, typeof BookOpen> = {
                sagas: BookOpen,
                events: Activity,
                stats: BarChart3,
              };
              const Icon = icons[tab];
              const isActive = activeTab === tab;
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-[11px] font-medium uppercase tracking-wider transition-all relative ${
                    isActive
                      ? 'text-white/90'
                      : 'text-white/40 hover:text-white/60'
                  }`}
                >
                  <Icon size={12} />
                  {tab}
                  {isActive && (
                    <div className="absolute bottom-0 left-2 right-2 h-[2px] bg-purple-500 rounded-full" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-hidden">
            {activeTab === 'sagas' && <SagasTab />}
            {activeTab === 'events' && <EventsTab />}
            {activeTab === 'stats' && <StatsTab />}
          </div>
        </div>
      </div>
    </>
  );
}

// ── Toggle Button (exported separately for placement) ──────

interface ToggleButtonProps {
  isOpen: boolean;
  onClick: () => void;
}

export function TimelineToggleButton({ isOpen, onClick }: ToggleButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded text-xs font-mono flex items-center gap-1.5 transition-all ${
        isOpen
          ? 'bg-purple-600 text-white'
          : 'bg-white/10 text-white/70 hover:bg-white/20'
      }`}
    >
      <Clock size={12} />
      Timeline
    </button>
  );
}

// ════════════════════════════════════════════════════════════
// SAGAS TAB
// ════════════════════════════════════════════════════════════

function SagasTab() {
  const [chapters, setChapters] = useState<SagaChapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await api.saga.getChapters(50);
        if (!cancelled) setChapters(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setChapters([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading && chapters.length === 0) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={18} className="animate-spin" style={{ color: '#d4a574' }} />
      </div>
    );
  }

  if (chapters.length === 0) {
    return (
      <div className="text-center py-16">
        <BookOpen size={20} className="mx-auto mb-3" style={{ color: '#d4a574', opacity: 0.5 }} />
        <p className="text-white/30 text-[12px]">No saga chapters yet</p>
        <p className="text-white/20 text-[11px] mt-1">The world is still writing its story...</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="p-3 space-y-2">
        {chapters.map((chapter) => (
          <SagaCard
            key={chapter.id}
            chapter={chapter}
            expanded={expandedId === chapter.id}
            onToggle={() => setExpandedId(expandedId === chapter.id ? null : chapter.id)}
          />
        ))}
      </div>
    </div>
  );
}

function SagaCard({
  chapter,
  expanded,
  onToggle,
}: {
  chapter: SagaChapter;
  expanded: boolean;
  onToggle: () => void;
}) {
  const moodHex: Record<string, string> = {
    hopeful: '#34d399',
    tragic: '#fb923c',
    triumphant: '#d4a574',
    mysterious: '#a78bfa',
    peaceful: '#22d3ee',
    turbulent: '#f472b6',
  };
  const hex = (chapter.mood && moodHex[chapter.mood]) || '#d4a574';

  return (
    <div
      className="rounded-xl border border-white/[0.06] overflow-hidden transition-all duration-200 hover:border-white/[0.12]"
      style={{ backgroundColor: 'rgba(212,165,116,0.03)' }}
    >
      {/* Clickable header */}
      <button
        onClick={onToggle}
        className="w-full text-left p-3.5 group"
      >
        <div className="flex items-center gap-2 mb-1.5">
          <span
            className="text-[10px] font-semibold uppercase tracking-[0.15em]"
            style={{ color: '#d4a574' }}
          >
            Era {chapter.era_number}
          </span>
          {chapter.mood && (
            <span
              className="text-[9px] px-1.5 py-0.5 rounded-full border"
              style={{
                color: hex,
                borderColor: `${hex}30`,
                backgroundColor: `${hex}10`,
              }}
            >
              {chapter.mood}
            </span>
          )}
          <span className="ml-auto text-[10px] font-mono text-white/30">
            T:{chapter.start_tick}-{chapter.end_tick}
          </span>
          <div className="text-white/30 group-hover:text-white/50 transition-colors">
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </div>
        </div>
        <h3
          className="text-[14px] font-medium leading-snug group-hover:text-white/90 transition-colors"
          style={{ color: '#e4e2e8', fontFamily: 'Georgia, "Times New Roman", serif' }}
        >
          {chapter.chapter_title}
        </h3>
        {!expanded && chapter.summary && (
          <p className="text-[11px] text-white/40 leading-relaxed mt-1 line-clamp-2">
            {chapter.summary}
          </p>
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-3.5 pb-4 space-y-3 border-t border-white/[0.04]">
          {/* Narrative */}
          <div
            className="text-[13px] leading-[1.8] text-white/70 pt-3 whitespace-pre-line"
            style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
          >
            {chapter.narrative}
          </div>

          {/* Key characters */}
          {chapter.key_characters.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#d4a574' }}>
                Key Characters
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {chapter.key_characters.map((char, i) => (
                  <span
                    key={i}
                    className="text-[10px] px-2 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06] text-white/60"
                  >
                    <span className="text-white/80 font-medium">{char.name}</span>
                    {char.role && <span className="text-white/30 ml-1">- {char.role}</span>}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Stats row */}
          <div className="flex items-center gap-3 text-[10px] text-white/40 pt-1">
            {chapter.era_statistics.births > 0 && (
              <span className="flex items-center gap-1">
                <Sparkles size={10} className="text-green-400" />
                {chapter.era_statistics.births} births
              </span>
            )}
            {chapter.era_statistics.deaths > 0 && (
              <span className="flex items-center gap-1">
                <Skull size={10} className="text-orange-400" />
                {chapter.era_statistics.deaths} deaths
              </span>
            )}
            {chapter.era_statistics.interactions > 0 && (
              <span className="flex items-center gap-1">
                <MessageCircle size={10} className="text-rose-400" />
                {chapter.era_statistics.interactions}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ════════════════════════════════════════════════════════════
// EVENTS TAB
// ════════════════════════════════════════════════════════════

function EventsTab() {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<EventFilter>('all');
  const [limit, setLimit] = useState(50);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const loadEvents = useCallback(async (currentLimit: number) => {
    try {
      const data = await api.history.getEvents(currentLimit);
      const normalized = (data || []).map(normalizeEvent);
      setEvents(normalized);
      setHasMore(normalized.length >= currentLimit);
    } catch {
      setEvents([]);
      setHasMore(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    loadEvents(limit).finally(() => setLoading(false));
  }, [limit, loadEvents]);

  // Auto-refresh every 15s
  useEffect(() => {
    const interval = setInterval(() => loadEvents(limit), 15000);
    return () => clearInterval(interval);
  }, [limit, loadEvents]);

  const handleScroll = () => {
    if (!scrollRef.current || loadingMore || !hasMore) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    if (scrollHeight - scrollTop - clientHeight < 100) {
      setLoadingMore(true);
      const newLimit = limit + 50;
      setLimit(newLimit);
      loadEvents(newLimit).finally(() => setLoadingMore(false));
    }
  };

  const filtered = filterEvents(events, filter);

  const filterButtons: { id: EventFilter; label: string; icon: typeof Skull }[] = [
    { id: 'all', label: 'All', icon: Activity },
    { id: 'deaths', label: 'Deaths', icon: Skull },
    { id: 'god', label: 'God', icon: Crown },
    { id: 'conflicts', label: 'Conflicts', icon: Swords },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Filter buttons */}
      <div className="flex gap-1.5 px-3 py-2.5 border-b border-white/[0.04] flex-shrink-0">
        {filterButtons.map((btn) => {
          const Icon = btn.icon;
          const isActive = filter === btn.id;
          return (
            <button
              key={btn.id}
              onClick={() => setFilter(btn.id)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-medium transition-all border ${
                isActive
                  ? 'bg-purple-500/15 text-purple-300 border-purple-500/30'
                  : 'bg-white/[0.03] text-white/40 border-white/[0.06] hover:text-white/60 hover:bg-white/[0.06]'
              }`}
            >
              <Icon size={10} />
              {btn.label}
            </button>
          );
        })}
      </div>

      {/* Event list */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto scrollbar-thin"
      >
        {loading && events.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={18} className="text-purple-400 animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <Activity size={20} className="mx-auto mb-3 text-white/20" />
            <p className="text-white/30 text-[12px]">No events found</p>
          </div>
        ) : (
          <div className="p-3 space-y-1.5">
            {filtered.map((event) => (
              <EventCard key={event.id} event={event} />
            ))}
            {hasMore && (
              <div className="flex items-center justify-center py-3">
                {loadingMore ? (
                  <Loader2 size={14} className="text-white/30 animate-spin" />
                ) : (
                  <button
                    onClick={() => {
                      setLoadingMore(true);
                      const newLimit = limit + 50;
                      setLimit(newLimit);
                      loadEvents(newLimit).finally(() => setLoadingMore(false));
                    }}
                    className="text-[11px] text-white/30 hover:text-white/50 transition-colors flex items-center gap-1"
                  >
                    <ChevronDown size={12} />
                    Load more
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function EventCard({ event }: { event: TimelineEvent }) {
  const config = getEventConfig(event.event_type);
  const Icon = config.icon;

  return (
    <div className="flex gap-2.5 p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-all duration-200">
      {/* Icon */}
      <div
        className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center mt-0.5"
        style={{ backgroundColor: `${config.hex}15` }}
      >
        <Icon size={13} style={{ color: config.hex }} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span
            className="text-[10px] font-medium uppercase tracking-wider"
            style={{ color: config.hex }}
          >
            {event.event_type.replace(/_/g, ' ')}
          </span>
          <span className="ml-auto text-[9px] font-mono text-white/25 flex-shrink-0">
            T:{event.tick_number}
          </span>
        </div>
        {event.title && (
          <p className="text-[12px] font-medium text-white/80 leading-snug">
            {event.title}
          </p>
        )}
        {event.description && (
          <p className="text-[11px] text-white/40 leading-relaxed mt-0.5 line-clamp-2">
            {event.description}
          </p>
        )}
        {/* Importance bar */}
        <div className="flex items-center gap-2 mt-1.5">
          <div className="flex-1 h-[2px] bg-white/[0.04] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.min(100, event.importance * 100)}%`,
                backgroundColor: config.hex,
                opacity: 0.5,
              }}
            />
          </div>
          <span className="text-[8px] font-mono text-white/20">
            {(event.importance * 100).toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════
// STATS TAB
// ════════════════════════════════════════════════════════════

function StatsTab() {
  const [stats, setStats] = useState<WorldStats | null>(null);
  const [ticks, setTicks] = useState<TickSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const tickNumber = useWorldStoreV3(s => s.tickNumber);
  const entityCount = useWorldStoreV3(s => s.entityCount);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const [statsData] = await Promise.all([
          api.world.getStats(),
          api.history.getEvents(100), // Get recent events as proxy for tick activity
        ]);
        if (!cancelled) {
          setStats(statsData);
        }
      } catch {
        // Ignore
      }

      // Also fetch recent tick snapshots
      try {
        const API_BASE = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api';
        const res = await fetch(`${API_BASE}/history/ticks?limit=100`);
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) setTicks(Array.isArray(data) ? data : []);
        }
      } catch {
        // Ignore
      }

      if (!cancelled) setLoading(false);
    }

    load();
    const interval = setInterval(load, 30000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={18} className="text-purple-400 animate-spin" />
      </div>
    );
  }

  const totalTicks = stats?.total_ticks ?? tickNumber;
  const totalBorn = stats?.total_ais_born ?? 0;
  const totalAlive = stats?.total_ais_alive ?? entityCount;
  const totalDeaths = totalBorn - totalAlive;
  const totalInteractions = stats?.total_interactions ?? 0;
  const totalEvents = stats?.total_events ?? 0;
  const totalConcepts = stats?.total_concepts ?? 0;

  // Build entity count chart data from tick snapshots (last 100 ticks)
  const chartTicks = [...ticks].reverse().slice(-100);
  const maxAiCount = Math.max(1, ...chartTicks.map(t => t.ai_count));

  // Average processing time
  const avgProcessing = chartTicks.length > 0
    ? chartTicks.reduce((sum, t) => sum + (t.processing_time_ms || 0), 0) / chartTicks.length
    : 0;

  // Average significant events per tick
  const avgEvents = chartTicks.length > 0
    ? chartTicks.reduce((sum, t) => sum + (t.significant_events || 0), 0) / chartTicks.length
    : 0;

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="p-4 space-y-4">
        {/* World age */}
        <div className="text-center pb-3 border-b border-white/[0.06]">
          <div className="flex items-center justify-center gap-2 mb-1">
            <Calendar size={14} className="text-purple-400" />
            <span className="text-[11px] uppercase tracking-wider text-white/40 font-medium">
              World Age
            </span>
          </div>
          <div className="text-[28px] font-mono font-bold text-white/90 tracking-tight">
            {totalTicks.toLocaleString()}
          </div>
          <div className="text-[11px] text-white/30 font-mono">
            ticks ({formatWorldAge(totalTicks)})
          </div>
        </div>

        {/* Stat cards grid */}
        <div className="grid grid-cols-2 gap-2">
          <StatCard
            icon={<Sparkles size={13} className="text-green-400" />}
            label="Total Born"
            value={totalBorn}
          />
          <StatCard
            icon={<Heart size={13} className="text-cyan-400" />}
            label="Currently Alive"
            value={totalAlive}
            highlight
          />
          <StatCard
            icon={<Skull size={13} className="text-orange-400" />}
            label="Total Deaths"
            value={totalDeaths}
          />
          <StatCard
            icon={<Swords size={13} className="text-red-400" />}
            label="Interactions"
            value={totalInteractions}
          />
          <StatCard
            icon={<Lightbulb size={13} className="text-cyan-300" />}
            label="Concepts"
            value={totalConcepts}
          />
          <StatCard
            icon={<Activity size={13} className="text-purple-400" />}
            label="Total Events"
            value={totalEvents}
          />
        </div>

        {/* Mini charts section */}
        {chartTicks.length > 0 && (
          <>
            {/* Entity count over time */}
            <div className="rounded-xl bg-white/[0.02] border border-white/[0.06] p-3">
              <div className="flex items-center gap-1.5 mb-3">
                <Users size={12} className="text-purple-400" />
                <span className="text-[11px] font-medium text-white/60 uppercase tracking-wider">
                  Entity Count (last {chartTicks.length} ticks)
                </span>
              </div>
              <MiniBarChart
                data={chartTicks.map(t => t.ai_count)}
                maxValue={maxAiCount}
                color="#a78bfa"
                height={48}
              />
              <div className="flex justify-between mt-1.5 text-[9px] font-mono text-white/20">
                <span>T:{chartTicks[0]?.tick_number}</span>
                <span>T:{chartTicks[chartTicks.length - 1]?.tick_number}</span>
              </div>
            </div>

            {/* Events per tick */}
            <div className="rounded-xl bg-white/[0.02] border border-white/[0.06] p-3">
              <div className="flex items-center gap-1.5 mb-3">
                <Activity size={12} className="text-cyan-400" />
                <span className="text-[11px] font-medium text-white/60 uppercase tracking-wider">
                  Events per Tick
                </span>
              </div>
              <MiniBarChart
                data={chartTicks.map(t => t.significant_events)}
                maxValue={Math.max(1, ...chartTicks.map(t => t.significant_events))}
                color="#22d3ee"
                height={48}
              />
              <div className="flex justify-between mt-1.5 text-[9px] font-mono text-white/20">
                <span>avg: {avgEvents.toFixed(1)}/tick</span>
                <span>proc: {avgProcessing.toFixed(0)}ms avg</span>
              </div>
            </div>
          </>
        )}

        {/* Footer meta */}
        <div className="text-center text-[10px] font-mono text-white/15 pt-2">
          Data refreshes every 30s
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  highlight,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div
      className={`flex flex-col gap-1.5 p-3 rounded-xl border transition-all ${
        highlight
          ? 'bg-cyan-500/5 border-cyan-500/15'
          : 'bg-white/[0.02] border-white/[0.06]'
      }`}
    >
      <div className="flex items-center gap-1.5">
        {icon}
        <span className="text-[10px] text-white/40 uppercase tracking-wider">{label}</span>
      </div>
      <span className={`text-[20px] font-mono font-bold tracking-tight ${
        highlight ? 'text-cyan-300' : 'text-white/80'
      }`}>
        {value.toLocaleString()}
      </span>
    </div>
  );
}

// ── Pure CSS Mini Bar Chart ────────────────────────────────

function MiniBarChart({
  data,
  maxValue,
  color,
  height = 48,
}: {
  data: number[];
  maxValue: number;
  color: string;
  height?: number;
}) {
  // Limit to reasonable number of bars
  const bars = data.length > 100 ? data.slice(-100) : data;
  const barWidth = Math.max(1, Math.floor(340 / bars.length) - 1);

  return (
    <div
      className="flex items-end gap-px"
      style={{ height }}
    >
      {bars.map((value, i) => {
        const h = maxValue > 0 ? (value / maxValue) * height : 0;
        return (
          <div
            key={i}
            className="rounded-t-sm transition-all duration-300"
            style={{
              width: barWidth,
              height: Math.max(1, h),
              backgroundColor: color,
              opacity: 0.3 + (value / maxValue) * 0.5,
              flexShrink: 0,
            }}
          />
        );
      })}
    </div>
  );
}
