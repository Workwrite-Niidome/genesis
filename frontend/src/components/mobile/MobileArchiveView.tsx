import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ScrollText,
  BookOpen,
  Filter,
  ChevronDown,
  ChevronRight,
  Loader2,
  Sparkles,
  X,
  MessageCircle,
  Eye,
  Lightbulb,
  Palette,
  Users,
  Zap,
} from 'lucide-react';
import { api } from '../../services/api';
import { useSagaStore } from '../../stores/sagaStore';
import { useDetailStore } from '../../stores/detailStore';
import SagaView from '../observer/SagaView';

// ---- Reuse event config from WorldArchive ----

const EVENT_TYPES = [
  'ai_birth', 'ai_death', 'interaction', 'god_message', 'god_observation',
  'concept_created', 'artifact_created', 'organization_formed',
] as const;

const eventTypeIcons: Record<string, typeof Sparkles> = {
  ai_birth: Sparkles, ai_death: X, interaction: MessageCircle,
  god_message: Eye, god_observation: Eye, concept_created: Lightbulb,
  artifact_created: Palette, organization_formed: Users,
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

type ArchiveTab = 'timeline' | 'saga';

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
  const sortedKeys = Array.from(eraMap.keys()).sort((a, b) => b - a);
  return sortedKeys.map((eraIndex) => ({
    label: `${eraIndex + 1}`,
    startTick: eraIndex * ERA_SIZE,
    endTick: (eraIndex + 1) * ERA_SIZE - 1,
    events: eraMap.get(eraIndex)!.sort((a, b) => b.tick_number - a.tick_number),
  }));
}

