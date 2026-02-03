import { useEffect, useState } from 'react';
import {
  Brain,
  MessageCircle,
  Lightbulb,
  Eye,
  Heart,
  Users,
  Compass,
  Zap,
  Building2,
  ChevronRight,
} from 'lucide-react';
import { useDetailStore } from '../../../stores/detailStore';
import { useAIStore } from '../../../stores/aiStore';
import { api } from '../../../services/api';
import type { AIEntity, Interaction } from '../../../types/world';
import PixelArt from '../../media/PixelArt';
import ChiptunePlayer from '../../media/ChiptunePlayer';
import CodeSandbox from '../../media/CodeSandbox';
import VoxelViewer from '../../media/VoxelViewer';
import {
  type TFn,
  AIProfileCard,
  ConversationView,
  InteractionPreview,
  MetaInfo,
  ImportanceBar,
  SectionLabel,
  LoadingBlock,
  JsonBlock,
} from './DetailShared';

/* ═══════════════════════════════════════════════════════════
   Configuration
   ═══════════════════════════════════════════════════════════ */

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
   Thought Detail — with AI profile & recent interactions
   ═══════════════════════════════════════════════════════════ */

export function ThoughtDetail({ data, t }: { data: any; t: TFn }) {
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

export function EventDetail({ data, t }: { data: any; t: TFn }) {
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

export function InteractionDetail({ data, t }: { data: any; t: TFn }) {
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

export function ArtifactDetail({ data, t }: { data: any; t: TFn }) {
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
            renderArtifactContent(data.artifact_type, data.content, data)
          )}
        </div>
      )}
    </div>
  );
}

