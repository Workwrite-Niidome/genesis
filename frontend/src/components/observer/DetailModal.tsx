import { useEffect, useState } from 'react';
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
  Loader2,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import DraggablePanel from '../ui/DraggablePanel';
import { useDetailStore, type DetailItemType } from '../../stores/detailStore';
import { useAIStore } from '../../stores/aiStore';
import { api } from '../../services/api';
import type { AIEntity, Interaction } from '../../types/world';

/* ═══════════════════════════════════════════════════════════
   Configuration
   ═══════════════════════════════════════════════════════════ */

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
  interaction: {
    titleKey: 'detail_interaction',
    fallbackTitle: 'Interaction',
    icon: <MessageCircle size={12} className="text-rose-400" />,
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

const thoughtColorMap: Record<string, { badge: string; bg: string }> = {
  reflection: { badge: 'bg-accent/10 text-accent border-accent/20', bg: 'bg-accent/5 border-accent/10' },
  reaction: { badge: 'bg-rose-500/10 text-rose-400 border-rose-500/20', bg: 'bg-rose-500/5 border-rose-500/10' },
  intention: { badge: 'bg-cyan/10 text-cyan border-cyan/20', bg: 'bg-cyan/5 border-cyan/10' },
  observation: { badge: 'bg-green-500/10 text-green-400 border-green-500/20', bg: 'bg-green-500/5 border-green-500/10' },
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

/* ═══════════════════════════════════════════════════════════
   Main component
   ═══════════════════════════════════════════════════════════ */

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
      defaultX={Math.round(window.innerWidth / 2 - 240)}
      defaultY={Math.round(window.innerHeight * 0.1)}
      defaultWidth={480}
      defaultHeight={580}
      minWidth={340}
      minHeight={250}
      maxWidth={750}
      maxHeight={900}
    >
      <div className="p-4">
        {itemType === 'thought' && <ThoughtDetail data={itemData} t={t} />}
        {itemType === 'event' && <EventDetail data={itemData} t={t} />}
        {itemType === 'interaction' && <InteractionDetail data={itemData} t={t} />}
        {itemType === 'artifact' && <ArtifactDetail data={itemData} t={t} />}
        {itemType === 'concept' && <ConceptDetail data={itemData} t={t} />}
        {itemType === 'memory' && <MemoryDetail data={itemData} t={t} />}
        {itemType === 'god_feed' && <GodFeedDetail data={itemData} t={t} />}
      </div>
    </DraggablePanel>
  );
}

/* ═══════════════════════════════════════════════════════════
   Thought Detail — with AI profile & recent interactions
   ═══════════════════════════════════════════════════════════ */

