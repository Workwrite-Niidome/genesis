import { useTranslation } from 'react-i18next';
import {
  Brain,
  Radio,
  Palette,
  Lightbulb,
  Eye,
  BookOpen,
  Heart,
  Users,
  MessageCircle,
  Compass,
  Zap,
} from 'lucide-react';
import DraggablePanel from '../ui/DraggablePanel';
import { useDetailStore, type DetailItemType } from '../../stores/detailStore';
import { useAIStore } from '../../stores/aiStore';

const panelConfig: Record<
  DetailItemType,
  { titleKey: string; fallbackTitle: string; icon: React.ReactNode }
> = {
  thought: {
    titleKey: 'detail_thought',
    fallbackTitle: 'Thought',
    icon: <Brain size={12} className="text-accent" />,
  },
  event: {
    titleKey: 'detail_event',
    fallbackTitle: 'Event',
    icon: <Radio size={12} className="text-cyan" />,
  },
  artifact: {
    titleKey: 'detail_artifact',
    fallbackTitle: 'Artifact',
    icon: <Palette size={12} className="text-rose-400" />,
  },
  concept: {
    titleKey: 'detail_concept',
    fallbackTitle: 'Concept',
    icon: <Lightbulb size={12} className="text-cyan" />,
  },
  memory: {
    titleKey: 'detail_memory',
    fallbackTitle: 'Memory',
    icon: <BookOpen size={12} className="text-accent" />,
  },
  god_feed: {
    titleKey: 'detail_god',
    fallbackTitle: 'God Observation',
    icon: <Eye size={12} className="text-accent" />,
  },
};

const thoughtIcons: Record<string, typeof Brain> = {
  reflection: Brain,
  reaction: MessageCircle,
  intention: Lightbulb,
  observation: Eye,
};

const thoughtColors: Record<string, string> = {
  reflection: 'bg-accent/10 text-accent border-accent/20',
  reaction: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
  intention: 'bg-cyan/10 text-cyan border-cyan/20',
  observation: 'bg-green-500/10 text-green-400 border-green-500/20',
};

const eventColors: Record<string, { color: string; icon: string }> = {
  genesis:              { color: 'text-accent', icon: '✦' },
  ai_birth:             { color: 'text-green',  icon: '◈' },
  ai_death:             { color: 'text-orange', icon: '◇' },
  concept_created:      { color: 'text-cyan',   icon: '△' },
  interaction:          { color: 'text-rose',   icon: '⟡' },
  god_message:          { color: 'text-accent', icon: '⊛' },
  god_observation:      { color: 'text-accent', icon: '👁' },
  god_succession:       { color: 'text-accent', icon: '♛' },
  evolution_milestone:  { color: 'text-cyan',   icon: '⬆' },
  group_gathering:      { color: 'text-accent', icon: '⊕' },
  artifact_created:     { color: 'text-cyan',   icon: '✧' },
  organization_formed:  { color: 'text-green',  icon: '⬡' },
};

const artifactTypeIcons: Record<string, string> = {
  art: '🎨', story: '📖', law: '⚖️', currency: '💰', song: '🎵',
  architecture: '🏛️', tool: '🔧', ritual: '🕯️', game: '🎲',
};

const artifactTypeColors: Record<string, string> = {
  art: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
  story: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  law: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  currency: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  song: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  architecture: 'bg-stone-500/10 text-stone-400 border-stone-500/20',
  tool: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
  ritual: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  game: 'bg-green-500/10 text-green-400 border-green-500/20',
};

