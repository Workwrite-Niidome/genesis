import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Brain,
  MessageCircle,
  Users,
  ArrowRight,
  Loader2,
  Zap,
  ChevronRight,
} from 'lucide-react';
import { useDetailStore } from '../../../stores/detailStore';
import { useAIStore } from '../../../stores/aiStore';
import { api } from '../../../services/api';
import type { AIEntity, Interaction } from '../../../types/world';

export type TFn = (k: string, f?: string) => string;

/** AI profile mini card */
export function AIProfileCard({ ai, onClick }: { ai: AIEntity; onClick?: () => void }) {
  const { t } = useTranslation();
  const color = ai.appearance?.primaryColor || '#7c5bf5';
  const traits = ai.personality_traits || [];

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
            {ai.is_alive ? t('alive') : t('dead')}
          </span>
        </div>
        <div className="flex items-center gap-1.5 mt-1 flex-wrap">
          {traits.slice(0, 4).map((trait) => (
            <span key={trait} className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-dim text-cyan capitalize">
              {trait}
            </span>
          ))}
        </div>
      </div>
      <ArrowRight size={14} className="text-text-3 opacity-40 flex-shrink-0" />
    </button>
  );
}

/** Full conversation view for an Interaction — handles both 1-on-1 and group gathering formats */
export function ConversationView({ interaction, t }: { interaction: Interaction; t: TFn }) {
  const content = interaction.content;
  const isGroup = interaction.interaction_type === 'group_gathering';

  if (isGroup) {
    return <GroupConversationView content={content} interaction={interaction} t={t} />;
  }

  return <PairConversationView content={content} interaction={interaction} t={t} />;
}

/** 1-on-1 conversation view — supports both multi-turn (turns array) and legacy format */
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
  const turns = content.turns;
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

  // Multi-turn format
  if (turns && turns.length > 0) {
    return (
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center gap-2">
          <MessageCircle size={12} className="text-rose-400" />
          <span className="text-[11px] font-medium text-rose-400 uppercase tracking-wider">
            {t(`interaction_type_${interaction.interaction_type}`, interaction.interaction_type)}
          </span>
          <span className="text-[10px] mono text-text-3 ml-auto">
            {t('tick')} {interaction.tick_number} · {turns.length} turns
          </span>
        </div>

        {/* Render each turn */}
        {turns.map((turn, idx) => {
          const isAi1 = turn.speaker === 'ai1';
          const name = turn.speaker_name || (isAi1 ? ai1Name : ai2Name);
          const color = isAi1 ? ai1Color : ai2Color;
          const side = isAi1 ? 'left' as const : 'right' as const;

          return (
            <div key={idx}>
              {idx > 0 && (
                <div className="flex items-center gap-2 px-2 my-2">
                  <div className="flex-1 h-px bg-white/[0.06]" />
                  {turn.emotion && (
                    <span className="text-[9px] text-text-3 opacity-40 italic">{turn.emotion}</span>
                  )}
                  <div className="flex-1 h-px bg-white/[0.06]" />
                </div>
              )}
              <ConversationTurnView
                name={name}
                color={color}
                thought={turn.thought}
                message={turn.message}
                side={side}
                t={t}
              />
            </div>
          );
        })}
      </div>
    );
  }

  // Legacy 2-turn format (backward compat)
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <MessageCircle size={12} className="text-rose-400" />
        <span className="text-[11px] font-medium text-rose-400 uppercase tracking-wider">
          {t(`interaction_type_${interaction.interaction_type}`, interaction.interaction_type)}
        </span>
        <span className="text-[10px] mono text-text-3 ml-auto">{t('tick')} {interaction.tick_number}</span>
      </div>

      <ConversationTurnView
        name={ai1Name}
        color={ai1Color}
        thought={ai1?.thought}
        message={ai1?.message}
        action={ai1?.action}
        side="left"
        t={t}
      />

      <div className="flex items-center gap-2 px-2">
        <div className="flex-1 h-px bg-white/[0.06]" />
        <ArrowRight size={12} className="text-text-3 opacity-30 rotate-90" />
        <div className="flex-1 h-px bg-white/[0.06]" />
      </div>

      <ConversationTurnView
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
        <span className="text-[10px] mono text-text-3 ml-auto">{t('tick')} {interaction.tick_number}</span>
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
function ConversationTurnView({
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
export function InteractionPreview({ interaction, t }: { interaction: Interaction; t: TFn }) {
  const openDetail = useDetailStore((s) => s.openDetail);
  const content = interaction.content;
  const isGroup = interaction.interaction_type === 'group_gathering';
  const turns = content.turns;

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
        ) : turns && turns.length > 0 ? (
          /* Multi-turn format: show first 2 turns */
          turns.slice(0, 2).map((turn, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <span className={`text-[10px] font-medium flex-shrink-0 mt-0.5 w-16 truncate ${
                turn.speaker === 'ai1' ? 'text-accent' : 'text-cyan'
              }`}>
                {turn.speaker_name}:
              </span>
              <p className="text-[11px] text-text-2 leading-relaxed line-clamp-2">{turn.message}</p>
            </div>
          ))
        ) : (
          /* Legacy format */
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

export function MetaInfo({ tick, timestamp, importance }: { tick?: number; timestamp?: string; importance?: number }) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-3 text-[11px] text-text-3 flex-wrap">
      {tick != null && <span className="mono">{t('tick')} {tick}</span>}
      {importance != null && <span>{t('importance')} {Math.round(importance * 100)}%</span>}
      {timestamp && <span>{new Date(timestamp).toLocaleString()}</span>}
    </div>
  );
}

export function ImportanceBar({ importance }: { importance: number }) {
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

export function SectionLabel({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <span className="text-[10px] font-medium text-text-3 uppercase tracking-wider">
        {label}
      </span>
      <div className="flex-1 h-px bg-white/[0.06]" />
    </div>
  );
}

export function LoadingBlock() {
  return (
    <div className="flex items-center justify-center py-4">
      <Loader2 size={16} className="text-text-3 animate-spin" />
    </div>
  );
}

export function JsonBlock({ data }: { data: Record<string, any> }) {
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
