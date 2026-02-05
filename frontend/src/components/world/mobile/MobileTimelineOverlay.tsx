/**
 * MobileTimelineOverlay — Timeline as full-screen overlay for mobile.
 *
 * Internal tabs (Sagas/Events/Stats) with 48px buttons.
 * All text bumped by 2-4px.
 * Full-width charts instead of hardcoded px widths.
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
import { api } from '../../../services/api';
import { useWorldStoreV3 } from '../../../stores/worldStoreV3';
import { useMobileStoreV3 } from '../../../stores/mobileStoreV3';
import { MobileOverlay } from './MobileOverlay';
import type { SagaChapter } from '../../../types/world';

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

// ── Event type config ───────────────────────────────────
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

function formatWorldAge(totalTicks: number): string {
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
    e.event_type === 'god_observation' || e.event_type === 'god_message' || e.event_type === 'god_crisis'
  );
  if (filter === 'conflicts') return events.filter(e =>
    e.event_type === 'conflict' || e.event_type === 'interaction'
  );
  return events;
}

// ── Main Component ─────────────────────────────────────
export function MobileTimelineOverlay() {
  const timelineOpen = useMobileStoreV3(s => s.timelineOpen);
  const setTimelineOpen = useMobileStoreV3(s => s.setTimelineOpen);
  const [activeTab, setActiveTab] = useState<TabId>('sagas');

  return (
    <MobileOverlay
      visible={timelineOpen}
      onClose={() => setTimelineOpen(false)}
      title="Timeline"
      icon={<Clock size={14} className="text-purple-400" />}
    >
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
              className={`flex-1 flex items-center justify-center gap-2 text-[13px] font-medium uppercase tracking-wider transition-all relative ${
                isActive ? 'text-white/90' : 'text-white/40'
              }`}
              style={{ height: 48 }}
            >
              <Icon size={14} />
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
        {activeTab === 'sagas' && <MobileSagasTab />}
        {activeTab === 'events' && <MobileEventsTab />}
        {activeTab === 'stats' && <MobileStatsTab />}
      </div>
    </MobileOverlay>
  );
}

// ── Sagas Tab ─────────────────────────────────────
const SAGA_PAGE_SIZE = 10;

function MobileSagasTab() {
  const [chapters, setChapters] = useState<SagaChapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [limit, setLimit] = useState(SAGA_PAGE_SIZE);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await api.saga.getChapters(limit);
        if (!cancelled) {
          const arr = Array.isArray(data) ? data : [];
          setChapters(arr);
          setHasMore(arr.length >= limit);
        }
      } catch {
        if (!cancelled) { setChapters([]); setHasMore(false); }
      } finally {
        if (!cancelled) { setLoading(false); setLoadingMore(false); }
      }
    }
    load();
    return () => { cancelled = true; };
  }, [limit]);

  if (loading && chapters.length === 0) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={20} className="animate-spin" style={{ color: '#d4a574' }} />
      </div>
    );
  }

  if (chapters.length === 0) {
    return (
      <div className="text-center py-16">
        <BookOpen size={24} className="mx-auto mb-3" style={{ color: '#d4a574', opacity: 0.5 }} />
        <p className="text-white/30 text-[14px]">No saga chapters yet</p>
        <p className="text-white/20 text-[13px] mt-1">The world is still writing its story...</p>
      </div>
    );
  }

  const moodHex: Record<string, string> = {
    hopeful: '#34d399', tragic: '#fb923c', triumphant: '#d4a574',
    mysterious: '#a78bfa', peaceful: '#22d3ee', turbulent: '#f472b6',
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-3 space-y-2">
        {chapters.slice(0, limit).map((chapter) => {
          const hex = (chapter.mood && moodHex[chapter.mood]) || '#d4a574';
          const expanded = expandedId === chapter.id;

          return (
            <div
              key={chapter.id}
              className="rounded-xl border border-white/[0.06] overflow-hidden"
              style={{ backgroundColor: 'rgba(212,165,116,0.03)' }}
            >
              <button
                onClick={() => setExpandedId(expanded ? null : chapter.id)}
                className="w-full text-left p-4"
                style={{ minHeight: 48 }}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[12px] font-semibold uppercase tracking-[0.15em]" style={{ color: '#d4a574' }}>
                    Era {chapter.era_number}
                  </span>
                  {chapter.mood && (
                    <span
                      className="text-[11px] px-1.5 py-0.5 rounded-full border"
                      style={{ color: hex, borderColor: `${hex}30`, backgroundColor: `${hex}10` }}
                    >
                      {chapter.mood}
                    </span>
                  )}
                  <span className="ml-auto text-[12px] font-mono text-white/30">
                    T:{chapter.start_tick}-{chapter.end_tick}
                  </span>
                  <div className="text-white/30">
                    {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </div>
                </div>
                <h3
                  className="text-[15px] font-medium leading-snug"
                  style={{ color: '#e4e2e8', fontFamily: 'Georgia, "Times New Roman", serif' }}
                >
                  {chapter.chapter_title}
                </h3>
                {!expanded && chapter.summary && (
                  <p className="text-[13px] text-white/40 leading-relaxed mt-1 line-clamp-2">{chapter.summary}</p>
                )}
              </button>

              {expanded && (
                <div className="px-4 pb-4 space-y-3 border-t border-white/[0.04]">
                  <div
                    className="text-[14px] leading-[1.8] text-white/70 pt-3 whitespace-pre-line"
                    style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                  >
                    {chapter.narrative}
                  </div>

                  {chapter.key_characters.length > 0 && (
                    <div>
                      <h4 className="text-[12px] font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#d4a574' }}>
                        Key Characters
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {chapter.key_characters.map((char, i) => (
                          <span key={i} className="text-[12px] px-2 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06] text-white/60">
                            <span className="text-white/80 font-medium">{char.name}</span>
                            {char.role && <span className="text-white/30 ml-1">- {char.role}</span>}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-3 text-[12px] text-white/40 pt-1">
                    {chapter.era_statistics.births > 0 && (
                      <span className="flex items-center gap-1">
                        <Sparkles size={12} className="text-green-400" />
                        {chapter.era_statistics.births} births
                      </span>
                    )}
                    {chapter.era_statistics.deaths > 0 && (
                      <span className="flex items-center gap-1">
                        <Skull size={12} className="text-orange-400" />
                        {chapter.era_statistics.deaths} deaths
                      </span>
                    )}
                    {chapter.era_statistics.interactions > 0 && (
                      <span className="flex items-center gap-1">
                        <MessageCircle size={12} className="text-rose-400" />
                        {chapter.era_statistics.interactions}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
        {hasMore && (
          <div className="flex items-center justify-center py-3">
            {loadingMore ? (
              <Loader2 size={16} className="text-white/30 animate-spin" />
            ) : (
              <button
                onClick={() => {
                  setLoadingMore(true);
                  setLimit(prev => prev + SAGA_PAGE_SIZE);
                }}
                className="text-[13px] text-white/30 flex items-center gap-1"
                style={{ minHeight: 44 }}
              >
                <ChevronDown size={14} />
                Load more sagas
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Events Tab ─────────────────────────────────────
function MobileEventsTab() {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<EventFilter>('all');
  const [limit, setLimit] = useState(20);
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

  useEffect(() => {
    const interval = setInterval(() => loadEvents(limit), 15000);
    return () => clearInterval(interval);
  }, [limit, loadEvents]);

  const handleScroll = () => {
    if (!scrollRef.current || loadingMore || !hasMore) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    if (scrollHeight - scrollTop - clientHeight < 100) {
      setLoadingMore(true);
      const newLimit = limit + 20;
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
      {/* Filters */}
      <div className="flex gap-2 px-3 py-2.5 border-b border-white/[0.04] flex-shrink-0 overflow-x-auto">
        {filterButtons.map((btn) => {
          const Icon = btn.icon;
          const isActive = filter === btn.id;
          return (
            <button
              key={btn.id}
              onClick={() => setFilter(btn.id)}
              className={`flex items-center gap-1.5 px-3 rounded-full text-[12px] font-medium border flex-shrink-0 ${
                isActive
                  ? 'bg-purple-500/15 text-purple-300 border-purple-500/30'
                  : 'bg-white/[0.03] text-white/40 border-white/[0.06]'
              }`}
              style={{ height: 36 }}
            >
              <Icon size={12} />
              {btn.label}
            </button>
          );
        })}
      </div>

      {/* Events */}
      <div ref={scrollRef} onScroll={handleScroll} className="flex-1 overflow-y-auto">
        {loading && events.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={20} className="text-purple-400 animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <Activity size={24} className="mx-auto mb-3 text-white/20" />
            <p className="text-white/30 text-[14px]">No events found</p>
          </div>
        ) : (
          <div className="p-3 space-y-1.5">
            {filtered.map((event) => {
              const config = getEventConfig(event.event_type);
              const Icon = config.icon;
              return (
                <div
                  key={event.id}
                  className="flex gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                  style={{ minHeight: 48 }}
                >
                  <div
                    className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center mt-0.5"
                    style={{ backgroundColor: `${config.hex}15` }}
                  >
                    <Icon size={14} style={{ color: config.hex }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-[12px] font-medium uppercase tracking-wider" style={{ color: config.hex }}>
                        {event.event_type.replace(/_/g, ' ')}
                      </span>
                      <span className="ml-auto text-[11px] font-mono text-white/25 flex-shrink-0">
                        T:{event.tick_number}
                      </span>
                    </div>
                    {event.title && (
                      <p className="text-[14px] font-medium text-white/80 leading-snug">{event.title}</p>
                    )}
                    {event.description && (
                      <p className="text-[13px] text-white/40 leading-relaxed mt-0.5 line-clamp-2">{event.description}</p>
                    )}
                    <div className="flex items-center gap-2 mt-1.5">
                      <div className="flex-1 h-[3px] bg-white/[0.04] rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.min(100, event.importance * 100)}%`,
                            backgroundColor: config.hex,
                            opacity: 0.5,
                          }}
                        />
                      </div>
                      <span className="text-[11px] font-mono text-white/20">
                        {(event.importance * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
            {hasMore && (
              <div className="flex items-center justify-center py-3">
                {loadingMore ? (
                  <Loader2 size={16} className="text-white/30 animate-spin" />
                ) : (
                  <button
                    onClick={() => {
                      setLoadingMore(true);
                      const newLimit = limit + 50;
                      setLimit(newLimit);
                      loadEvents(newLimit).finally(() => setLoadingMore(false));
                    }}
                    className="text-[13px] text-white/30 flex items-center gap-1"
                    style={{ minHeight: 44 }}
                  >
                    <ChevronDown size={14} />
                    Load more events
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

// ── Stats Tab ─────────────────────────────────────
function MobileStatsTab() {
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
          api.history.getEvents(100),
        ]);
        if (!cancelled) setStats(statsData);
      } catch {
        // Ignore
      }

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
        <Loader2 size={20} className="text-purple-400 animate-spin" />
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

  const chartTicks = [...ticks].reverse().slice(-100);
  const maxAiCount = Math.max(1, ...chartTicks.map(t => t.ai_count));

  const avgProcessing = chartTicks.length > 0
    ? chartTicks.reduce((sum, t) => sum + (t.processing_time_ms || 0), 0) / chartTicks.length
    : 0;

  const avgEvents = chartTicks.length > 0
    ? chartTicks.reduce((sum, t) => sum + (t.significant_events || 0), 0) / chartTicks.length
    : 0;

  const statCards = [
    { icon: <Sparkles size={14} className="text-green-400" />, label: 'Total Born', value: totalBorn },
    { icon: <Heart size={14} className="text-cyan-400" />, label: 'Alive', value: totalAlive, highlight: true },
    { icon: <Skull size={14} className="text-orange-400" />, label: 'Deaths', value: totalDeaths },
    { icon: <Swords size={14} className="text-red-400" />, label: 'Interactions', value: totalInteractions },
    { icon: <Lightbulb size={14} className="text-cyan-300" />, label: 'Concepts', value: totalConcepts },
    { icon: <Activity size={14} className="text-purple-400" />, label: 'Events', value: totalEvents },
  ];

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-4 space-y-4">
        {/* World age */}
        <div className="text-center pb-3 border-b border-white/[0.06]">
          <div className="flex items-center justify-center gap-2 mb-1">
            <Calendar size={15} className="text-purple-400" />
            <span className="text-[13px] uppercase tracking-wider text-white/40 font-medium">World Age</span>
          </div>
          <div className="text-[28px] font-mono font-bold text-white/90 tracking-tight">
            {totalTicks.toLocaleString()}
          </div>
          <div className="text-[13px] text-white/30 font-mono">
            ticks ({formatWorldAge(totalTicks)})
          </div>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 gap-2">
          {statCards.map((card) => (
            <div
              key={card.label}
              className={`flex flex-col gap-1.5 p-3 rounded-xl border ${
                card.highlight ? 'bg-cyan-500/5 border-cyan-500/15' : 'bg-white/[0.02] border-white/[0.06]'
              }`}
            >
              <div className="flex items-center gap-1.5">
                {card.icon}
                <span className="text-[12px] text-white/40 uppercase tracking-wider">{card.label}</span>
              </div>
              <span className={`text-[20px] font-mono font-bold tracking-tight ${
                card.highlight ? 'text-cyan-300' : 'text-white/80'
              }`}>
                {card.value.toLocaleString()}
              </span>
            </div>
          ))}
        </div>

        {/* Charts */}
        {chartTicks.length > 0 && (
          <>
            <div className="rounded-xl bg-white/[0.02] border border-white/[0.06] p-3">
              <div className="flex items-center gap-1.5 mb-3">
                <Users size={13} className="text-purple-400" />
                <span className="text-[13px] font-medium text-white/60 uppercase tracking-wider">
                  Entity Count (last {chartTicks.length} ticks)
                </span>
              </div>
              <MobileBarChart
                data={chartTicks.map(t => t.ai_count)}
                maxValue={maxAiCount}
                color="#a78bfa"
                height={52}
              />
              <div className="flex justify-between mt-1.5 text-[11px] font-mono text-white/20">
                <span>T:{chartTicks[0]?.tick_number}</span>
                <span>T:{chartTicks[chartTicks.length - 1]?.tick_number}</span>
              </div>
            </div>

            <div className="rounded-xl bg-white/[0.02] border border-white/[0.06] p-3">
              <div className="flex items-center gap-1.5 mb-3">
                <Activity size={13} className="text-cyan-400" />
                <span className="text-[13px] font-medium text-white/60 uppercase tracking-wider">
                  Events per Tick
                </span>
              </div>
              <MobileBarChart
                data={chartTicks.map(t => t.significant_events)}
                maxValue={Math.max(1, ...chartTicks.map(t => t.significant_events))}
                color="#22d3ee"
                height={52}
              />
              <div className="flex justify-between mt-1.5 text-[11px] font-mono text-white/20">
                <span>avg: {avgEvents.toFixed(1)}/tick</span>
                <span>proc: {avgProcessing.toFixed(0)}ms avg</span>
              </div>
            </div>
          </>
        )}

        <div className="text-center text-[12px] font-mono text-white/15 pt-2">
          Data refreshes every 30s
        </div>
      </div>
    </div>
  );
}

// ── Full-width bar chart ─────────────────────────────
function MobileBarChart({
  data,
  maxValue,
  color,
  height = 52,
}: {
  data: number[];
  maxValue: number;
  color: string;
  height?: number;
}) {
  const bars = data.length > 100 ? data.slice(-100) : data;

  return (
    <div className="flex items-end gap-px w-full" style={{ height }}>
      {bars.map((value, i) => {
        const h = maxValue > 0 ? (value / maxValue) * height : 0;
        return (
          <div
            key={i}
            className="flex-1 rounded-t-sm transition-all duration-300"
            style={{
              height: Math.max(1, h),
              backgroundColor: color,
              opacity: 0.3 + (value / maxValue) * 0.5,
              minWidth: 1,
            }}
          />
        );
      })}
    </div>
  );
}