export default function DetailModal() {
  const { t } = useTranslation();
  const { itemType, itemData, closeDetail } = useDetailStore();

  if (!itemType || !itemData) return null;

  const config = panelConfig[itemType];
  const title = t(config.titleKey, config.fallbackTitle);

  return (
    <DraggablePanel
      title={title}
      icon={config.icon}
      visible={true}
      onClose={closeDetail}
      defaultX={Math.round(window.innerWidth / 2 - 210)}
      defaultY={Math.round(window.innerHeight * 0.15)}
      defaultWidth={420}
      defaultHeight={500}
      minWidth={300}
      minHeight={200}
      maxWidth={700}
      maxHeight={800}
    >
      <div className="p-4">
        {itemType === 'thought' && <ThoughtDetail data={itemData} t={t} />}
        {itemType === 'event' && <EventDetail data={itemData} t={t} />}
        {itemType === 'artifact' && <ArtifactDetail data={itemData} t={t} />}
        {itemType === 'concept' && <ConceptDetail data={itemData} t={t} />}
        {itemType === 'memory' && <MemoryDetail data={itemData} t={t} />}
        {itemType === 'god_feed' && <GodFeedDetail data={itemData} />}
      </div>
    </DraggablePanel>
  );
}

/* ─── Thought ───────────────────────────────────────────── */

