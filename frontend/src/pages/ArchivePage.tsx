import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  Users,
  Palette,
  Eye,
  BarChart3,
  Search,
  Filter,
  ChevronDown,
  Loader2,
  X,
  Skull,
  Brain,
  Swords,
  Building2,
  Sparkles,
  MessageCircle,
  Lightbulb,
  Zap,
  ScrollText,
  BookOpen,
} from 'lucide-react';
import { api } from '../services/api';
import { useWorldStore } from '../stores/worldStore';
import EventCard, { getEventConfig } from '../components/timeline/EventCard';
import type { WorldEventData } from '../components/timeline/EventCard';
import TimelineBar from '../components/timeline/TimelineBar';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ArchiveTab = 'events' | 'entities' | 'artifacts' | 'god' | 'stats';

interface EntityLife {
  id: string;
  name: string;
  is_alive: boolean;
  birth_tick: number;
  death_tick: number | null;
  is_god: boolean;
}

interface StatsData {
  current: {
    alive_entities: number;
    total_entities: number;
    total_artifacts: number;
    total_events: number;
    max_tick: number;
  };
  births_over_time: { tick: number; count: number }[];
  deaths_over_time: { tick: number; count: number }[];
  events_over_time: { tick: number; count: number }[];
  event_type_breakdown: { event_type: string; count: number }[];
  entity_lives: EntityLife[];
}

// ---------------------------------------------------------------------------
// Color config (duplicated locally for the full page)
// ---------------------------------------------------------------------------

const eventTypeColors: Record<string, string> = {
  ai_birth: '#34d399',
  ai_death: '#f87171',
  entity_died: '#f87171',
  interaction: '#f472b6',
  god_message: '#fbbf24',
  god_observation: '#fbbf24',
  concept_created: '#22d3ee',
  artifact_created: '#c084fc',
  organization_formed: '#4ade80',
  entity_thought: '#60a5fa',
  conflict: '#fb923c',
  building: '#9ca3af',
};

function getTypeColor(type: string) {
  return eventTypeColors[type] || '#9ca3af';
}

// ---------------------------------------------------------------------------
// Main Archive Page
// ---------------------------------------------------------------------------

