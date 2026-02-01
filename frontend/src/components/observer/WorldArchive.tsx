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
  ChevronDown,
  ChevronRight,
  ScrollText,
  BookOpen,
  Loader2,
} from 'lucide-react';
import { api } from '../../services/api';
import { useSagaStore } from '../../stores/sagaStore';
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
] as const;

const eventTypeIcons: Record<string, typeof Sparkles> = {
  ai_birth: Sparkles,
  ai_death: X,
  interaction: MessageCircle,
  god_message: Eye,
  god_observation: Eye,
  concept_created: Lightbulb,
  artifact_created: Palette,
  organization_formed: Users,
};

const eventTypeColors: Record<string, { text: string; bg: string; border: string; hex: string }> = {
  ai_birth:            { text: 'text-green',    bg: 'bg-green/10',    border: 'border-green/20',    hex: '#34d399' },
  ai_death:            { text: 'text-orange',   bg: 'bg-orange/10',   border: 'border-orange/20',   hex: '#fb923c' },
  interaction:         { text: 'text-rose',     bg: 'bg-rose-400/10', border: 'border-rose-400/20', hex: '#f472b6' },
  god_message:         { text: 'text-accent',   bg: 'bg-accent/10',   border: 'border-accent/20',   hex: '#7c5bf5' },
  god_observation:     { text: 'text-accent',   bg: 'bg-accent/10',   border: 'border-accent/20',   hex: '#7c5bf5' },
  concept_created:     { text: 'text-cyan',     bg: 'bg-cyan/10',     border: 'border-cyan/20',     hex: '#58d5f0' },
  artifact_created:    { text: 'text-cyan',     bg: 'bg-cyan/10',     border: 'border-cyan/20',     hex: '#67e8f9' },
  organization_formed: { text: 'text-green',    bg: 'bg-green/10',    border: 'border-green/20',    hex: '#4ade80' },
};

const defaultColor = { text: 'text-text-3', bg: 'bg-white/5', border: 'border-white/10', hex: '#8a8694' };

function getIcon(eventType: string) {
  return eventTypeIcons[eventType] || Zap;
}

function getColor(eventType: string) {
  return eventTypeColors[eventType] || defaultColor;
}

// ---- Normalize timeline API response ----
// API returns { type, timestamp } but our code expects { event_type, created_at }
interface TimelineEvent {
  id: string;
  event_type: string;
  importance: number;
  title: string;
  description?: string;
  tick_number: number;
  created_at: string;
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
    if (!eraMap.has(eraIndex)) {
      eraMap.set(eraIndex, []);
    }
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

type ArchiveTab = 'timeline' | 'saga';

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
    if (!visible) return;
    setLoading(true);
    loadEvents(limit).finally(() => setLoading(false));
    const interval = setInterval(() => loadEvents(limit), 10000);
    return () => clearInterval(interval);
  }, [visible, limit, loadEvents]);

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
    if (scrollHeight - scrollTop - clientHeight < 100) {
      handleLoadMore();
    }
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

  const filteredEvents =
    activeFilters.size === 0
      ? events
      : events.filter((e) => activeFilters.has(e.event_type));

  const eras = groupByEra(filteredEvents);

  // Tab bar as header extra
  const tabBar = (
    <div className="flex items-center gap-0.5 mr-1">
      <button
        onClick={() => setActiveTab('timeline')}
        className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all ${
          activeTab === 'timeline'
            ? 'bg-accent/15 text-accent'
            : 'text-text-3 hover:text-text-2'
        }`}
      >
        {t('timeline_tab')}
      </button>
      <button
        onClick={handleSagaTab}
        className={`relative px-2 py-0.5 rounded text-[10px] font-medium transition-all ${
          activeTab === 'saga'
            ? 'bg-gold/15'
            : 'text-text-3 hover:text-text-2'
        }`}
        style={activeTab === 'saga' ? { color: '#d4a574' } : undefined}
      >
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
      defaultX={Math.round(window.innerWidth - 420)}
      defaultY={60}
      defaultWidth={400}
      defaultHeight={600}
      minWidth={320}
      minHeight={300}
      maxWidth={700}
      maxHeight={900}
      headerExtra={tabBar}
    >
      {activeTab === 'timeline' ? (
        <>
          {/* Filter row */}
          <div className="flex items-center justify-end px-3 py-1.5 flex-shrink-0">
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className={`relative p-1.5 rounded-lg transition-colors ${
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
              <EmptyState message={t('no_events')} />
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
      ) : (
        <SagaView />
      )}
    </DraggablePanel>
  );
}

// ---- Era section ----

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

// ---- Single timeline event ----

function TimelineEventCard({
  event,
  style,
}: {
  event: TimelineEvent;
  style?: React.CSSProperties;
}) {
  const Icon = getIcon(event.event_type);
  const color = getColor(event.event_type);

  return (
    <div
      className="relative p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-all duration-200 fade-in"
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
    </div>
  );
}

// ---- Empty state ----

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