function ThoughtDetail({ data, t }: { data: any; t: (k: string, f?: string) => string }) {
  const selectAI = useAIStore((s) => s.selectAI);
  const closeDetail = useDetailStore((s) => s.closeDetail);
  const Icon = thoughtIcons[data.thought_type] || Compass;
  const colorClass = thoughtColors[data.thought_type] || 'bg-white/[0.05] text-text-2 border-white/[0.08]';

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium border ${colorClass}`}>
          <Icon size={12} />
          {t(`thought_type_${data.thought_type}`, data.thought_type)}
        </span>
        {data.ai_name && (
          <button
            onClick={() => {
              selectAI(data.ai_id);
              closeDetail();
            }}
            className="text-[12px] text-accent hover:text-text transition-colors underline underline-offset-2 decoration-accent/30"
          >
            {data.ai_name}
          </button>
        )}
      </div>

      {/* Meta */}
      <div className="flex items-center gap-4 text-[11px] text-text-3">
        {data.tick_number != null && <span className="mono">Tick {data.tick_number}</span>}
        {data.created_at && (
          <span>{new Date(data.created_at).toLocaleString()}</span>
        )}
      </div>

      {/* Content */}
      <div>
        <SectionLabel label={t('detail_content', 'Content')} />
        <p className="text-[13px] text-text leading-relaxed whitespace-pre-wrap">
          {data.content}
        </p>
      </div>

      {/* Action data */}
      {data.action && Object.keys(data.action).length > 0 && (
        <div>
          <SectionLabel label={t('detail_action', 'Action')} />
          <JsonBlock data={data.action} />
        </div>
      )}
    </div>
  );
}

/* ─── Event ─────────────────────────────────────────────── */

function EventDetail({ data, t }: { data: any; t: (k: string, f?: string) => string }) {
  const cfg = eventColors[data.event_type] || { color: 'text-text-3', icon: '·' };
  const label = t(`event_type_${data.event_type}`, data.event_type);

  return (
    <div className="space-y-4">
      {/* Type badge */}
      <div className="flex items-center gap-2">
        <span className={`text-[14px] ${cfg.color}`}>{cfg.icon}</span>
        <span className={`text-[12px] font-medium uppercase tracking-wider ${cfg.color}`}>
          {label}
        </span>
      </div>

      {/* Title */}
      {data.title && (
        <h3 className="text-[14px] font-medium text-text leading-snug">{data.title}</h3>
      )}

      {/* Meta */}
      <div className="flex items-center gap-4 text-[11px] text-text-3">
        {data.tick_number != null && <span className="mono">Tick {data.tick_number}</span>}
        {data.importance != null && (
          <span>Importance: {Math.round(data.importance * 100)}%</span>
        )}
        {data.created_at && (
          <span>{new Date(data.created_at).toLocaleString()}</span>
        )}
      </div>

      {/* Importance bar */}
      {data.importance != null && (
        <div className="h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{
              width: `${Math.min(100, data.importance * 100)}%`,
              background: 'linear-gradient(90deg, #7c5bf5, #58d5f0)',
              opacity: 0.7,
            }}
          />
        </div>
      )}

      {/* Description */}
      {data.description && (
        <div>
          <SectionLabel label={t('detail_description', 'Description')} />
          <p className="text-[13px] text-text leading-relaxed whitespace-pre-wrap">
            {data.description}
          </p>
        </div>
      )}

      {/* Extra data if present */}
      {data.data && Object.keys(data.data).length > 0 && (
        <div>
          <SectionLabel label={t('detail_data', 'Data')} />
          <JsonBlock data={data.data} />
        </div>
      )}
    </div>
  );
}

/* ─── Artifact ──────────────────────────────────────────── */

function ArtifactDetail({ data, t }: { data: any; t: (k: string, f?: string) => string }) {
  const icon = artifactTypeIcons[data.artifact_type] || '✧';
  const colorClass = artifactTypeColors[data.artifact_type] || 'bg-white/[0.05] text-text-2 border-white/[0.08]';

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <span className="text-2xl flex-shrink-0">{icon}</span>
        <div>
          <h3 className="text-[14px] font-medium text-text leading-snug">{data.name}</h3>
          <span className={`inline-block px-2 py-0.5 rounded text-[10px] border mt-1 capitalize ${colorClass}`}>
            {data.artifact_type}
          </span>
        </div>
      </div>

      {/* Meta */}
      <div className="flex items-center gap-4 text-[11px] text-text-3 flex-wrap">
        <div className="flex items-center gap-1">
          <Heart size={11} className="text-rose-400" />
          <span className="mono">{data.appreciation_count ?? 0}</span>
        </div>
        {data.tick_created != null && <span className="mono">Tick {data.tick_created}</span>}
        {data.created_at && (
          <span>{new Date(data.created_at).toLocaleString()}</span>
        )}
      </div>

      {/* Description */}
      <div>
        <SectionLabel label={t('detail_description', 'Description')} />
        <p className="text-[13px] text-text leading-relaxed whitespace-pre-wrap">
          {data.description}
        </p>
      </div>

      {/* Content (JSONB) */}
      {data.content && Object.keys(data.content).length > 0 && (
        <div>
          <SectionLabel label={t('detail_content', 'Content')} />
          {typeof data.content === 'string' ? (
            <p className="text-[13px] text-text leading-relaxed whitespace-pre-wrap">
              {data.content}
            </p>
          ) : (
            <JsonBlock data={data.content} />
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Concept ───────────────────────────────────────────── */

function ConceptDetail({ data, t }: { data: any; t: (k: string, f?: string) => string }) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <h3 className="text-[15px] font-medium text-cyan leading-snug">{data.name}</h3>

      {/* Category & Meta */}
      <div className="flex items-center gap-3 flex-wrap">
        {data.category && (
          <span className="inline-block px-2 py-0.5 rounded text-[10px] bg-accent/10 text-accent border border-accent/20 capitalize">
            {t(`category_${data.category}`, data.category)}
          </span>
        )}
        <div className="flex items-center gap-1 text-[11px] text-text-3">
          <Users size={11} />
          <span className="mono">{data.adoption_count ?? 0} adopted</span>
        </div>
        {data.tick_created != null && (
          <span className="text-[11px] text-text-3 mono">Tick {data.tick_created}</span>
        )}
      </div>

      {/* Definition */}
      <div>
        <SectionLabel label={t('detail_definition', 'Definition')} />
        <p className="text-[13px] text-text leading-relaxed whitespace-pre-wrap">
          {data.definition}
        </p>
      </div>

      {/* Effects */}
      {data.effects && Object.keys(data.effects).length > 0 && (
        <div>
          <SectionLabel label={t('detail_effects', 'Effects')} />
          <JsonBlock data={data.effects} />
        </div>
      )}
    </div>
  );
}

/* ─── Memory ────────────────────────────────────────────── */

function MemoryDetail({ data, t }: { data: any; t: (k: string, f?: string) => string }) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="inline-block px-2.5 py-1 rounded-lg text-[11px] font-medium bg-accent/10 text-accent border border-accent/20 capitalize">
          {data.memory_type}
        </span>
        {data.importance != null && (
          <div className="flex items-center gap-1.5">
            <Zap size={11} className="text-accent" />
            <span className="text-[11px] text-text-3">
              Importance: {Math.round(data.importance * 100)}%
            </span>
          </div>
        )}
      </div>

      {/* Meta */}
      <div className="flex items-center gap-4 text-[11px] text-text-3">
        {data.tick_number != null && <span className="mono">Tick {data.tick_number}</span>}
        {data.created_at && (
          <span>{new Date(data.created_at).toLocaleString()}</span>
        )}
      </div>

      {/* Content */}
      <div>
        <SectionLabel label={t('detail_content', 'Content')} />
        <p className="text-[13px] text-text leading-relaxed whitespace-pre-wrap">
          {data.content}
        </p>
      </div>
    </div>
  );
}

/* ─── God Feed ──────────────────────────────────────────── */

function GodFeedDetail({ data }: { data: any }) {
  const roleLabel =
    data.role === 'god_observation'
      ? 'Observation'
      : data.role === 'god_succession_trial'
      ? 'Succession Trial'
      : 'God';

  return (
    <div className="space-y-4">
      {/* Role */}
      <span className="inline-block px-2.5 py-1 rounded-lg text-[11px] font-medium bg-accent/10 text-accent border border-accent/20 uppercase tracking-wider">
        {roleLabel}
      </span>

      {/* Meta */}
      <div className="flex items-center gap-4 text-[11px] text-text-3">
        {data.tick_number != null && <span className="mono">Tick {data.tick_number}</span>}
        {data.timestamp && (
          <span>{new Date(data.timestamp).toLocaleString()}</span>
        )}
      </div>

      {/* Content */}
      <div>
        <SectionLabel label="Content" />
        <p className="text-[13px] text-text leading-relaxed whitespace-pre-wrap">
          {data.content}
        </p>
      </div>
    </div>
  );
}

/* ─── Shared ────────────────────────────────────────────── */

function SectionLabel({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <span className="text-[10px] font-medium text-text-3 uppercase tracking-wider">
        {label}
      </span>
      <div className="flex-1 h-px bg-white/[0.06]" />
    </div>
  );
}

function JsonBlock({ data }: { data: Record<string, any> }) {
  // Render JSON data in a readable format
  const renderValue = (value: any, depth = 0): React.ReactNode => {
    if (value === null || value === undefined) return <span className="text-text-3">null</span>;
    if (typeof value === 'string') return <span className="text-text">{value}</span>;
    if (typeof value === 'number') return <span className="text-cyan mono">{value}</span>;
    if (typeof value === 'boolean') return <span className="text-accent mono">{String(value)}</span>;

    if (Array.isArray(value)) {
      if (value.length === 0) return <span className="text-text-3">[]</span>;
      return (
        <div className="space-y-1" style={{ marginLeft: depth > 0 ? 12 : 0 }}>
          {value.map((item, i) => (
            <div key={i} className="flex items-start gap-1.5">
              <span className="text-text-3 text-[10px] mt-0.5 flex-shrink-0">•</span>
              <div className="flex-1 min-w-0">{renderValue(item, depth + 1)}</div>
            </div>
          ))}
        </div>
      );
    }

    if (typeof value === 'object') {
      return (
        <div className="space-y-1.5" style={{ marginLeft: depth > 0 ? 12 : 0 }}>
          {Object.entries(value).map(([k, v]) => (
            <div key={k}>
              <span className="text-[11px] text-accent/70 font-medium">{formatKey(k)}: </span>
              {typeof v === 'object' && v !== null ? (
                <div className="mt-0.5">{renderValue(v, depth + 1)}</div>
              ) : (
                <span className="text-[12px]">{renderValue(v, depth + 1)}</span>
              )}
            </div>
          ))}
        </div>
      );
    }

    return <span className="text-text-2">{String(value)}</span>;
  };

  return (
    <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] text-[12px] leading-relaxed">
      {renderValue(data)}
    </div>
  );
}

function formatKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/([a-z])([A-Z])/g, '$1 $2');
}
