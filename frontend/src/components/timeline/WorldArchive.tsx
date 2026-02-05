import { useState, useEffect, useCallback, useRef } from 'react';
import {
  ScrollText,
  Filter,
  Search,
  ChevronDown,
  Loader2,
  Users,
  Palette,
  Eye,
  BarChart3,
  Clock,
  X,
} from 'lucide-react';
import { api } from '../../services/api';
import { useWorldStore } from '../../stores/worldStore';
import EventCard, { getEventConfig } from './EventCard';
import type { WorldEventData } from './EventCard';
import DraggablePanel from '../ui/DraggablePanel';

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
// Props
// ---------------------------------------------------------------------------

interface Props {
  visible: boolean;
  onClose: () => void;
}

export default function WorldArchiveTimeline({ visible, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<ArchiveTab>('events');

  const tabBar = (
    <div className="flex items-center gap-0.5 mr-1">
      {([
        { key: 'events' as ArchiveTab, label: 'Events', icon: Clock },
        { key: 'entities' as ArchiveTab, label: 'Entities', icon: Users },
        { key: 'artifacts' as ArchiveTab, label: 'Artifacts', icon: Palette },
        { key: 'god' as ArchiveTab, label: 'God', icon: Eye },
        { key: 'stats' as ArchiveTab, label: 'Stats', icon: BarChart3 },
      ]).map(({ key, label, icon: TabIcon }) => (
        <button
          key={key}
          onClick={() => setActiveTab(key)}
          className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium transition-all ${
            activeTab === key
              ? 'bg-accent/15 text-accent'
              : 'text-text-3 hover:text-text-2'
          }`}
        >
          <TabIcon size={10} />
          {label}
        </button>
      ))}
    </div>
  );

  return (
    <DraggablePanel
      title="World Archive"
      icon={<ScrollText size={13} className="text-accent" />}
      visible={visible}
      onClose={onClose}
      defaultX={Math.round(window.innerWidth - 520)}
      defaultY={50}
      defaultWidth={500}
      defaultHeight={650}
      minWidth={380}
      minHeight={300}
      maxWidth={800}
      maxHeight={900}
      headerExtra={tabBar}
    >
      {activeTab === 'events' && <EventTimelineTab />}
      {activeTab === 'entities' && <EntityLivesTab />}
      {activeTab === 'artifacts' && <ArtifactsGalleryTab />}
      {activeTab === 'god' && <GodRecordTab />}
      {activeTab === 'stats' && <StatisticsTab />}
    </DraggablePanel>
  );
}


// ===========================================================================
// TAB 1: Event Timeline
// ===========================================================================

function EventTimelineTab() {
  const [events, setEvents] = useState<WorldEventData[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [eventTypes, setEventTypes] = useState<string[]>([]);
  const [filterOpen, setFilterOpen] = useState(false);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const LIMIT = 50;
  const scrollRef = useRef<HTMLDivElement>(null);

  // Fetch event types on mount
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

  const loadMore = () => {
    fetchEvents(offset + LIMIT);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Search bar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[0.04] flex-shrink-0">
        <div className="flex-1 flex items-center gap-2 bg-white/[0.03] border border-white/[0.06] rounded-lg px-2.5 py-1.5">
          <Search size={12} className="text-text-3" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search events..."
            className="flex-1 bg-transparent text-[11px] text-text placeholder-text-3 outline-none"
          />
          {search && (
            <button onClick={() => setSearch('')} className="text-text-3 hover:text-text">
              <X size={11} />
            </button>
          )}
        </div>
        <button
          onClick={() => setFilterOpen(!filterOpen)}
          className={`p-1.5 rounded-lg transition-colors ${
            filterOpen || typeFilter
              ? 'bg-accent/10 text-accent'
              : 'hover:bg-white/[0.06] text-text-3'
          }`}
        >
          <Filter size={13} />
        </button>
      </div>

      {/* Filter chips */}
      {filterOpen && (
        <div className="px-3 py-2 border-b border-white/[0.04] flex flex-wrap gap-1.5 flex-shrink-0">
          <button
            onClick={() => setTypeFilter(null)}
            className={`px-2 py-1 rounded-full text-[10px] font-medium border transition-all ${
              !typeFilter
                ? 'bg-accent/15 text-accent border-accent/30'
                : 'bg-white/[0.02] text-text-3 border-white/[0.06] hover:bg-white/[0.04]'
            }`}
          >
            All
          </button>
          {eventTypes.map((et) => {
            const config = getEventConfig(et);
            const active = typeFilter === et;
            return (
              <button
                key={et}
                onClick={() => setTypeFilter(active ? null : et)}
                className={`flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium border transition-all ${
                  active
                    ? `${config.bgColor} ${config.color} ${config.borderColor}`
                    : 'bg-white/[0.02] text-text-3 border-white/[0.06] hover:bg-white/[0.04]'
                }`}
              >
                <div
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ backgroundColor: config.hex }}
                />
                {et.replace(/_/g, ' ')}
              </button>
            );
          })}
        </div>
      )}

      {/* Results count */}
      <div className="px-3 py-1.5 text-[10px] text-text-3 flex-shrink-0">
        {total.toLocaleString()} events
        {typeFilter && <span className="ml-1 text-accent">[{typeFilter.replace(/_/g, ' ')}]</span>}
        {search && <span className="ml-1 text-cyan">matching "{search}"</span>}
      </div>

      {/* Events list */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 pb-3 space-y-1.5">
        {loading && events.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={18} className="text-text-3 animate-spin" />
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-16 text-text-3 text-[12px]">No events found</div>
        ) : (
          <>
            {events.map((event, idx) => (
              <EventCard
                key={`${event.id}-${idx}`}
                event={event}
                style={{ animationDelay: `${Math.min(idx, 10) * 20}ms` }}
              />
            ))}
            {events.length < total && (
              <button
                onClick={loadMore}
                disabled={loading}
                className="w-full py-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04] text-text-3 text-[11px] font-medium hover:bg-white/[0.05] transition-all flex items-center justify-center gap-2"
              >
                {loading ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <ChevronDown size={12} />
                )}
                Load more ({events.length} / {total})
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}


// ===========================================================================
// TAB 2: Entity Lives
// ===========================================================================

function EntityLivesTab() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(false);
  const { tickNumber, maxTick } = useWorldStore();
  const effectiveMax = Math.max(maxTick, tickNumber, 1);

  useEffect(() => {
    setLoading(true);
    api.historyV3.getStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={18} className="text-text-3 animate-spin" />
      </div>
    );
  }

  if (!stats || stats.entity_lives.length === 0) {
    return <div className="text-center py-16 text-text-3 text-[12px]">No entities yet</div>;
  }

  return (
    <div className="overflow-y-auto p-3 space-y-1">
      <div className="text-[10px] text-text-3 mb-2">
        {stats.current.alive_entities} alive / {stats.current.total_entities} total entities
      </div>
      {stats.entity_lives.map((entity) => {
        const start = (entity.birth_tick / effectiveMax) * 100;
        const end = entity.death_tick
          ? (entity.death_tick / effectiveMax) * 100
          : 100;
        const width = Math.max(0.5, end - start);
        const isGod = entity.is_god;
        const barColor = isGod ? '#fbbf24' : entity.is_alive ? '#4ade80' : '#f87171';

        return (
          <div
            key={entity.id}
            className="flex items-center gap-2 py-1.5 hover:bg-white/[0.03] rounded-lg px-2 transition-colors"
          >
            <div className="w-[80px] flex-shrink-0 truncate">
              <span className={`text-[11px] font-medium ${isGod ? 'text-amber-400' : entity.is_alive ? 'text-text' : 'text-text-3'}`}>
                {entity.name}
              </span>
            </div>
            {/* Life bar */}
            <div className="flex-1 h-2 bg-white/[0.04] rounded-full relative overflow-hidden">
              <div
                className="absolute top-0 h-full rounded-full transition-all"
                style={{
                  left: `${start}%`,
                  width: `${width}%`,
                  backgroundColor: barColor,
                  opacity: entity.is_alive ? 0.8 : 0.5,
                }}
              />
              {/* Death marker */}
              {entity.death_tick && (
                <div
                  className="absolute top-0 w-0.5 h-full bg-red-400"
                  style={{ left: `${end}%` }}
                />
              )}
            </div>
            <div className="w-[60px] flex-shrink-0 text-right">
              <span className="text-[9px] mono text-text-3">
                T:{entity.birth_tick}
                {entity.death_tick ? `-${entity.death_tick}` : '+'}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}


// ===========================================================================
// TAB 3: Artifacts Gallery
// ===========================================================================

function ArtifactsGalleryTab() {
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.artifacts.list()
      .then((data) => setArtifacts(Array.isArray(data) ? data : []))
      .catch(() => setArtifacts([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={18} className="text-text-3 animate-spin" />
      </div>
    );
  }

  if (artifacts.length === 0) {
    return <div className="text-center py-16 text-text-3 text-[12px]">No artifacts created yet</div>;
  }

  return (
    <div className="overflow-y-auto p-3">
      <div className="grid grid-cols-2 gap-2">
        {artifacts.map((artifact) => (
          <ArtifactCard key={artifact.id} artifact={artifact} />
        ))}
      </div>
    </div>
  );
}

function ArtifactCard({ artifact }: { artifact: any }) {
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

  const color = typeColors[artifact.artifact_type] || '#9ca3af';

  return (
    <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.04] hover:border-white/[0.1] transition-all cursor-pointer">
      {/* Color bar top */}
      <div
        className="w-full h-1 rounded-full mb-2"
        style={{ backgroundColor: color, opacity: 0.6 }}
      />
      <div className="flex items-center gap-1.5 mb-1">
        <Palette size={10} style={{ color }} />
        <span className="text-[9px] font-semibold uppercase tracking-wider" style={{ color }}>
          {artifact.artifact_type || 'unknown'}
        </span>
      </div>
      <p className="text-[11px] font-medium text-text line-clamp-1 mb-0.5">
        {artifact.name}
      </p>
      <p className="text-[10px] text-text-3 line-clamp-2 leading-relaxed">
        {artifact.description}
      </p>
      <div className="mt-2 flex items-center justify-between">
        <span className="text-[9px] mono text-text-3 opacity-50">
          T:{artifact.tick_created}
        </span>
        {artifact.creator_name && (
          <span className="text-[9px] text-text-3 truncate max-w-[80px]">
            by {artifact.creator_name}
          </span>
        )}
      </div>
    </div>
  );
}


// ===========================================================================
// TAB 4: God's Record
// ===========================================================================

function GodRecordTab() {
  const [feed, setFeed] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.history.getGodFeed(50)
      .then((data) => setFeed(data.feed || []))
      .catch(() => setFeed([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={18} className="text-text-3 animate-spin" />
      </div>
    );
  }

  if (feed.length === 0) {
    return <div className="text-center py-16 text-text-3 text-[12px]">No god observations yet</div>;
  }

  return (
    <div className="overflow-y-auto p-3 space-y-2">
      {feed.map((item, idx) => (
        <div
          key={idx}
          className="p-3 rounded-xl bg-amber-400/[0.03] border border-amber-400/[0.08] hover:bg-amber-400/[0.06] transition-all"
        >
          <div className="flex items-center gap-1.5 mb-1.5">
            <Eye size={11} className="text-amber-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-400">
              {item.type || 'observation'}
            </span>
            {item.tick_number != null && (
              <span className="ml-auto text-[10px] mono text-text-3 opacity-60">
                T:{item.tick_number}
              </span>
            )}
          </div>
          {item.title && (
            <p className="text-[12px] font-medium text-text leading-relaxed mb-0.5">
              {item.title}
            </p>
          )}
          <p className="text-[11px] text-text-2 leading-relaxed line-clamp-4">
            {item.content || item.description || item.message || JSON.stringify(item)}
          </p>
          {item.created_at && (
            <p className="text-[9px] text-text-3 opacity-50 mt-1.5">
              {new Date(item.created_at).toLocaleString()}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}


// ===========================================================================
// TAB 5: Statistics Charts (CSS bar charts)
// ===========================================================================

function StatisticsTab() {
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
      <div className="flex items-center justify-center py-16">
        <Loader2 size={18} className="text-text-3 animate-spin" />
      </div>
    );
  }

  if (!stats) {
    return <div className="text-center py-16 text-text-3 text-[12px]">No statistics available</div>;
  }

  return (
    <div className="overflow-y-auto p-3 space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-2">
        <StatCard label="Alive Entities" value={stats.current.alive_entities} color="#4ade80" />
        <StatCard label="Total Entities" value={stats.current.total_entities} color="#60a5fa" />
        <StatCard label="Artifacts" value={stats.current.total_artifacts} color="#c084fc" />
        <StatCard label="Total Events" value={stats.current.total_events} color="#fbbf24" />
      </div>

      {/* Event type breakdown */}
      {stats.event_type_breakdown.length > 0 && (
        <div>
          <h4 className="text-[11px] font-semibold text-text uppercase tracking-wider mb-2">
            Event Type Breakdown
          </h4>
          <div className="space-y-1.5">
            {stats.event_type_breakdown.map((item) => {
              const config = getEventConfig(item.event_type);
              const maxCount = stats.event_type_breakdown[0]?.count || 1;
              const pct = (item.count / maxCount) * 100;
              return (
                <div key={item.event_type} className="flex items-center gap-2">
                  <span className="text-[10px] text-text-3 w-[100px] truncate">
                    {item.event_type.replace(/_/g, ' ')}
                  </span>
                  <div className="flex-1 h-[6px] bg-white/[0.04] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: config.hex,
                        opacity: 0.7,
                      }}
                    />
                  </div>
                  <span className="text-[10px] mono text-text-3 w-[40px] text-right">
                    {item.count}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Births over time chart */}
      {stats.births_over_time.length > 0 && (
        <BarChartSection
          title="Entity Births Over Time"
          data={stats.births_over_time}
          color="#4ade80"
        />
      )}

      {/* Deaths over time chart */}
      {stats.deaths_over_time.length > 0 && (
        <BarChartSection
          title="Entity Deaths Over Time"
          data={stats.deaths_over_time}
          color="#f87171"
        />
      )}

      {/* Events over time chart */}
      {stats.events_over_time.length > 0 && (
        <BarChartSection
          title="Events Over Time"
          data={stats.events_over_time}
          color="#60a5fa"
        />
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
      <p className="text-[10px] text-text-3 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-[18px] font-bold mono" style={{ color }}>
        {value.toLocaleString()}
      </p>
    </div>
  );
}

function BarChartSection({
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
    <div>
      <h4 className="text-[11px] font-semibold text-text uppercase tracking-wider mb-2">
        {title}
      </h4>
      <div className="flex items-end gap-px h-[60px] bg-white/[0.02] rounded-lg p-1.5 border border-white/[0.04]">
        {data.map((d, idx) => (
          <div
            key={idx}
            className="flex-1 min-w-[2px] rounded-t-sm transition-all hover:opacity-100 group relative"
            style={{
              height: `${(d.count / maxVal) * 100}%`,
              backgroundColor: color,
              opacity: 0.6,
              minHeight: d.count > 0 ? 2 : 0,
            }}
            title={`Tick ${d.tick}: ${d.count}`}
          >
            {/* Hover tooltip via CSS */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-10">
              <div className="px-1.5 py-0.5 rounded bg-surface border border-border text-[9px] mono text-text whitespace-nowrap">
                T:{d.tick} = {d.count}
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between mt-1">
        <span className="text-[9px] mono text-text-3 opacity-50">
          T:{data[0]?.tick || 0}
        </span>
        <span className="text-[9px] mono text-text-3 opacity-50">
          T:{data[data.length - 1]?.tick || 0}
        </span>
      </div>
    </div>
  );
}