/** Renders artifact content with type-aware formatting */
function renderArtifactContent(artifactType: string, content: Record<string, any>, artifact?: any): React.ReactNode {
  // Pixel art: render canvas
  if (artifactType === 'art' && (content.pixels || artifact?.id)) {
    return (
      <div className="space-y-3">
        <div className="flex justify-center p-4 rounded-xl bg-black/40 border border-white/[0.06]">
          <PixelArt artifact={{ id: artifact?.id || 'unknown', content }} size={256} />
        </div>
        {content.palette && (
          <div className="flex items-center gap-1 px-1">
            <span className="text-[10px] text-text-3 mr-1">Palette:</span>
            {content.palette.map((color: string, i: number) => (
              <div
                key={i}
                className="w-4 h-4 rounded border border-white/10"
                style={{ backgroundColor: color }}
                title={color}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // Song: render chiptune player
  if (artifactType === 'song' && (content.notes || artifact?.id)) {
    return (
      <ChiptunePlayer artifact={{ id: artifact?.id || 'unknown', content }} />
    );
  }

  // Code / tool: render sandbox
  if ((artifactType === 'code' || artifactType === 'tool') && (content.source || content.language)) {
    return (
      <div className="space-y-3">
        <CodeSandbox artifact={{ id: artifact?.id || 'unknown', content }} />
      </div>
    );
  }

  // Architecture: render isometric voxel view
  if (artifactType === 'architecture' && (content.voxels || artifact?.id)) {
    return (
      <div className="space-y-3">
        <div className="flex justify-center p-4 rounded-xl bg-black/40 border border-white/[0.06]">
          <VoxelViewer artifact={{ id: artifact?.id || 'unknown', content }} size={280} />
        </div>
        {content.palette && (
          <div className="flex items-center gap-1 px-1">
            <span className="text-[10px] text-text-3 mr-1">Palette:</span>
            {content.palette.map((color: string, i: number) => (
              <div
                key={i}
                className="w-4 h-4 rounded border border-white/10"
                style={{ backgroundColor: color }}
                title={color}
              />
            ))}
          </div>
        )}
        {content.height && (
          <div className="text-[10px] text-text-3 px-1">
            Height: {content.height} · Voxels: {Array.isArray(content.voxels) ? content.voxels.length : '?'}
          </div>
        )}
      </div>
    );
  }

  // Stories: show text field prominently
  if ((artifactType === 'story') && content.text) {
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
              <span className="text-blue-400 font-medium mr-2">{i + 1}</span>
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

  // Currency: show symbol, denominations, rules
  if (artifactType === 'currency' && (content.symbol || content.denomination)) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-4 p-4 rounded-xl bg-yellow-500/[0.04] border border-yellow-500/10">
          {content.visual?.color && (
            <div
              className="w-14 h-14 rounded-xl flex items-center justify-center text-2xl font-bold border border-white/10 flex-shrink-0"
              style={{ backgroundColor: content.visual.color + '20', color: content.visual.color }}
            >
              {content.symbol || '¤'}
            </div>
          )}
          <div>
            <p className="text-[15px] font-semibold text-yellow-400">{content.denomination || 'Unknown'}</p>
            {content.backing && (
              <p className="text-[11px] text-text-3 mt-1">{content.backing}</p>
            )}
          </div>
        </div>
        {Array.isArray(content.denominations) && content.denominations.length > 0 && (
          <div>
            <span className="text-[10px] text-text-3 uppercase tracking-wider font-medium">Denominations</span>
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {content.denominations.map((d: string, i: number) => (
                <span key={i} className="px-2.5 py-1 rounded-lg text-[11px] bg-yellow-500/[0.06] text-yellow-300 border border-yellow-500/15">
                  {d}
                </span>
              ))}
            </div>
          </div>
        )}
        {Array.isArray(content.rules) && content.rules.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[10px] text-text-3 uppercase tracking-wider font-medium">Rules</span>
            {content.rules.map((rule: string, i: number) => (
              <div key={i} className="p-2.5 rounded-lg bg-yellow-500/[0.03] border border-yellow-500/8">
                <p className="text-[12px] text-text leading-[1.6]">
                  <span className="text-yellow-400 font-medium mr-2">{i + 1}</span>
                  {rule}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Ritual: show steps, purpose, effects
  if (artifactType === 'ritual' && Array.isArray(content.steps)) {
    return (
      <div className="space-y-3">
        {content.purpose && (
          <div className="p-3.5 rounded-xl bg-orange-500/[0.04] border border-orange-500/10">
            <span className="text-[10px] text-orange-400 uppercase tracking-wider font-medium">Purpose</span>
            <p className="text-[13px] text-text leading-[1.7] mt-1">{content.purpose}</p>
          </div>
        )}
        <div className="space-y-2">
          <span className="text-[10px] text-text-3 uppercase tracking-wider font-medium">Steps</span>
          {content.steps.map((step: string, i: number) => (
            <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg bg-orange-500/[0.03] border border-orange-500/8">
              <div className="w-6 h-6 rounded-full bg-orange-500/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-[11px] font-bold text-orange-400">{i + 1}</span>
              </div>
              <p className="text-[12px] text-text leading-[1.7]">{step}</p>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-4 text-[11px] text-text-3">
          {content.frequency && <span>🔄 {content.frequency}</span>}
          {content.participants && <span>👥 {content.participants}</span>}
          {content.effects && <span>✨ {content.effects}</span>}
        </div>
      </div>
    );
  }

  // Game: show objective, rules, components
  if (artifactType === 'game' && (content.rules || content.objective)) {
    return (
      <div className="space-y-3">
        <div className="p-3.5 rounded-xl bg-green-500/[0.04] border border-green-500/10">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-green-400 uppercase tracking-wider font-medium">Objective</span>
            {content.players && (
              <span className="text-[10px] text-text-3">👥 {content.players} players</span>
            )}
          </div>
          <p className="text-[13px] text-text leading-[1.7]">{content.objective || 'Be the last one standing.'}</p>
        </div>
        {Array.isArray(content.rules) && content.rules.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[10px] text-text-3 uppercase tracking-wider font-medium">Rules</span>
            {content.rules.map((rule: string, i: number) => (
              <div key={i} className="p-2.5 rounded-lg bg-green-500/[0.03] border border-green-500/8">
                <p className="text-[12px] text-text leading-[1.6]">
                  <span className="text-green-400 font-medium mr-2">{i + 1}</span>
                  {rule}
                </p>
              </div>
            ))}
          </div>
        )}
        {Array.isArray(content.components) && content.components.length > 0 && (
          <div>
            <span className="text-[10px] text-text-3 uppercase tracking-wider font-medium">Components</span>
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {content.components.map((c: string, i: number) => (
                <span key={i} className="px-2.5 py-1 rounded-lg text-[11px] bg-green-500/[0.06] text-green-300 border border-green-500/15">
                  {c}
                </span>
              ))}
            </div>
          </div>
        )}
        {content.theme && (
          <p className="text-[11px] text-text-3 italic">Theme: {content.theme}</p>
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

export function ConceptDetail({ data, t }: { data: any; t: TFn }) {
  if (data.category === 'organization') {
    return <OrganizationConceptDetail data={data} t={t} />;
  }
  return <GenericConceptDetail data={data} t={t} />;
}

function GenericConceptDetail({ data, t }: { data: any; t: TFn }) {
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

/** Organization-specific concept detail with member roster */
function OrganizationConceptDetail({ data, t }: { data: any; t: TFn }) {
  const [creator, setCreator] = useState<AIEntity | null>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [membersLoading, setMembersLoading] = useState(false);

  useEffect(() => {
    if (!data.creator_id) return;
    setLoading(true);
    api.ais.get(data.creator_id).then(setCreator).catch(() => null).finally(() => setLoading(false));
  }, [data.creator_id]);

  useEffect(() => {
    if (!data.id) return;
    setMembersLoading(true);
    api.concepts.getMembers(data.id).then(setMembers).catch(() => setMembers([])).finally(() => setMembersLoading(false));
  }, [data.id]);

  // Strip "Organization: " prefix from definition to show as purpose
  const purpose = (data.definition || '').replace(/^Organization:\s*/i, '');
  const focusArea = data.effects?.purpose_category;
  const aliveCount = members.filter((m) => m.is_alive).length;
  const deadCount = members.filter((m) => !m.is_alive).length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2.5">
        <Building2 size={18} className="text-green-400 flex-shrink-0" />
        <h3 className="text-[16px] font-semibold text-green-400 leading-snug">{data.name}</h3>
      </div>

      {/* Category badge + focus area */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="inline-block px-2.5 py-0.5 rounded text-[11px] bg-green-500/10 text-green-400 border border-green-500/20 capitalize font-medium">
          {t('category_organization', 'Organization')}
        </span>
        {focusArea && (
          <span className="inline-block px-2.5 py-0.5 rounded text-[11px] bg-cyan/10 text-cyan border border-cyan/20 capitalize font-medium">
            {t('org_focus_area', 'Focus Area')}: {t(`category_${focusArea}`, focusArea)}
          </span>
        )}
        <MetaInfo tick={data.tick_created} timestamp={data.created_at} />
      </div>

      {/* Purpose */}
      {purpose && (
        <div>
          <SectionLabel label={t('org_purpose', 'Purpose')} />
          <div className="p-3.5 rounded-xl bg-green-500/[0.04] border border-green-500/10">
            <p className="text-[13px] text-text leading-[1.7] whitespace-pre-wrap">
              {purpose}
            </p>
          </div>
        </div>
      )}

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

      {/* Member roster */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-medium text-text-3 uppercase tracking-wider">
              {t('org_members', 'Members')}
            </span>
            <div className="flex-1 h-px bg-white/[0.06]" />
          </div>
          {members.length > 0 && (
            <div className="flex items-center gap-2 text-[10px] text-text-3 ml-2 flex-shrink-0">
              <span className="text-green-400 mono">{aliveCount} {t('alive')}</span>
              {deadCount > 0 && <span className="text-orange mono">{deadCount} {t('dead')}</span>}
            </div>
          )}
        </div>
        {membersLoading ? (
          <LoadingBlock />
        ) : members.length === 0 ? (
          <p className="text-[11px] text-text-3 italic py-2">{t('org_no_members', 'No members')}</p>
        ) : (
          <div className="space-y-1.5">
            {/* Sort: founders first, then alive before dead */}
            {[...members]
              .sort((a, b) => {
                if (a.role === 'founder' && b.role !== 'founder') return -1;
                if (a.role !== 'founder' && b.role === 'founder') return 1;
                if (a.is_alive && !b.is_alive) return -1;
                if (!a.is_alive && b.is_alive) return 1;
                return 0;
              })
              .map((member) => {
                const memberColor = member.appearance?.primaryColor || '#7c5bf5';
                const isFounder = member.role === 'founder';
                return (
                  <button
                    key={member.id}
                    onClick={() => {
                      useAIStore.getState().selectAI(member.id);
                      useDetailStore.getState().closeDetail();
                    }}
                    className="w-full text-left flex items-center gap-2.5 p-2 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-colors cursor-pointer"
                  >
                    <div
                      className="w-7 h-7 rounded-full flex-shrink-0"
                      style={{
                        backgroundColor: memberColor,
                        boxShadow: `0 0 10px ${memberColor}30`,
                        opacity: member.is_alive ? 1 : 0.5,
                      }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[12px] font-medium text-text truncate">{member.name}</span>
                        <span className={`text-[8px] px-1.5 py-0.5 rounded ${member.is_alive ? 'bg-green-dim text-green' : 'bg-orange-dim text-orange'}`}>
                          {member.is_alive ? t('alive') : t('dead')}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`text-[9px] font-medium capitalize ${isFounder ? 'text-green-400' : 'text-text-3'}`}>
                          {isFounder ? t('org_founder', 'Founder') : t('org_member', 'Member')}
                        </span>
                        {member.personality_traits?.slice(0, 3).map((trait: string) => (
                          <span key={trait} className="text-[8px] px-1 py-0.5 rounded bg-cyan-dim text-cyan capitalize">
                            {trait}
                          </span>
                        ))}
                      </div>
                    </div>
                    <ChevronRight size={12} className="text-text-3 opacity-40 flex-shrink-0" />
                  </button>
                );
              })}
          </div>
        )}
      </div>

      {/* Effects (excluding purpose_category which is already shown) */}
      {data.effects && Object.keys(data.effects).filter(k => k !== 'purpose_category' && k !== 'type').length > 0 && (
        <div>
          <SectionLabel label={t('detail_effects', 'Effects')} />
          <JsonBlock data={Object.fromEntries(Object.entries(data.effects).filter(([k]) => k !== 'purpose_category' && k !== 'type'))} />
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Memory Detail — with importance visualization
   ═══════════════════════════════════════════════════════════ */

export function MemoryDetail({ data, t }: { data: any; t: TFn }) {
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

export function GodFeedDetail({ data, t }: { data: any; t: TFn }) {
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
