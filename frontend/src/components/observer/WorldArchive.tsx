import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Sparkles,
  X,
  MessageCircle,
  Eye,
  Lightbulb,
  Palette,
  Users,
  Zap,
  Filter,
  Search,
  ChevronDown,
  ChevronRight,
  ScrollText,
  BookOpen,
  Loader2,
  Clock,
  BarChart3,
  Skull,
  Brain,
  Swords,
  Building2,
} from 'lucide-react';
import { api } from '../../services/api';
import { useSagaStore } from '../../stores/sagaStore';
import { useDetailStore } from '../../stores/detailStore';
import { useWorldStore } from '../../stores/worldStore';
import SagaView from './SagaView';
import DraggablePanel from '../ui/DraggablePanel';

// ---- Event type configuration ----

const EVENT_TYPES = [
  'ai_birth',
  'ai_death',
  'interaction',
  'god_message',
  'god_observation',
  'concept_created',
  'artifact_created',
  'organization_formed',
  'entity_thought',
  'entity_died',
  'conflict',
  'building',
] as const;

const eventTypeIcons: Record<string, typeof Sparkles> = {
  ai_birth: Sparkles,
  ai_death: Skull,
  entity_died: Skull,
  interaction: MessageCircle,
  god_message: Eye,
  god_observation: Eye,
  concept_created: Lightbulb,
  artifact_created: Palette,
  organization_formed: Users,
  entity_thought: Brain,
  conflict: Swords,
  building: Building2,
};