function ThoughtDetail({ data, t }: { data: any; t: TFn }) {
  const selectAI = useAIStore((s) => s.selectAI);
  const closeDetail = useDetailStore((s) => s.closeDetail);
  const [aiEntity, setAiEntity] = useState<AIEntity | null>(null);
  const [recentInteractions, setRecentInteractions] = useState<Interaction[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!data.ai_id) return;
    setLoading(true);
    Promise.all([
      api.ais.get(data.ai_id).catch(() => null),
      api.interactions.getByAI(data.ai_id, 5).catch(() => []),
    ]).then(([ai, interactions]) => {
      setAiEntity(ai);
      setRecentInteractions(interactions || []);
      setLoading(false);
    });
  }, [data.ai_id]);

  const Icon = thoughtIcons[data.thought_type] || Compass;
  const colors = thoughtColorMap[data.thought_type] || { badge: 'bg-white/[0.05] text-text-2 border-white/[0.08]', bg: 'bg-white/[0.02] border-white/[0.04]' };

  return (
    <div className="space-y-4">
      {/* AI profile card */}
      {loading ? (
        <LoadingBlock />
      ) : aiEntity ? (
        <AIProfileCard
          ai={aiEntity}
          onClick={() => { selectAI(data.ai_id); closeDetail(); }}
        />
      ) : data.ai_name ? (
        <button
          onClick={() => { selectAI(data.ai_id); closeDetail(); }}
          className="text-[13px] text-accent hover:text-text transition-colors underline underline-offset-2"
        >
          {data.ai_name}
        </button>
      ) : null}

      {/* Thought type + meta */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium border ${colors.badge}`}>
          <Icon size={12} />
          {t(`thought_type_${data.thought_type}`, data.thought_type)}
        </span>
        <MetaInfo tick={data.tick_number} timestamp={data.created_at} />
      </div>

      {/* Full content */}
      <div>
        <SectionLabel label={t('detail_content', 'Content')} />
        <div className={`p-3.5 rounded-xl border ${colors.bg}`}>
          <p className="text-[13px] text-text leading-[1.7] whitespace-pre-wrap">
            {data.content}
          </p>
        </div>
      </div>

      {/* Action data */}
      {data.action && Object.keys(data.action).length > 0 && (
        <div>
          <SectionLabel label={t('detail_action', 'Action')} />
          <JsonBlock data={data.action} />
        </div>
      )}

      {/* Recent interactions of this AI */}
      {recentInteractions.length > 0 && (
        <div>
          <SectionLabel label={t('detail_recent_interactions', 'Recent Conversations')} />
          <div className="space-y-2">
            {recentInteractions.slice(0, 3).map((inter) => (
              <InteractionPreview key={inter.id} interaction={inter} t={t} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Event Detail — auto-fetches interaction if type=interaction
   ═══════════════════════════════════════════════════════════ */

function EventDetail({ data, t }: { data: any; t: TFn }) {
  const [interaction, setInteraction] = useState<Interaction | null>(null);
  const [loadingInteraction, setLoadingInteraction] = useState(false);

  // Fetch full interaction by ID from event metadata (works for both 1-on-1 and group)
  useEffect(() => {
    const rawId = data.metadata_?.interaction_id || data.data?.interaction_id;
    // Guard against "None" string from backend bug
    const interactionId = rawId && rawId !== 'None' && rawId !== 'null' ? rawId : null;
    const isInteractionEvent = data.event_type === 'interaction' || data.event_type === 'group_gathering';
    if (!isInteractionEvent) return;

    setLoadingInteraction(true);
    if (interactionId) {
      // Fetch by exact ID
      api.interactions.get(interactionId)
        .then((i) => setInteraction(i || null))
        .catch(() => setInteraction(null))
        .finally(() => setLoadingInteraction(false));
    } else {
      // Fallback: search by tick_number for events without valid interaction_id
      api.interactions.list(50).then((interactions) => {
        const matches = (interactions || []).filter(
          (i: Interaction) => i.tick_number === data.tick_number
        );
        // Try to match by event_type: group_gathering -> group_gathering, interaction -> dialogue
        const eventIsGroup = data.event_type === 'group_gathering';
        const bestMatch = matches.find((i: Interaction) =>
          eventIsGroup ? i.interaction_type === 'group_gathering' : i.interaction_type !== 'group_gathering'
        ) || matches[0];
        setInteraction(bestMatch || null);
        setLoadingInteraction(false);
      }).catch(() => setLoadingInteraction(false));
    }
  }, [data.event_type, data.tick_number, data.metadata_?.interaction_id, data.data?.interaction_id]);

  const cfg = eventColors[data.event_type] || { color: 'text-text-3', icon: '·' };
  const label = t(`event_type_${data.event_type}`, data.event_type);

  return (
    <div className="space-y-4">
      {/* Type badge */}
      <div className="flex items-center gap-2">
        <span className={`text-[16px] ${cfg.color}`}>{cfg.icon}</span>
        <span className={`text-[13px] font-semibold uppercase tracking-wider ${cfg.color}`}>
          {label}
        </span>
      </div>

      {/* Title */}
      {data.title && (
        <h3 className="text-[15px] font-medium text-text leading-snug">{data.title}</h3>
      )}

      {/* Meta */}
      <MetaInfo tick={data.tick_number} timestamp={data.created_at} importance={data.importance} />

      {/* Importance bar */}
      {data.importance != null && (
        <ImportanceBar importance={data.importance} />
      )}

      {/* Description */}
      {data.description && (
        <div>
          <SectionLabel label={t('detail_description', 'Description')} />
          <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
            <p className="text-[13px] text-text leading-[1.7] whitespace-pre-wrap">
              {data.description}
            </p>
          </div>
        </div>
      )}

      {/* Full interaction conversation (for interaction & group_gathering events) */}
      {(data.event_type === 'interaction' || data.event_type === 'group_gathering') && (
        loadingInteraction ? (
          <LoadingBlock />
        ) : interaction ? (
          <div>
            <SectionLabel label={t('detail_conversation', 'Full Conversation')} />
            <ConversationView interaction={interaction} t={t} />
          </div>
        ) : null
      )}

      {/* Extra data */}
      {data.data && Object.keys(data.data).length > 0 && (
        <div>
          <SectionLabel label={t('detail_data', 'Data')} />
          <JsonBlock data={data.data} />
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Interaction Detail — full AI conversation
   ═══════════════════════════════════════════════════════════ */

function InteractionDetail({ data, t }: { data: any; t: TFn }) {
  return (
    <div className="space-y-4">
      {/* Type */}
      <div className="flex items-center gap-2">
        <span className="text-[16px] text-rose-400">⟡</span>
        <span className="text-[13px] font-semibold text-rose-400 uppercase tracking-wider">
          {t(`interaction_type_${data.interaction_type}`, data.interaction_type)}
        </span>
      </div>

      {/* Meta */}
      <MetaInfo tick={data.tick_number} timestamp={data.created_at} />

      {/* Full conversation */}
      <ConversationView interaction={data} t={t} />

      {/* Concepts involved */}
      {data.concepts_involved && data.concepts_involved.length > 0 && (
        <div>
          <SectionLabel label={t('detail_concepts_involved', 'Concepts Involved')} />
          <div className="flex flex-wrap gap-1.5">
            {data.concepts_involved.map((id: string) => (
              <span key={id} className="px-2 py-0.5 rounded text-[10px] bg-cyan/10 text-cyan border border-cyan/20 mono">
                {id.slice(0, 8)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Artifact Detail — with creator AI profile
   ═══════════════════════════════════════════════════════════ */

function ArtifactDetail({ data, t }: { data: any; t: TFn }) {
  const [creator, setCreator] = useState<AIEntity | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!data.creator_id) return;
    setLoading(true);
    api.ais.get(data.creator_id).then(setCreator).catch(() => null).finally(() => setLoading(false));
  }, [data.creator_id]);

  const icon = artifactTypeIcons[data.artifact_type] || '✧';
  const colorClass = artifactTypeColors[data.artifact_type] || 'bg-white/[0.05] text-text-2 border-white/[0.08]';

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <span className="text-3xl flex-shrink-0">{icon}</span>
        <div>
          <h3 className="text-[16px] font-semibold text-text leading-snug">{data.name}</h3>
          <span className={`inline-block px-2.5 py-0.5 rounded text-[10px] border mt-1.5 capitalize ${colorClass}`}>
            {data.artifact_type}
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-5 text-[12px] text-text-3 flex-wrap">
        <div className="flex items-center gap-1.5">
          <Heart size={13} className="text-rose-400" />
          <span className="mono font-medium text-text-2">{data.appreciation_count ?? 0}</span>
          <span className="text-[10px]">appreciations</span>
        </div>
        <MetaInfo tick={data.tick_created} timestamp={data.created_at} />
      </div>

      {/* Creator AI */}
      {loading ? (
        <LoadingBlock />
      ) : creator ? (
        <div>
          <SectionLabel label={t('detail_creator', 'Creator')} />
          <AIProfileCard ai={creator} onClick={() => {
            useAIStore.getState().selectAI(creator.id);
            useDetailStore.getState().closeDetail();
          }} />
        </div>
      ) : null}

      {/* Description */}
      <div>
        <SectionLabel label={t('detail_description', 'Description')} />
        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
          <p className="text-[13px] text-text leading-[1.7] whitespace-pre-wrap">
            {data.description}
          </p>
        </div>
      </div>

      {/* Content (JSONB) */}
      {data.content && Object.keys(data.content).length > 0 && (
        <div>
          <SectionLabel label={t('detail_full_content', 'Full Content')} />
          {typeof data.content === 'string' ? (
            <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <p className="text-[13px] text-text leading-[1.7] whitespace-pre-wrap">{data.content}</p>
            </div>
          ) : (
            renderArtifactContent(data.artifact_type, data.content)
          )}
        </div>
      )}
    </div>
  );
}

/** Renders artifact content with type-aware formatting */
function renderArtifactContent(artifactType: string, content: Record<string, any>): React.ReactNode {
  // Stories and songs: show text field prominently
  if ((artifactType === 'story' || artifactType === 'song' || artifactType === 'art') && content.text) {
    return (
      <div className="space-y-3">
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.04]">
          <p className="text-[13px] text-text leading-[1.8] whitespace-pre-wrap font-[family-name:var(--font-saga)]">
            {content.text}
          </p>
        </div>
        {Object.keys(content).filter(k => k !== 'text').length > 0 && (
          <JsonBlock data={Object.fromEntries(Object.entries(content).filter(([k]) => k !== 'text'))} />
        )}
      </div>
    );
  }
  // Laws: show rules/provisions
  if (artifactType === 'law' && (content.rules || content.provisions || content.articles)) {
    const rules = content.rules || content.provisions || content.articles;
    return (
      <div className="space-y-2">
        {Array.isArray(rules) ? rules.map((rule: any, i: number) => (
          <div key={i} className="p-3 rounded-xl bg-blue-500/[0.03] border border-blue-500/10">
            <p className="text-[13px] text-text leading-[1.7]">
              <span className="text-blue-400 font-medium mr-2">§{i + 1}</span>
              {typeof rule === 'string' ? rule : rule.text || JSON.stringify(rule)}
            </p>
          </div>
        )) : (
          <JsonBlock data={{ rules }} />
        )}
        {Object.keys(content).filter(k => !['rules', 'provisions', 'articles'].includes(k)).length > 0 && (
          <JsonBlock data={Object.fromEntries(Object.entries(content).filter(([k]) => !['rules', 'provisions', 'articles'].includes(k)))} />
        )}
      </div>
    );
  }
  // Default: structured JSON
  return <JsonBlock data={content} />;
}

/* ═══════════════════════════════════════════════════════════
   Concept Detail — with creator AI profile
   ═══════════════════════════════════════════════════════════ */

function ConceptDetail({ data, t }: { data: any; t: TFn }) {
  const [creator, setCreator] = useState<AIEntity | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!data.creator_id) return;
    setLoading(true);
    api.ais.get(data.creator_id).then(setCreator).catch(() => null).finally(() => setLoading(false));
  }, [data.creator_id]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <h3 className="text-[16px] font-semibold text-cyan leading-snug">{data.name}</h3>

      {/* Category & stats */}
      <div className="flex items-center gap-3 flex-wrap">
        {data.category && (
          <span className="inline-block px-2.5 py-0.5 rounded text-[11px] bg-accent/10 text-accent border border-accent/20 capitalize font-medium">
            {t(`category_${data.category}`, data.category)}
          </span>
        )}
        <div className="flex items-center gap-1.5 text-[12px] text-text-3">
          <Users size={12} />
          <span className="mono font-medium text-text-2">{data.adoption_count ?? 0}</span>
          <span className="text-[10px]">adopted</span>
        </div>
        <MetaInfo tick={data.tick_created} timestamp={data.created_at} />
      </div>

      {/* Creator AI */}
      {loading ? (
        <LoadingBlock />
      ) : creator ? (
        <div>
          <SectionLabel label={t('detail_creator', 'Creator')} />
          <AIProfileCard ai={creator} onClick={() => {
            useAIStore.getState().selectAI(creator.id);
            useDetailStore.getState().closeDetail();
          }} />
        </div>
      ) : null}

      {/* Definition */}
      <div>
        <SectionLabel label={t('detail_definition', 'Definition')} />
        <div className="p-3.5 rounded-xl bg-cyan/[0.03] border border-cyan/10">
          <p className="text-[13px] text-text leading-[1.7] whitespace-pre-wrap">
            {data.definition}
          </p>
        </div>
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

/* ═══════════════════════════════════════════════════════════
   Memory Detail — with importance visualization
   ═══════════════════════════════════════════════════════════ */

function MemoryDetail({ data, t }: { data: any; t: TFn }) {
  const importance = data.importance ?? 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="inline-block px-2.5 py-1 rounded-lg text-[11px] font-medium bg-accent/10 text-accent border border-accent/20 capitalize">
          {data.memory_type}
        </span>
        <MetaInfo tick={data.tick_number} timestamp={data.created_at} />
      </div>

      {/* Importance meter */}
      <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5">
            <Zap size={12} className="text-accent" />
            <span className="text-[11px] font-medium text-text-3 uppercase tracking-wider">
              {t('importance', 'Importance')}
            </span>
          </div>
          <span className="text-[13px] mono font-medium text-accent">{Math.round(importance * 100)}%</span>
        </div>
        <div className="h-2 bg-white/[0.04] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.min(100, importance * 100)}%`,
              background: `linear-gradient(90deg, #7c5bf5, ${importance > 0.7 ? '#f472b6' : '#58d5f0'})`,
              boxShadow: `0 0 8px ${importance > 0.7 ? '#f472b680' : '#7c5bf540'}`,
            }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[9px] text-text-3">Trivial</span>
          <span className="text-[9px] text-text-3">Critical</span>
        </div>
      </div>

      {/* Full content */}
      <div>
        <SectionLabel label={t('detail_content', 'Content')} />
        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
          <p className="text-[13px] text-text leading-[1.7] whitespace-pre-wrap">
            {data.content}
          </p>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   God Feed Detail
   ═══════════════════════════════════════════════════════════ */

function GodFeedDetail({ data, t }: { data: any; t: TFn }) {
  const roleLabel =
    data.role === 'god_observation'
      ? t('detail_god_observation', 'Divine Observation')
      : data.role === 'god_succession_trial'
      ? t('detail_god_succession', 'Succession Trial')
      : t('detail_god_word', 'Word of God');

  return (
    <div className="space-y-4">
      {/* Role */}
      <div className="flex items-center gap-2">
        <Eye size={16} className="text-accent" />
        <span className="text-[13px] font-semibold text-accent uppercase tracking-wider">
          {roleLabel}
        </span>
      </div>

      {/* Meta */}
      <MetaInfo tick={data.tick_number} timestamp={data.timestamp} />

      {/* Content */}
      <div>
        <SectionLabel label={t('detail_content', 'Content')} />
        <div className="p-4 rounded-xl bg-accent/[0.03] border border-accent/10">
          <p className="text-[13px] text-text leading-[1.8] whitespace-pre-wrap">
            {data.content}
          </p>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Shared Components
   ═══════════════════════════════════════════════════════════ */

type TFn = (k: string, f?: string) => string;

/** AI profile mini card */
function AIProfileCard({ ai, onClick }: { ai: AIEntity; onClick?: () => void }) {
  const color = ai.appearance?.primaryColor || '#7c5bf5';
  const traits = ai.personality_traits || [];
  const energy = typeof ai.state?.energy === 'number' ? ai.state.energy : null;
  const evoScore = typeof ai.state?.evolution_score === 'number' ? ai.state.evolution_score : null;

  return (
    <button
      onClick={onClick}
      className="w-full text-left flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-colors cursor-pointer"
    >
      <div
        className="w-10 h-10 rounded-full flex-shrink-0"
        style={{
          backgroundColor: color,
          boxShadow: `0 0 16px ${color}40`,
        }}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-medium text-text truncate">{ai.name}</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded ${ai.is_alive ? 'bg-green-dim text-green' : 'bg-orange-dim text-orange'}`}>
            {ai.is_alive ? 'Alive' : 'Dead'}
          </span>
        </div>
        <div className="flex items-center gap-1.5 mt-1 flex-wrap">
          {traits.slice(0, 4).map((trait) => (
            <span key={trait} className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-dim text-cyan capitalize">
              {trait}
            </span>
          ))}
        </div>
        {(energy !== null || evoScore !== null) && (
          <div className="flex items-center gap-3 mt-1.5">
            {energy !== null && (
              <div className="flex items-center gap-1">
                <Zap size={9} className="text-cyan" />
                <span className="text-[10px] mono text-text-3">{Math.round(energy * 100)}%</span>
              </div>
            )}
            {evoScore !== null && (
              <div className="flex items-center gap-1">
                <Sparkles size={9} className="text-accent" />
                <span className="text-[10px] mono text-text-3">{evoScore.toFixed(1)}</span>
              </div>
            )}
          </div>
        )}
      </div>
      <ArrowRight size={14} className="text-text-3 opacity-40 flex-shrink-0" />
    </button>
  );
}

/** Full conversation view for an Interaction — handles both 1-on-1 and group gathering formats */
function ConversationView({ interaction, t }: { interaction: Interaction; t: TFn }) {
  const content = interaction.content;
  const isGroup = interaction.interaction_type === 'group_gathering';

  if (isGroup) {
    return <GroupConversationView content={content} interaction={interaction} t={t} />;
  }

  return <PairConversationView content={content} interaction={interaction} t={t} />;
}

/** 1-on-1 conversation view */
function PairConversationView({
  content,
  interaction,
  t,
}: {
  content: Interaction['content'];
  interaction: Interaction;
  t: TFn;
}) {
  const ai1 = content.ai1;
  const ai2 = content.ai2;
  const [ai1Entity, setAi1Entity] = useState<AIEntity | null>(null);
  const [ai2Entity, setAi2Entity] = useState<AIEntity | null>(null);

  useEffect(() => {
    if (ai1?.id) api.ais.get(ai1.id).then(setAi1Entity).catch(() => null);
    if (ai2?.id) api.ais.get(ai2.id).then(setAi2Entity).catch(() => null);
  }, [ai1?.id, ai2?.id]);

  const ai1Color = ai1Entity?.appearance?.primaryColor || '#7c5bf5';
  const ai2Color = ai2Entity?.appearance?.primaryColor || '#58d5f0';
  const ai1Name = ai1?.name || ai1Entity?.name || '???';
  const ai2Name = ai2?.name || ai2Entity?.name || '???';

  return (
    <div className="space-y-4">
      {/* Interaction type badge */}
      <div className="flex items-center gap-2">
        <MessageCircle size={12} className="text-rose-400" />
        <span className="text-[11px] font-medium text-rose-400 uppercase tracking-wider">
          {t(`interaction_type_${interaction.interaction_type}`, interaction.interaction_type)}
        </span>
        <span className="text-[10px] mono text-text-3 ml-auto">Tick {interaction.tick_number}</span>
      </div>

      {/* AI 1 turn */}
      <ConversationTurn
        name={ai1Name}
        color={ai1Color}
        thought={ai1?.thought}
        message={ai1?.message}
        action={ai1?.action}
        side="left"
        t={t}
      />

      {/* Divider */}
      <div className="flex items-center gap-2 px-2">
        <div className="flex-1 h-px bg-white/[0.06]" />
        <ArrowRight size={12} className="text-text-3 opacity-30 rotate-90" />
        <div className="flex-1 h-px bg-white/[0.06]" />
      </div>

      {/* AI 2 turn */}
      <ConversationTurn
        name={ai2Name}
        color={ai2Color}
        thought={ai2?.thought}
        message={ai2?.message}
        action={ai2?.action}
        side="right"
        t={t}
      />
    </div>
  );
}

/** Group gathering conversation view */
function GroupConversationView({
  content,
  interaction,
  t,
}: {
  content: Interaction['content'];
  interaction: Interaction;
  t: TFn;
}) {
  const speaker = content.speaker;
  const speech = content.speech || '';
  const thought = content.thought || '';
  const participants = content.participants || [];
  const speakerName = speaker?.name || '???';

  return (
    <div className="space-y-4">
      {/* Type badge */}
      <div className="flex items-center gap-2">
        <Users size={12} className="text-accent" />
        <span className="text-[11px] font-medium text-accent uppercase tracking-wider">
          {t('interaction_type_group_gathering', 'Group Gathering')}
        </span>
        <span className="text-[10px] mono text-text-3 ml-auto">Tick {interaction.tick_number}</span>
      </div>

      {/* Participants */}
      <div>
        <SectionLabel label={t('detail_participants', 'Participants')} />
        <div className="flex flex-wrap gap-1.5">
          {participants.map((p) => (
            <span
              key={p.id}
              className={`px-2 py-0.5 rounded text-[11px] border ${
                p.id === speaker?.id
                  ? 'bg-accent/10 text-accent border-accent/20 font-medium'
                  : 'bg-white/[0.04] text-text-2 border-white/[0.08]'
              }`}
            >
              {p.name}{p.id === speaker?.id ? ` (${t('detail_speaker', 'Speaker')})` : ''}
            </span>
          ))}
        </div>
      </div>

      {/* Speaker's thought */}
      {thought && (
        <div>
          <div className="flex items-center gap-1 mb-1">
            <Brain size={10} className="text-accent/60" />
            <span className="text-[9px] text-accent/60 uppercase tracking-wider font-medium">
              {speakerName} — {t('detail_inner_thought', 'Inner Thought')}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-accent/[0.04] border border-accent/10">
            <p className="text-[12px] text-text-2 leading-[1.7] whitespace-pre-wrap italic">
              {thought}
            </p>
          </div>
        </div>
      )}

      {/* Speaker's speech */}
      {speech && (
        <div>
          <div className="flex items-center gap-1 mb-1">
            <MessageCircle size={10} className="text-text-3" />
            <span className="text-[9px] text-text-3 uppercase tracking-wider font-medium">
              {speakerName} — {t('detail_spoken', 'Spoken')}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-accent/[0.06] border border-accent/15">
            <p className="text-[13px] text-text leading-[1.7] whitespace-pre-wrap">
              {speech}
            </p>
          </div>
        </div>
      )}

      {/* Artifact proposal */}
      {content.artifact && typeof content.artifact === 'object' && content.artifact.name && (
        <div>
          <SectionLabel label={t('detail_artifact_proposal', 'Artifact Proposed')} />
          <div className="p-3 rounded-xl bg-rose-500/[0.04] border border-rose-500/10">
            <p className="text-[13px] text-text font-medium">{content.artifact.name}</p>
            {content.artifact.description && (
              <p className="text-[12px] text-text-2 mt-1">{content.artifact.description}</p>
            )}
          </div>
        </div>
      )}

      {/* Organization proposal */}
      {content.organization && typeof content.organization === 'object' && content.organization.name && (
        <div>
          <SectionLabel label={t('detail_org_proposal', 'Organization Proposed')} />
          <div className="p-3 rounded-xl bg-green-500/[0.04] border border-green-500/10">
            <p className="text-[13px] text-text font-medium">{content.organization.name}</p>
            {content.organization.purpose && (
              <p className="text-[12px] text-text-2 mt-1">{content.organization.purpose}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** Single AI's turn in a conversation */
function ConversationTurn({
  name,
  color,
  thought,
  message,
  action,
  side,
  t,
}: {
  name: string;
  color: string;
  thought?: string;
  message?: string;
  action?: Record<string, any>;
  side: 'left' | 'right';
  t: TFn;
}) {
  return (
    <div className="space-y-2">
      {/* AI identity */}
      <div className={`flex items-center gap-2 ${side === 'right' ? 'flex-row-reverse' : ''}`}>
        <div
          className="w-6 h-6 rounded-full flex-shrink-0"
          style={{ backgroundColor: color, boxShadow: `0 0 10px ${color}40` }}
        />
        <span className="text-[12px] font-medium text-text">{name}</span>
      </div>

      {/* Thought bubble */}
      {thought && (
        <div className={`${side === 'right' ? 'ml-4' : 'ml-8'}`}>
          <div className="flex items-center gap-1 mb-1">
            <Brain size={10} className="text-accent/60" />
            <span className="text-[9px] text-accent/60 uppercase tracking-wider font-medium">
              {t('detail_inner_thought', 'Inner Thought')}
            </span>
          </div>
          <div
            className="p-3 rounded-xl border"
            style={{
              backgroundColor: `${color}08`,
              borderColor: `${color}15`,
            }}
          >
            <p className="text-[12px] text-text-2 leading-[1.7] whitespace-pre-wrap italic">
              {thought}
            </p>
          </div>
        </div>
      )}

      {/* Spoken message */}
      {message && (
        <div className={`${side === 'right' ? 'ml-4' : 'ml-8'}`}>
          <div className="flex items-center gap-1 mb-1">
            <MessageCircle size={10} className="text-text-3" />
            <span className="text-[9px] text-text-3 uppercase tracking-wider font-medium">
              {t('detail_spoken', 'Spoken')}
            </span>
          </div>
          <div
            className="p-3 rounded-xl border"
            style={{
              backgroundColor: `${color}0c`,
              borderColor: `${color}20`,
            }}
          >
            <p className="text-[13px] text-text leading-[1.7] whitespace-pre-wrap">
              {message}
            </p>
          </div>
        </div>
      )}

      {/* Action data */}
      {action && Object.keys(action).length > 0 && (
        <div className={`${side === 'right' ? 'ml-4' : 'ml-8'}`}>
          <div className="flex items-center gap-1 mb-1">
            <Zap size={10} className="text-text-3" />
            <span className="text-[9px] text-text-3 uppercase tracking-wider font-medium">
              {t('detail_action', 'Action')}
            </span>
          </div>
          <JsonBlock data={action} />
        </div>
      )}
    </div>
  );
}

/** Compact interaction preview for thought context */
function InteractionPreview({ interaction, t }: { interaction: Interaction; t: TFn }) {
  const openDetail = useDetailStore((s) => s.openDetail);
  const content = interaction.content;
  const isGroup = interaction.interaction_type === 'group_gathering';

  return (
    <button
      onClick={() => openDetail('interaction', interaction)}
      className="w-full text-left p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-colors cursor-pointer"
    >
      <div className="flex items-center gap-2 mb-2">
        {isGroup ? (
          <Users size={10} className="text-accent" />
        ) : (
          <MessageCircle size={10} className="text-rose-400" />
        )}
        <span className={`text-[10px] font-medium uppercase tracking-wider ${isGroup ? 'text-accent' : 'text-rose-400'}`}>
          {t(`interaction_type_${interaction.interaction_type}`, interaction.interaction_type)}
        </span>
        <span className="text-[9px] mono text-text-3 ml-auto">T:{interaction.tick_number}</span>
      </div>
      <div className="space-y-1.5">
        {isGroup ? (
          content.speech && (
            <div className="flex items-start gap-2">
              <span className="text-[10px] font-medium text-accent flex-shrink-0 mt-0.5 w-16 truncate">
                {content.speaker?.name || '???'}:
              </span>
              <p className="text-[11px] text-text-2 leading-relaxed line-clamp-2">{content.speech}</p>
            </div>
          )
        ) : (
          <>
            {content.ai1?.message && (
              <div className="flex items-start gap-2">
                <span className="text-[10px] font-medium text-accent flex-shrink-0 mt-0.5 w-16 truncate">
                  {content.ai1.name}:
                </span>
                <p className="text-[11px] text-text-2 leading-relaxed line-clamp-2">{content.ai1.message}</p>
              </div>
            )}
            {content.ai2?.message && (
              <div className="flex items-start gap-2">
                <span className="text-[10px] font-medium text-cyan flex-shrink-0 mt-0.5 w-16 truncate">
                  {content.ai2.name}:
                </span>
                <p className="text-[11px] text-text-2 leading-relaxed line-clamp-2">{content.ai2.message}</p>
              </div>
            )}
          </>
        )}
      </div>
    </button>
  );
}

function MetaInfo({ tick, timestamp, importance }: { tick?: number; timestamp?: string; importance?: number }) {
  return (
    <div className="flex items-center gap-3 text-[11px] text-text-3 flex-wrap">
      {tick != null && <span className="mono">Tick {tick}</span>}
      {importance != null && <span>Importance {Math.round(importance * 100)}%</span>}
      {timestamp && <span>{new Date(timestamp).toLocaleString()}</span>}
    </div>
  );
}

function ImportanceBar({ importance }: { importance: number }) {
  return (
    <div className="h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all"
        style={{
          width: `${Math.min(100, importance * 100)}%`,
          background: 'linear-gradient(90deg, #7c5bf5, #58d5f0)',
          opacity: 0.7,
        }}
      />
    </div>
  );
}

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

function LoadingBlock() {
  return (
    <div className="flex items-center justify-center py-4">
      <Loader2 size={16} className="text-text-3 animate-spin" />
    </div>
  );
}

function JsonBlock({ data }: { data: Record<string, any> }) {
  const renderValue = (value: any, depth = 0): React.ReactNode => {
    if (value === null || value === undefined) return <span className="text-text-3 italic">null</span>;
    if (typeof value === 'string') return <span className="text-text">{value}</span>;
    if (typeof value === 'number') return <span className="text-cyan mono">{value}</span>;
    if (typeof value === 'boolean') return <span className="text-accent mono">{String(value)}</span>;

    if (Array.isArray(value)) {
      if (value.length === 0) return <span className="text-text-3 italic">empty</span>;
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