export default function ArchivePage() {
  const [activeTab, setActiveTab] = useState<ArchiveTab>('events');

  const tabs: { key: ArchiveTab; label: string; icon: typeof Clock }[] = [
    { key: 'events', label: 'Event Timeline', icon: Clock },
    { key: 'entities', label: 'Entity Lives', icon: Users },
    { key: 'artifacts', label: 'Artifacts Gallery', icon: Palette },
    { key: 'god', label: "God's Record", icon: Eye },
    { key: 'stats', label: 'Statistics', icon: BarChart3 },
  ];

  return (
    <div className="h-screen w-screen flex flex-col bg-bg text-text">
      {/* Header */}
      <header className="flex items-center gap-4 px-6 py-3 border-b border-border bg-surface/80 backdrop-blur-xl flex-shrink-0">
        <Link
          to="/"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] text-text-3 hover:text-text hover:bg-white/[0.06] transition-colors"
        >
          <ArrowLeft size={14} />
          Back
        </Link>
        <div className="flex items-center gap-2">
          <ScrollText size={16} className="text-accent" />
          <h1 className="text-[14px] font-bold uppercase tracking-wider text-text">
            World Archive
          </h1>
        </div>
        <div className="flex-1" />
        {/* Tab buttons */}
        <div className="flex items-center gap-1">
          {tabs.map(({ key, label, icon: TabIcon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all ${
                activeTab === key
                  ? 'bg-accent/15 text-accent border border-accent/30'
                  : 'text-text-3 hover:text-text hover:bg-white/[0.06]'
              }`}
            >
              <TabIcon size={12} />
              {label}
            </button>
          ))}
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-hidden">
        {activeTab === 'events' && <FullPageEventTimeline />}
        {activeTab === 'entities' && <FullPageEntityLives />}
        {activeTab === 'artifacts' && <FullPageArtifacts />}
        {activeTab === 'god' && <FullPageGodRecord />}
        {activeTab === 'stats' && <FullPageStatistics />}
      </main>

      {/* Timeline bar at bottom */}
      <TimelineBar />
    </div>
  );
}


// ===========================================================================
// Full Page Event Timeline
// ===========================================================================

function FullPageEventTimeline() {
  const [events, setEvents] = useState<WorldEventData[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [eventTypes, setEventTypes] = useState<string[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const LIMIT = 80;

  useEffect(() => {
    api.historyV3.getEventTypes().then((d) => setEventTypes(d.event_types)).catch(() => {});
  }, []);

  const fetchEvents = useCallback(async (currentOffset = 0) => {
    setLoading(true);
    try {
      const data = await api.historyV3.searchEvents({
        type: typeFilter || undefined,
        search: search || undefined,
        limit: LIMIT,
        offset: currentOffset,
      });
      if (currentOffset === 0) {
        setEvents(data.events);
      } else {
        setEvents((prev) => [...prev, ...data.events]);
      }
      setTotal(data.total);
      setOffset(currentOffset);
    } catch {
      if (currentOffset === 0) setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [search, typeFilter]);

  useEffect(() => {
    fetchEvents(0);
  }, [fetchEvents]);

  const loadMore = () => fetchEvents(offset + LIMIT);

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-white/[0.04] flex-shrink-0">
        <div className="flex items-center gap-2 bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 w-[300px]">
          <Search size={13} className="text-text-3" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search events by action or reason..."
            className="flex-1 bg-transparent text-[12px] text-text placeholder-text-3 outline-none"
          />
          {search && (
            <button onClick={() => setSearch('')} className="text-text-3 hover:text-text">
              <X size={12} />
            </button>
          )}
        </div>

        {/* Type filter chips */}
        <div className="flex items-center gap-1.5 flex-wrap flex-1">
          <button
            onClick={() => setTypeFilter(null)}
            className={`px-2.5 py-1 rounded-full text-[10px] font-medium border transition-all ${
              !typeFilter
                ? 'bg-accent/15 text-accent border-accent/30'
                : 'bg-white/[0.02] text-text-3 border-white/[0.06] hover:bg-white/[0.04]'
            }`}
          >
            All types
          </button>
          {eventTypes.map((et) => {
            const config = getEventConfig(et);
            const active = typeFilter === et;
            return (
              <button
                key={et}
                onClick={() => setTypeFilter(active ? null : et)}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-medium border transition-all ${
                  active
                    ? `${config.bgColor} ${config.color} ${config.borderColor}`
                    : 'bg-white/[0.02] text-text-3 border-white/[0.06] hover:bg-white/[0.04]'
                }`}
              >
                <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: config.hex }} />
                {et.replace(/_/g, ' ')}
              </button>
            );
          })}
        </div>

        <span className="text-[11px] text-text-3 whitespace-nowrap">
          {total.toLocaleString()} events
        </span>
      </div>

      {/* Events grid */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loading && events.length === 0 ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 size={24} className="text-text-3 animate-spin" />
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-24 text-text-3 text-[13px]">No events found</div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {events.map((event, idx) => (
                <EventCard key={`${event.id}-${idx}`} event={event} />
              ))}
            </div>
            {events.length < total && (
              <div className="flex justify-center mt-6">
                <button
                  onClick={loadMore}
                  disabled={loading}
                  className="px-6 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] text-text-3 text-[12px] font-medium hover:bg-white/[0.06] transition-all flex items-center gap-2"
                >
                  {loading ? <Loader2 size={14} className="animate-spin" /> : <ChevronDown size={14} />}
                  Load more ({events.length} / {total})
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}


// ===========================================================================
// Full Page Entity Lives
// ===========================================================================

function FullPageEntityLives() {
  const [entityLives, setEntityLives] = useState<EntityLife[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const { tickNumber, maxTick } = useWorldStore();
  const effectiveMax = Math.max(maxTick, tickNumber, 1);

  useEffect(() => {
    setLoading(true);
    api.historyV3.getStats()
      .then((data) => setEntityLives(data.entity_lives || []))
      .catch(() => setEntityLives([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = search.trim()
    ? entityLives.filter((e) => e.name.toLowerCase().includes(search.toLowerCase()))
    : entityLives;

  const aliveCount = entityLives.filter((e) => e.is_alive).length;

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-white/[0.04] flex-shrink-0">
        <div className="flex items-center gap-2 bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 w-[300px]">
          <Search size={13} className="text-text-3" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search entities..."
            className="flex-1 bg-transparent text-[12px] text-text placeholder-text-3 outline-none"
          />
        </div>
        <span className="text-[11px] text-text-3">
          <span className="text-green font-medium">{aliveCount}</span> alive / {entityLives.length} total
        </span>
        <div className="flex-1" />
        <span className="text-[10px] mono text-text-3">
          Timeline: 0 &mdash; {effectiveMax.toLocaleString()}
        </span>
      </div>

      {/* Entity rows */}
      <div className="flex-1 overflow-y-auto px-6 py-3">
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 size={24} className="text-text-3 animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-24 text-text-3 text-[13px]">No entities found</div>
        ) : (
          <div className="space-y-1">
            {filtered.map((entity) => {
              const start = (entity.birth_tick / effectiveMax) * 100;
              const end = entity.death_tick
                ? (entity.death_tick / effectiveMax) * 100
                : 100;
              const width = Math.max(0.5, end - start);
              const isGod = entity.is_god;
              const barColor = isGod ? '#fbbf24' : entity.is_alive ? '#4ade80' : '#f87171';
              const lifespan = entity.death_tick
                ? entity.death_tick - entity.birth_tick
                : effectiveMax - entity.birth_tick;

              return (
                <div
                  key={entity.id}
                  className="flex items-center gap-3 py-2 px-3 hover:bg-white/[0.03] rounded-lg transition-colors group"
                >
                  {/* Status dot */}
                  <div
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{
                      backgroundColor: barColor,
                      boxShadow: entity.is_alive ? `0 0 6px ${barColor}60` : 'none',
                    }}
                  />
                  {/* Name */}
                  <div className="w-[120px] flex-shrink-0 truncate">
                    <span
                      className={`text-[12px] font-medium ${
                        isGod ? 'text-amber-400' : entity.is_alive ? 'text-text' : 'text-text-3'
                      }`}
                    >
                      {entity.name}
                    </span>
                    {isGod && (
                      <span className="ml-1 text-[9px] text-amber-400/60 uppercase">god</span>
                    )}
                  </div>
                  {/* Life bar */}
                  <div className="flex-1 h-3 bg-white/[0.03] rounded-full relative overflow-hidden border border-white/[0.04]">
                    <div
                      className="absolute top-0 h-full rounded-full transition-all"
                      style={{
                        left: `${start}%`,
                        width: `${width}%`,
                        backgroundColor: barColor,
                        opacity: entity.is_alive ? 0.7 : 0.4,
                      }}
                    />
                    {entity.death_tick && (
                      <div
                        className="absolute top-0 w-0.5 h-full"
                        style={{
                          left: `${end}%`,
                          backgroundColor: '#f87171',
                        }}
                      />
                    )}
                  </div>
                  {/* Tick range */}
                  <div className="w-[100px] flex-shrink-0 text-right">
                    <span className="text-[10px] mono text-text-3">
                      T:{entity.birth_tick}
                      {entity.death_tick ? ` - ${entity.death_tick}` : ' +'}
                    </span>
                  </div>
                  {/* Lifespan */}
                  <div className="w-[50px] flex-shrink-0 text-right">
                    <span className="text-[10px] mono text-text-3 opacity-60">
                      {lifespan}t
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}


// ===========================================================================
// Full Page Artifacts
// ===========================================================================

function FullPageArtifacts() {
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.artifacts.list()
      .then((data) => setArtifacts(Array.isArray(data) ? data : []))
      .catch(() => setArtifacts([]))
      .finally(() => setLoading(false));
  }, []);

  const typeColors: Record<string, string> = {
    art: '#c084fc',
    story: '#60a5fa',
    law: '#fbbf24',
    currency: '#34d399',
    song: '#f472b6',
    architecture: '#9ca3af',
    tool: '#fb923c',
    ritual: '#a78bfa',
  };

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 size={24} className="text-text-3 animate-spin" />
        </div>
      ) : artifacts.length === 0 ? (
        <div className="text-center py-24 text-text-3 text-[13px]">No artifacts created yet</div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
          {artifacts.map((artifact) => {
            const color = typeColors[artifact.artifact_type] || '#9ca3af';
            return (
              <div
                key={artifact.id}
                className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.04] hover:border-white/[0.1] transition-all cursor-pointer"
              >
                <div
                  className="w-full h-1 rounded-full mb-3"
                  style={{ backgroundColor: color, opacity: 0.6 }}
                />
                <div className="flex items-center gap-1.5 mb-2">
                  <Palette size={12} style={{ color }} />
                  <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color }}>
                    {artifact.artifact_type || 'unknown'}
                  </span>
                </div>
                <p className="text-[13px] font-medium text-text line-clamp-1 mb-1">
                  {artifact.name}
                </p>
                <p className="text-[11px] text-text-3 line-clamp-3 leading-relaxed">
                  {artifact.description}
                </p>
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-[10px] mono text-text-3 opacity-50">
                    T:{artifact.tick_created}
                  </span>
                  {artifact.creator_name && (
                    <span className="text-[10px] text-text-3 truncate max-w-[120px]">
                      by {artifact.creator_name}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}


// ===========================================================================
// Full Page God's Record
// ===========================================================================

function FullPageGodRecord() {
  const [feed, setFeed] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.history.getGodFeed(100)
      .then((data) => setFeed(data.feed || []))
      .catch(() => setFeed([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 size={24} className="text-text-3 animate-spin" />
        </div>
      ) : feed.length === 0 ? (
        <div className="text-center py-24 text-text-3 text-[13px]">No god observations yet</div>
      ) : (
        <div className="max-w-3xl mx-auto space-y-3">
          {feed.map((item, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl bg-amber-400/[0.03] border border-amber-400/[0.08] hover:bg-amber-400/[0.06] transition-all"
            >
              <div className="flex items-center gap-1.5 mb-2">
                <Eye size={13} className="text-amber-400" />
                <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400">
                  {item.type || 'observation'}
                </span>
                {item.tick_number != null && (
                  <span className="ml-auto text-[11px] mono text-text-3 opacity-60">
                    Tick {item.tick_number}
                  </span>
                )}
              </div>
              {item.title && (
                <p className="text-[14px] font-medium text-text leading-relaxed mb-1">
                  {item.title}
                </p>
              )}
              <p className="text-[12px] text-text-2 leading-relaxed">
                {item.content || item.description || item.message || JSON.stringify(item)}
              </p>
              {item.created_at && (
                <p className="text-[10px] text-text-3 opacity-50 mt-2">
                  {new Date(item.created_at).toLocaleString()}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


// ===========================================================================
// Full Page Statistics
// ===========================================================================

function FullPageStatistics() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.historyV3.getStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 size={24} className="text-text-3 animate-spin" />
      </div>
    );
  }

  if (!stats) {
    return <div className="text-center py-24 text-text-3 text-[13px]">No statistics available</div>;
  }

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <BigStatCard label="Alive Entities" value={stats.current.alive_entities} color="#4ade80" />
          <BigStatCard label="Total Entities" value={stats.current.total_entities} color="#60a5fa" />
          <BigStatCard label="Artifacts" value={stats.current.total_artifacts} color="#c084fc" />
          <BigStatCard label="Total Events" value={stats.current.total_events} color="#fbbf24" />
        </div>

        {/* Max tick */}
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] text-center">
          <p className="text-[11px] text-text-3 uppercase tracking-wider mb-1">World Time</p>
          <p className="text-[28px] font-bold mono text-cyan">
            {stats.current.max_tick.toLocaleString()} <span className="text-[14px] text-text-3">ticks</span>
          </p>
        </div>

        {/* Charts in 2-column grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Event type breakdown */}
          {stats.event_type_breakdown.length > 0 && (
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
              <h4 className="text-[12px] font-semibold text-text uppercase tracking-wider mb-3">
                Event Type Breakdown
              </h4>
              <div className="space-y-2">
                {stats.event_type_breakdown.map((item) => {
                  const hex = getTypeColor(item.event_type);
                  const maxCount = stats.event_type_breakdown[0]?.count || 1;
                  const pct = (item.count / maxCount) * 100;
                  return (
                    <div key={item.event_type} className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: hex }} />
                      <span className="text-[11px] text-text-3 w-[120px] truncate">
                        {item.event_type.replace(/_/g, ' ')}
                      </span>
                      <div className="flex-1 h-[8px] bg-white/[0.04] rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${pct}%`, backgroundColor: hex, opacity: 0.7 }}
                        />
                      </div>
                      <span className="text-[11px] mono text-text-3 w-[50px] text-right">
                        {item.count.toLocaleString()}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Births over time */}
          {stats.births_over_time.length > 0 && (
            <BigBarChart title="Entity Births Over Time" data={stats.births_over_time} color="#4ade80" />
          )}

          {/* Deaths over time */}
          {stats.deaths_over_time.length > 0 && (
            <BigBarChart title="Entity Deaths Over Time" data={stats.deaths_over_time} color="#f87171" />
          )}

          {/* Events over time */}
          {stats.events_over_time.length > 0 && (
            <BigBarChart title="Events Over Time" data={stats.events_over_time} color="#60a5fa" />
          )}
        </div>
      </div>
    </div>
  );
}

function BigStatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
      <p className="text-[11px] text-text-3 uppercase tracking-wider mb-1.5">{label}</p>
      <p className="text-[24px] font-bold mono" style={{ color }}>
        {value.toLocaleString()}
      </p>
    </div>
  );
}

function BigBarChart({
  title,
  data,
  color,
}: {
  title: string;
  data: { tick: number; count: number }[];
  color: string;
}) {
  const maxVal = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
      <h4 className="text-[12px] font-semibold text-text uppercase tracking-wider mb-3">
        {title}
      </h4>
      <div className="flex items-end gap-px h-[80px] bg-white/[0.02] rounded-lg p-2 border border-white/[0.04]">
        {data.map((d, idx) => (
          <div
            key={idx}
            className="flex-1 min-w-[3px] rounded-t-sm transition-all hover:opacity-100 group relative"
            style={{
              height: `${(d.count / maxVal) * 100}%`,
              backgroundColor: color,
              opacity: 0.6,
              minHeight: d.count > 0 ? 2 : 0,
            }}
          >
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-10">
              <div className="px-2 py-1 rounded bg-surface border border-border text-[10px] mono text-text whitespace-nowrap shadow-lg">
                Tick {d.tick}: {d.count}
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between mt-1.5">
        <span className="text-[10px] mono text-text-3 opacity-50">
          T:{data[0]?.tick || 0}
        </span>
        <span className="text-[10px] mono text-text-3 opacity-50">
          T:{data[data.length - 1]?.tick || 0}
        </span>
      </div>
    </div>
  );
}