const eventTypeColors: Record<string, { text: string; bg: string; border: string; hex: string }> = {
  ai_birth:            { text: 'text-green',    bg: 'bg-green/10',    border: 'border-green/20',    hex: '#34d399' },
  ai_death:            { text: 'text-red-400',  bg: 'bg-red-400/10',  border: 'border-red-400/20',  hex: '#f87171' },
  entity_died:         { text: 'text-red-400',  bg: 'bg-red-400/10',  border: 'border-red-400/20',  hex: '#f87171' },
  interaction:         { text: 'text-rose',     bg: 'bg-rose-400/10', border: 'border-rose-400/20', hex: '#f472b6' },
  god_message:         { text: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/20', hex: '#fbbf24' },
  god_observation:     { text: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/20', hex: '#fbbf24' },
  concept_created:     { text: 'text-cyan',     bg: 'bg-cyan/10',     border: 'border-cyan/20',     hex: '#58d5f0' },
  artifact_created:    { text: 'text-purple-400', bg: 'bg-purple-400/10', border: 'border-purple-400/20', hex: '#c084fc' },
  organization_formed: { text: 'text-green',    bg: 'bg-green/10',    border: 'border-green/20',    hex: '#4ade80' },
  entity_thought:      { text: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/20', hex: '#60a5fa' },
  conflict:            { text: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/20', hex: '#fb923c' },
  building:            { text: 'text-gray-400', bg: 'bg-gray-400/10', border: 'border-gray-400/20', hex: '#9ca3af' },
};

const defaultColor = { text: 'text-text-3', bg: 'bg-white/5', border: 'border-white/10', hex: '#8a8694' };

function getIcon(eventType: string) {
  return eventTypeIcons[eventType] || Zap;
}

function getColor(eventType: string) {
  return eventTypeColors[eventType] || defaultColor;
}

// ---- Normalize timeline API response ----
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

// ---- Era grouping helpers ----
const ERA_SIZE = 50;

interface Era {
  label: string;
  startTick: number;
  endTick: number;
  events: TimelineEvent[];
}

function groupByEra(events: TimelineEvent[]): Era[] {
  const eraMap = new Map<number, TimelineEvent[]>();
  for (const event of events) {
    const eraIndex = Math.floor(event.tick_number / ERA_SIZE);
    if (!eraMap.has(eraIndex)) eraMap.set(eraIndex, []);
    eraMap.get(eraIndex)!.push(event);
  }
  const eras: Era[] = [];
  const sortedKeys = Array.from(eraMap.keys()).sort((a, b) => b - a);
  for (const eraIndex of sortedKeys) {
    const eraEvents = eraMap.get(eraIndex)!;
    eras.push({
      label: `${eraIndex + 1}`,
      startTick: eraIndex * ERA_SIZE,
      endTick: (eraIndex + 1) * ERA_SIZE - 1,
      events: eraEvents.sort((a, b) => b.tick_number - a.tick_number),
    });
  }
  return eras;
}

// ---- Importance bar ----
function ImportanceBar({ importance, hex }: { importance: number; hex: string }) {
  return (
    <div className="flex-1 h-[2px] bg-white/[0.04] rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{
          width: `${Math.min(100, importance * 100)}%`,
          backgroundColor: hex,
          opacity: 0.6,
        }}
      />
    </div>
  );
}

// ---- Tab type ----
type ArchiveTab = 'timeline' | 'saga' | 'entities' | 'artifacts' | 'god' | 'stats';

// ---- Main component ----
interface Props {
  visible: boolean;
  onClose: () => void;
}

export default function WorldArchive({ visible, onClose }: Props) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<ArchiveTab>('timeline');
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set());
  const [collapsedEras, setCollapsedEras] = useState<Set<string>>(new Set());
  const [limit, setLimit] = useState(100);
  const [hasMore, setHasMore] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { hasNewChapter, clearNewFlag } = useSagaStore();

  const loadEvents = useCallback(async (currentLimit: number) => {
    try {
      const data = await api.history.getTimeline(currentLimit);
      const normalized = (data || []).map(normalizeEvent);
      setEvents(normalized);
      setHasMore(normalized.length >= currentLimit);
    } catch {
      setEvents([]);
      setHasMore(false);
    }
  }, []);

  useEffect(() => {
    if (!visible || activeTab !== 'timeline') return;
    setLoading(true);
    loadEvents(limit).finally(() => setLoading(false));
    const interval = setInterval(() => loadEvents(limit), 10000);
    return () => clearInterval(interval);
  }, [visible, limit, loadEvents, activeTab]);

  const handleLoadMore = async () => {
    setLoadingMore(true);
    const newLimit = limit + 100;
    setLimit(newLimit);
    await loadEvents(newLimit);
    setLoadingMore(false);
  };

  const handleScroll = () => {
    if (!scrollRef.current || loadingMore || !hasMore) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    if (scrollHeight - scrollTop - clientHeight < 100) handleLoadMore();
  };

  const toggleFilter = (eventType: string) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(eventType)) next.delete(eventType);
      else next.add(eventType);
      return next;
    });
  };

  const toggleEra = (eraLabel: string) => {
    setCollapsedEras((prev) => {
      const next = new Set(prev);
      if (next.has(eraLabel)) next.delete(eraLabel);
      else next.add(eraLabel);
      return next;
    });
  };

  const handleSagaTab = () => {
    setActiveTab('saga');
    clearNewFlag();
  };

  // Filter events by type and search text
  let filteredEvents = activeFilters.size === 0
    ? events
    : events.filter((e) => activeFilters.has(e.event_type));

  if (searchText.trim()) {
    const q = searchText.toLowerCase();
    filteredEvents = filteredEvents.filter(
      (e) =>
        (e.title && e.title.toLowerCase().includes(q)) ||
        (e.description && e.description.toLowerCase().includes(q)) ||
        e.event_type.toLowerCase().includes(q)
    );
  }

  const eras = groupByEra(filteredEvents);

  // Tab bar as header extra
  const tabBar = (
    <div className="flex items-center gap-0.5 mr-1 overflow-x-auto">
      {([
        { key: 'timeline' as ArchiveTab, label: t('timeline_tab'), icon: Clock },
        { key: 'entities' as ArchiveTab, label: 'Entities', icon: Users },
        { key: 'artifacts' as ArchiveTab, label: 'Artifacts', icon: Palette },
        { key: 'god' as ArchiveTab, label: 'God', icon: Eye },
        { key: 'stats' as ArchiveTab, label: 'Stats', icon: BarChart3 },
      ]).map(({ key, label, icon: TabIcon }) => (
        <button
          key={key}
          onClick={() => setActiveTab(key)}
          className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium transition-all whitespace-nowrap ${
            activeTab === key
              ? 'bg-accent/15 text-accent'
              : 'text-text-3 hover:text-text-2'
          }`}
        >
          <TabIcon size={10} />
          {label}
        </button>
      ))}
      <button
        onClick={handleSagaTab}
        className={`relative flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium transition-all whitespace-nowrap ${
          activeTab === 'saga'
            ? 'bg-gold/15'
            : 'text-text-3 hover:text-text-2'
        }`}
        style={activeTab === 'saga' ? { color: '#d4a574' } : undefined}
      >
        <BookOpen size={10} />
        {t('saga_tab')}
        {hasNewChapter && activeTab !== 'saga' && (
          <span
            className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full animate-pulse"
            style={{ backgroundColor: '#d4a574' }}
          />
        )}
      </button>
    </div>
  );

  return (
    <DraggablePanel
      title={t('world_archive')}
      icon={<ScrollText size={13} className="text-accent" />}
      visible={visible}
      onClose={onClose}
      defaultX={Math.round(window.innerWidth - 480)}
      defaultY={50}
      defaultWidth={460}
      defaultHeight={650}
      minWidth={340}
      minHeight={300}
      maxWidth={800}
      maxHeight={900}
      headerExtra={tabBar}
    >
      {activeTab === 'timeline' ? (
        <>
          {/* Search + Filter row */}
          <div className="flex items-center gap-2 px-3 py-1.5 flex-shrink-0">
            <div className="flex-1 flex items-center gap-2 bg-white/[0.03] border border-white/[0.06] rounded-lg px-2 py-1">
              <Search size={11} className="text-text-3 flex-shrink-0" />
              <input
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder={t('search_events') || 'Search events...'}
                className="flex-1 bg-transparent text-[11px] text-text placeholder-text-3 outline-none min-w-0"
              />
              {searchText && (
                <button onClick={() => setSearchText('')} className="text-text-3 hover:text-text">
                  <X size={10} />
                </button>
              )}
            </div>
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className={`relative p-1.5 rounded-lg transition-colors flex-shrink-0 ${
                filterOpen || activeFilters.size > 0
                  ? 'bg-accent/10 text-accent'
                  : 'hover:bg-white/[0.08] text-text-3 hover:text-text'
              }`}
              title={t('filter_events')}
            >
              <Filter size={13} />
              {activeFilters.size > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-accent" />
              )}
            </button>
          </div>

          {filterOpen && (
            <div className="px-3 py-2.5 border-b border-white/[0.04] fade-in">
              <div className="flex flex-wrap gap-1.5">
                {EVENT_TYPES.map((type) => {
                  const color = getColor(type);
                  const active = activeFilters.has(type);
                  const Icon = getIcon(type);
                  return (
                    <button
                      key={type}
                      onClick={() => toggleFilter(type)}
                      className={`flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium transition-all duration-200 border ${
                        active
                          ? `${color.bg} ${color.text} ${color.border}`
                          : 'bg-white/[0.02] text-text-3 border-white/[0.06] hover:bg-white/[0.05] hover:text-text-2'
                      }`}
                    >
                      <Icon size={10} />
                      {type.replace(/_/g, ' ')}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto"
          >
            {loading && events.length === 0 ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 size={18} className="text-text-3 animate-spin" />
              </div>
            ) : eras.length === 0 ? (
              <EmptyState message={searchText ? `No events matching "${searchText}"` : t('no_events')} />
            ) : (
              <div className="p-3 space-y-2">
                {eras.map((era) => (
                  <EraSection
                    key={era.label}
                    era={era}
                    collapsed={collapsedEras.has(era.label)}
                    onToggle={() => toggleEra(era.label)}
                    t={t}
                  />
                ))}
                {hasMore && (
                  <button
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className="w-full py-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04] text-text-3 text-[11px] font-medium hover:bg-white/[0.05] hover:text-text-2 transition-all duration-200 flex items-center justify-center gap-2"
                  >
                    {loadingMore ? <Loader2 size={12} className="animate-spin" /> : <ChevronDown size={12} />}
                    {t('load_more')}
                  </button>
                )}
              </div>
            )}
          </div>
        </>
      ) : activeTab === 'entities' ? (
        <EntityLivesPanel />
      ) : activeTab === 'artifacts' ? (
        <ArtifactsGalleryPanel />
      ) : activeTab === 'god' ? (
        <GodRecordPanel />
      ) : activeTab === 'stats' ? (
        <StatisticsPanel />
      ) : (
        <SagaView />
      )}
    </DraggablePanel>
  );
}


// ===========================================================================
// Era section
// ===========================================================================

function EraSection({
  era,
  collapsed,
  onToggle,
  t,
}: {
  era: Era;
  collapsed: boolean;
  onToggle: () => void;
  t: (key: string) => string;
}) {
  return (
    <div className="fade-in">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-white/[0.03] transition-colors group"
      >
        <div className="text-text-3 group-hover:text-text-2 transition-colors">
          {collapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-medium text-accent uppercase tracking-wider">
            {t('era')} {era.label}
          </span>
          <span className="text-[10px] mono text-text-3">
            T:{era.startTick}&ndash;{era.endTick}
          </span>
        </div>
        <span className="ml-auto text-[10px] mono text-text-3 opacity-60">
          {era.events.length}
        </span>
      </button>

      {!collapsed && (
        <div className="ml-3 pl-3 border-l border-white/[0.06] space-y-1.5 mt-1 mb-2">
          {era.events.map((event, idx) => (
            <TimelineEventCard
              key={event.id}
              event={event}
              style={{ animationDelay: `${idx * 30}ms` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}


// ===========================================================================
// Single timeline event card
// ===========================================================================

function TimelineEventCard({
  event,
  style,
}: {
  event: TimelineEvent;
  style?: React.CSSProperties;
}) {
  const openDetail = useDetailStore((s) => s.openDetail);
  const Icon = getIcon(event.event_type);
  const color = getColor(event.event_type);

  return (
    <button
      onClick={() => openDetail('event', event)}
      className="relative w-full text-left p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-all duration-200 fade-in cursor-pointer"
      style={style}
    >
      <div
        className="absolute -left-[19px] top-3.5 w-2.5 h-2.5 rounded-full border-2"
        style={{
          borderColor: color.hex,
          backgroundColor: `${color.hex}40`,
          boxShadow: `0 0 6px ${color.hex}30`,
        }}
      />
      <div className="flex items-center gap-1.5 mb-1">
        <div className={`flex-shrink-0 ${color.text}`}>
          <Icon size={12} />
        </div>
        <span className={`text-[10px] font-medium uppercase tracking-wider ${color.text}`}>
          {event.event_type.replace(/_/g, ' ')}
        </span>
        <span className="ml-auto text-[10px] mono text-text-3 opacity-60 flex-shrink-0">
          T:{event.tick_number}
        </span>
      </div>
      {event.title && (
        <p className="text-[12px] font-medium text-text leading-relaxed mb-0.5">
          {event.title}
        </p>
      )}
      {event.description && (
        <p className="text-[11px] text-text-2 leading-relaxed line-clamp-3">
          {event.description}
        </p>
      )}
      <div className="flex items-center gap-2 mt-2">
        <ImportanceBar importance={event.importance} hex={color.hex} />
        <span className="text-[9px] mono text-text-3 opacity-50 flex-shrink-0">
          {(event.importance * 100).toFixed(0)}%
        </span>
      </div>
    </button>
  );
}


// ===========================================================================
// Entity Lives Panel
// ===========================================================================

interface EntityLife {
  id: string;
  name: string;
  is_alive: boolean;
  birth_tick: number;
  death_tick: number | null;
  is_god: boolean;
}

function EntityLivesPanel() {
  const [entityLives, setEntityLives] = useState<EntityLife[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const { tickNumber, maxTick } = useWorldStore();
  const effectiveMax = Math.max(maxTick, tickNumber, 1);

  useEffect(() => {
    setLoading(true);
    api.historyV3.getStats()
      .then((data) => setEntityLives(data.entity_lives || []))
      .catch(() => setEntityLives([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={18} className="text-text-3 animate-spin" />
      </div>
    );
  }

  const filtered = searchText.trim()
    ? entityLives.filter((e) => e.name.toLowerCase().includes(searchText.toLowerCase()))
    : entityLives;

  if (entityLives.length === 0) {
    return <EmptyState message="No entities yet" />;
  }

  const aliveCount = entityLives.filter((e) => e.is_alive).length;

  return (
    <div className="flex flex-col h-full">
      {/* Search + summary */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[0.04] flex-shrink-0">
        <div className="flex-1 flex items-center gap-2 bg-white/[0.03] border border-white/[0.06] rounded-lg px-2 py-1">
          <Search size={11} className="text-text-3 flex-shrink-0" />
          <input
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search entities..."
            className="flex-1 bg-transparent text-[11px] text-text placeholder-text-3 outline-none min-w-0"
          />
        </div>
        <span className="text-[10px] text-text-3 whitespace-nowrap">
          <span className="text-green">{aliveCount}</span> / {entityLives.length}
        </span>
      </div>

      {/* Entity life bars */}
      <div className="flex-1 overflow-y-auto p-3 space-y-0.5">
        {filtered.map((entity) => {
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
                <span
                  className={`text-[11px] font-medium ${
                    isGod ? 'text-amber-400' : entity.is_alive ? 'text-text' : 'text-text-3'
                  }`}
                >
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
    </div>
  );
}


// ===========================================================================
// Artifacts Gallery Panel
// ===========================================================================

function ArtifactsGalleryPanel() {
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
    return <EmptyState message="No artifacts created yet" />;
  }

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
    <div className="overflow-y-auto p-3">
      <div className="grid grid-cols-2 gap-2">
        {artifacts.map((artifact) => {
          const color = typeColors[artifact.artifact_type] || '#9ca3af';
          return (
            <div
              key={artifact.id}
              className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.04] hover:border-white/[0.1] transition-all cursor-pointer"
            >
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
        })}
      </div>
    </div>
  );
}


// ===========================================================================
// God's Record Panel
// ===========================================================================

function GodRecordPanel() {
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
    return <EmptyState message="No god observations yet" />;
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
// Statistics Panel (CSS bar charts)
// ===========================================================================

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
  entity_lives: any[];
}

function StatisticsPanel() {
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
    return <EmptyState message="No statistics available" />;
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

      {/* Max tick indicator */}
      <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.06] text-center">
        <p className="text-[10px] text-text-3 uppercase tracking-wider mb-0.5">Current Tick</p>
        <p className="text-[20px] font-bold mono text-cyan">{stats.current.max_tick.toLocaleString()}</p>
      </div>

      {/* Event type breakdown */}
      {stats.event_type_breakdown.length > 0 && (
        <div>
          <h4 className="text-[11px] font-semibold text-text uppercase tracking-wider mb-2">
            Event Types
          </h4>
          <div className="space-y-1.5">
            {stats.event_type_breakdown.map((item) => {
              const color = getColor(item.event_type);
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
                        backgroundColor: color.hex,
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

      {/* Births over time */}
      {stats.births_over_time.length > 0 && (
        <BarChartSection title="Births Over Time" data={stats.births_over_time} color="#4ade80" />
      )}

      {/* Deaths over time */}
      {stats.deaths_over_time.length > 0 && (
        <BarChartSection title="Deaths Over Time" data={stats.deaths_over_time} color="#f87171" />
      )}

      {/* Events over time */}
      {stats.events_over_time.length > 0 && (
        <BarChartSection title="Events Over Time" data={stats.events_over_time} color="#60a5fa" />
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


// ===========================================================================
// Empty state
// ===========================================================================

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-16">
      <div className="relative w-10 h-10 mx-auto mb-4">
        <div className="absolute inset-0 rounded-full border border-border/50 pulse-ring" />
        <div className="absolute inset-0 flex items-center justify-center">
          <ScrollText size={16} className="text-text-3" />
        </div>
      </div>
      <p className="text-text-3 text-[12px]">{message}</p>
    </div>
  );
}