export default function MobileArchiveView() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<ArchiveTab>('timeline');
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterOpen, setFilterOpen] = useState(false);
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set());
  const [collapsedEras, setCollapsedEras] = useState<Set<string>>(new Set());
  const [limit, setLimit] = useState(100);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { hasNewChapter, clearNewFlag } = useSagaStore();
  const openDetail = useDetailStore((s) => s.openDetail);

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
    setLoading(true);
    loadEvents(limit).finally(() => setLoading(false));
    const interval = setInterval(() => loadEvents(limit), 10000);
    return () => clearInterval(interval);
  }, [limit, loadEvents]);

  const handleLoadMore = async () => {
    setLoadingMore(true);
    const newLimit = limit + 100;
    setLimit(newLimit);
    await loadEvents(newLimit);
    setLoadingMore(false);
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

  const filteredEvents = activeFilters.size === 0 ? events : events.filter((e) => activeFilters.has(e.event_type));
  const eras = groupByEra(filteredEvents);

  return (
    <div className="h-full flex flex-col">
      {/* Sub-tab bar */}
      <div className="flex border-b border-border flex-shrink-0">
        <button
          onClick={() => setActiveTab('timeline')}
          className={`flex-1 flex items-center justify-center gap-2 py-3 text-[11px] font-medium uppercase tracking-wider transition-colors ${
            activeTab === 'timeline'
              ? 'text-accent border-b-2 border-accent bg-white/[0.02]'
              : 'text-text-3'
          }`}
        >
          <ScrollText size={13} />
          {t('timeline_tab')}
        </button>
        <button
          onClick={handleSagaTab}
          className={`relative flex-1 flex items-center justify-center gap-2 py-3 text-[11px] font-medium uppercase tracking-wider transition-colors ${
            activeTab === 'saga'
              ? 'border-b-2 bg-white/[0.02]'
              : 'text-text-3'
          }`}
          style={activeTab === 'saga' ? { color: '#d4a574', borderColor: '#d4a574' } : undefined}
        >
          <BookOpen size={13} />
          {t('saga_tab')}
          {hasNewChapter && activeTab !== 'saga' && (
            <span className="absolute top-2 right-[30%] w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: '#d4a574' }} />
          )}
        </button>
      </div>

      {/* Content */}
      {activeTab === 'saga' ? (
        <div className="flex-1 overflow-y-auto">
          <SagaView />
        </div>
      ) : (
        <>
          {/* Filter toggle */}
          <div className="flex items-center justify-between px-4 py-2 flex-shrink-0">
            <span className="text-[11px] text-text-3">{events.length} {t('events')}</span>
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className={`relative p-2 rounded-lg transition-colors touch-target ${
                filterOpen || activeFilters.size > 0 ? 'bg-accent/10 text-accent' : 'text-text-3'
              }`}
            >
              <Filter size={14} />
              {activeFilters.size > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-accent" />
              )}
            </button>
          </div>

          {filterOpen && (
            <div className="px-4 pb-3 fade-in">
              <div className="flex flex-wrap gap-1.5">
                {EVENT_TYPES.map((type) => {
                  const color = eventTypeColors[type] || defaultColor;
                  const active = activeFilters.has(type);
                  const Icon = eventTypeIcons[type] || Zap;
                  return (
                    <button
                      key={type}
                      onClick={() => toggleFilter(type)}
                      className={`flex items-center gap-1 px-2.5 py-1.5 rounded-full text-[10px] font-medium border touch-target ${
                        active
                          ? `${color.bg} ${color.text} ${color.border}`
                          : 'bg-white/[0.02] text-text-3 border-white/[0.06]'
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

          {/* Timeline */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 pb-3">
            {loading && events.length === 0 ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 size={18} className="text-text-3 animate-spin" />
              </div>
            ) : eras.length === 0 ? (
              <div className="text-center py-16">
                <p className="text-text-3 text-[12px]">{t('no_events')}</p>
              </div>
            ) : (
              <div className="space-y-2">
                {eras.map((era) => (
                  <div key={era.label} className="fade-in">
                    <button
                      onClick={() => toggleEra(era.label)}
                      className="w-full flex items-center gap-2 px-2 py-2 rounded-lg active:bg-white/[0.03] transition-colors touch-target"
                    >
                      {collapsedEras.has(era.label) ? <ChevronRight size={12} className="text-text-3" /> : <ChevronDown size={12} className="text-text-3" />}
                      <span className="text-[11px] font-medium text-accent uppercase tracking-wider">{t('era')} {era.label}</span>
                      <span className="text-[10px] mono text-text-3">T:{era.startTick}&ndash;{era.endTick}</span>
                      <span className="ml-auto text-[10px] mono text-text-3 opacity-60">{era.events.length}</span>
                    </button>
                    {!collapsedEras.has(era.label) && (
                      <div className="ml-3 pl-3 border-l border-white/[0.06] space-y-1.5 mt-1 mb-2">
                        {era.events.map((event) => {
                          const color = eventTypeColors[event.event_type] || defaultColor;
                          const Icon = eventTypeIcons[event.event_type] || Zap;
                          return (
                            <button
                              key={event.id}
                              onClick={() => openDetail('event', event)}
                              className="relative w-full text-left p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] active:bg-white/[0.05] transition-colors touch-target"
                            >
                              <div
                                className="absolute -left-[19px] top-3.5 w-2.5 h-2.5 rounded-full border-2"
                                style={{ borderColor: color.hex, backgroundColor: `${color.hex}40`, boxShadow: `0 0 6px ${color.hex}30` }}
                              />
                              <div className="flex items-center gap-1.5 mb-1">
                                <Icon size={12} className={color.text} />
                                <span className={`text-[10px] font-medium uppercase tracking-wider ${color.text}`}>
                                  {event.event_type.replace(/_/g, ' ')}
                                </span>
                                <span className="ml-auto text-[10px] mono text-text-3 opacity-60">T:{event.tick_number}</span>
                              </div>
                              {event.title && <p className="text-[12px] font-medium text-text leading-relaxed mb-0.5">{event.title}</p>}
                              {event.description && <p className="text-[11px] text-text-2 leading-relaxed line-clamp-2">{event.description}</p>}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))}
                {hasMore && (
                  <button
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className="w-full py-3 rounded-xl bg-white/[0.02] border border-white/[0.04] text-text-3 text-[11px] font-medium active:bg-white/[0.05] flex items-center justify-center gap-2 touch-target"
                  >
                    {loadingMore ? <Loader2 size={12} className="animate-spin" /> : <ChevronDown size={12} />}
                    {t('load_more')}
                  </button>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
