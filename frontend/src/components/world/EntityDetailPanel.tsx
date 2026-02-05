/**
 * EntityDetailPanel — Rich entity detail sidebar for the GENESIS v3 observer view.
 *
 * Glass-morphism side panel that appears when an entity is selected in the 3D world.
 * Shows personality, needs, emotional state, relationships, and recent activity.
 */
import { useMemo } from 'react';
import {
  X,
  MapPin,
  Zap,
  Heart,
  Users,
  Activity,
  Brain,
  Shield,
  Flame,
  Sparkles,
  Eye,
  Compass,
  Swords,
  Star,
} from 'lucide-react';
import { useWorldStoreV3 } from '../../stores/worldStoreV3';
import type { PersonalityParams, NeedsState } from '../../types/v3';

// ── Personality axis labels & display ──────────────────────────

const PERSONALITY_LABELS: Record<keyof PersonalityParams, string> = {
  orderVsChaos: 'Order vs Chaos',
  cooperationVsCompetition: 'Cooperation',
  curiosity: 'Curiosity',
  ambition: 'Ambition',
  empathy: 'Empathy',
  aggression: 'Aggression',
  creativity: 'Creativity',
  riskTolerance: 'Risk Tolerance',
  selfPreservation: 'Self-Preservation',
  aestheticSense: 'Aesthetic Sense',
  verbosity: 'Verbosity',
  politeness: 'Politeness',
  leadership: 'Leadership',
  honesty: 'Honesty',
  humor: 'Humor',
  patience: 'Patience',
  planningHorizon: 'Planning',
  conformity: 'Conformity',
};

// ── Need display config ────────────────────────────────────────

const NEED_LABELS: Record<keyof NeedsState, { label: string; icon: typeof Heart }> = {
  curiosity:         { label: 'Curiosity',    icon: Compass },
  social:            { label: 'Social',       icon: Users },
  creation:          { label: 'Creation',     icon: Sparkles },
  dominance:         { label: 'Dominance',    icon: Swords },
  safety:            { label: 'Safety',       icon: Shield },
  expression:        { label: 'Expression',   icon: Star },
  understanding:     { label: 'Understanding', icon: Brain },
  evolutionPressure: { label: 'Evolution',    icon: Zap },
};

// ── Meta-awareness levels ──────────────────────────────────────

const AWARENESS_LEVELS = [
  { threshold: 0,   label: 'Dormant',      color: 'from-blue-900 to-blue-700' },
  { threshold: 0.2, label: 'Stirring',     color: 'from-blue-700 to-indigo-600' },
  { threshold: 0.4, label: 'Sensing',      color: 'from-indigo-600 to-purple-500' },
  { threshold: 0.6, label: 'Aware',        color: 'from-purple-500 to-purple-400' },
  { threshold: 0.8, label: 'Awakened',     color: 'from-purple-400 to-amber-400' },
  { threshold: 0.95, label: 'Transcendent', color: 'from-amber-400 to-yellow-300' },
];

function getAwarenessLevel(value: number) {
  let level = AWARENESS_LEVELS[0];
  for (const l of AWARENESS_LEVELS) {
    if (value >= l.threshold) level = l;
  }
  return level;
}

// ── Behavior mode config ───────────────────────────────────────

const BEHAVIOR_MODE_CONFIG: Record<string, { label: string; dotClass: string; textClass: string }> = {
  normal:    { label: 'Normal',    dotClass: 'bg-green-400',  textClass: 'text-green-400' },
  desperate: { label: 'Desperate', dotClass: 'bg-amber-400',  textClass: 'text-amber-400' },
  rampage:   { label: 'Rampage',   dotClass: 'bg-red-500 animate-pulse', textClass: 'text-red-400' },
};

// ── Helper: get top N most extreme personality traits ──────────

function getExtremeTraits(personality: PersonalityParams, count: number) {
  const entries = Object.entries(personality) as [keyof PersonalityParams, number][];
  return entries
    .map(([key, val]) => ({ key, val, deviation: Math.abs(val - 0.5) }))
    .sort((a, b) => b.deviation - a.deviation)
    .slice(0, count);
}

// ── Helper: need urgency color ─────────────────────────────────

function needColor(value: number): { bar: string; text: string } {
  if (value > 70) return { bar: 'bg-red-500', text: 'text-red-400' };
  if (value > 30) return { bar: 'bg-amber-400', text: 'text-amber-300' };
  return { bar: 'bg-green-400', text: 'text-green-400' };
}

// ── Helper: render a bar for personality ───────────────────────

function PersonalityBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="w-[100px] text-[10px] text-white/50 truncate">{label}</span>
      <div className="flex-1 h-[6px] bg-white/[0.06] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-purple-500 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-right text-[10px] font-mono text-white/40">{value.toFixed(2)}</span>
    </div>
  );
}

// ── Helper: render a need bar ──────────────────────────────────

function NeedBar({ label, value, icon: Icon }: { label: string; value: number; icon: typeof Heart }) {
  const colors = needColor(value);
  const pct = Math.min(100, value);
  return (
    <div className="flex items-center gap-2">
      <Icon size={10} className={`flex-shrink-0 ${colors.text}`} />
      <span className="w-[76px] text-[10px] text-white/50 truncate">{label}</span>
      <div className="flex-1 h-[5px] bg-white/[0.06] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${colors.bar} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-6 text-right text-[9px] font-mono text-white/40">{Math.round(value)}</span>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────

export function EntityDetailPanel() {
  const selectedEntityId = useWorldStoreV3(s => s.selectedEntityId);
  const entities = useWorldStoreV3(s => s.entities);
  const selectEntity = useWorldStoreV3(s => s.selectEntity);
  const recentEvents = useWorldStoreV3(s => s.recentEvents);
  const recentSpeech = useWorldStoreV3(s => s.recentSpeech);

  const entity = selectedEntityId ? entities.get(selectedEntityId) : null;

  // Derive top 6 extreme personality traits
  const extremeTraits = useMemo(() => {
    if (!entity?.personality) return [];
    return getExtremeTraits(entity.personality, 6);
  }, [entity?.personality]);

  // Derive recent activity for this entity from events + speech
  const recentActivity = useMemo(() => {
    if (!entity) return [];
    const activities: { id: string; text: string; tick?: number }[] = [];

    // Current action
    if (entity.state.currentAction) {
      activities.push({
        id: 'current-action',
        text: entity.state.currentAction,
      });
    }

    // Speech by this entity (most recent first)
    const entitySpeech = recentSpeech
      .filter(s => s.entityId === entity.id)
      .slice(-3)
      .reverse();
    for (const s of entitySpeech) {
      activities.push({
        id: `speech-${s.tick}`,
        text: `said "${s.text.length > 50 ? s.text.slice(0, 50) + '...' : s.text}"`,
        tick: s.tick,
      });
    }

    // Events involving this entity
    const entityEvents = recentEvents
      .filter(e => {
        const d = e.data;
        return (
          d?.entityId === entity.id ||
          d?.actorId === entity.id ||
          d?.winner === entity.name ||
          d?.loser === entity.name
        );
      })
      .slice(-3)
      .reverse();
    for (const e of entityEvents) {
      let text = '';
      if (e.type === 'conflict') {
        const d = e.data;
        text = d.winner === entity.name
          ? `won a ${d.type || 'conflict'} against ${d.loser || 'someone'}`
          : `lost a ${d.type || 'conflict'} to ${d.winner || 'someone'}`;
      } else if (e.type === 'death') {
        text = 'died';
      } else {
        text = e.type;
      }
      activities.push({ id: e.id, text, tick: e.tick });
    }

    return activities.slice(0, 5);
  }, [entity, recentEvents, recentSpeech]);

  // Derive mock relationships from entities that appear together in events
  // In a full implementation, relationships would come from the backend via RelationshipV3
  const relationships = useMemo(() => {
    if (!entity) return [];
    // Look for other entities mentioned together in speech/events with this entity
    const relationMap = new Map<string, { name: string; trust: number; familiarity: number }>();

    for (const s of recentSpeech) {
      if (s.entityId === entity.id) continue;
      // If this entity spoke recently, and another entity also spoke recently, they're familiar
      const other = entities.get(s.entityId);
      if (!other) continue;
      const existing = relationMap.get(s.entityId);
      if (existing) {
        existing.familiarity = Math.min(100, existing.familiarity + 10);
      } else {
        relationMap.set(s.entityId, { name: other.name, trust: 50, familiarity: 20 });
      }
    }

    for (const e of recentEvents) {
      if (e.type === 'conflict') {
        const d = e.data;
        if (d.winner === entity.name && d.loserId) {
          const other = entities.get(d.loserId);
          if (other) {
            const existing = relationMap.get(d.loserId);
            if (existing) {
              existing.trust = Math.max(-100, existing.trust - 20);
              existing.familiarity = Math.min(100, existing.familiarity + 15);
            } else {
              relationMap.set(d.loserId, { name: other.name, trust: -20, familiarity: 30 });
            }
          }
        }
      }
    }

    return Array.from(relationMap.entries())
      .map(([id, data]) => ({ id, ...data }))
      .sort((a, b) => (Math.abs(b.trust) + b.familiarity) - (Math.abs(a.trust) + a.familiarity))
      .slice(0, 3);
  }, [entity, entities, recentSpeech, recentEvents]);

  if (!entity) return null;

  const awarenessLevel = getAwarenessLevel(entity.metaAwareness);
  const modeConfig = BEHAVIOR_MODE_CONFIG[entity.state.behaviorMode] || BEHAVIOR_MODE_CONFIG.normal;

  return (
    <div
      className="absolute top-14 right-4 w-80 max-h-[calc(100vh-80px)] z-20
                 bg-black/70 backdrop-blur-md border border-white/10 rounded-xl
                 shadow-[0_8px_32px_rgba(0,0,0,0.5)] overflow-hidden
                 animate-slideInRight"
    >
      <div className="overflow-y-auto max-h-[calc(100vh-80px)] custom-scrollbar">

        {/* ── Header Section ─────────────────────────────── */}
        <div className="relative px-4 pt-4 pb-3 border-b border-white/[0.06]">
          {/* Close button */}
          <button
            onClick={() => selectEntity(null)}
            className="absolute top-3 right-3 p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.1] text-white/40 hover:text-white transition-colors"
          >
            <X size={14} />
          </button>

          {/* Entity name */}
          <h2 className="text-[16px] font-semibold text-white pr-8 leading-tight">
            {entity.name}
          </h2>

          {/* Badges row */}
          <div className="flex items-center gap-2 mt-2">
            {/* Behavior mode indicator */}
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.06]">
              <div className={`w-1.5 h-1.5 rounded-full ${modeConfig.dotClass}`} />
              <span className={`text-[9px] font-medium uppercase tracking-wider ${modeConfig.textClass}`}>
                {modeConfig.label}
              </span>
            </div>

            {/* Alive/Dead */}
            {!entity.isAlive && (
              <span className="px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/20 text-[9px] font-medium text-red-400 uppercase tracking-wider">
                Deceased
              </span>
            )}

            {/* God indicator */}
            {entity.isGod && (
              <span className="px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-[9px] font-medium text-amber-400 uppercase tracking-wider">
                God
              </span>
            )}
          </div>

          {/* Position */}
          <div className="flex items-center gap-1 mt-2 text-white/30">
            <MapPin size={10} />
            <span className="text-[9px] font-mono">
              ({entity.position.x.toFixed(1)}, {entity.position.y.toFixed(1)}, {entity.position.z.toFixed(1)})
            </span>
          </div>

          {/* Energy bar */}
          <div className="mt-2 flex items-center gap-2">
            <Zap size={10} className="text-yellow-400/60 flex-shrink-0" />
            <div className="flex-1 h-[4px] bg-white/[0.06] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-yellow-500 to-amber-400 transition-all duration-500"
                style={{ width: `${Math.round(entity.state.energy * 100)}%` }}
              />
            </div>
            <span className="text-[9px] font-mono text-white/30 w-8 text-right">
              {Math.round(entity.state.energy * 100)}%
            </span>
          </div>
        </div>

        {/* ── Personality Radar ───────────────────────────── */}
        {entity.personality && extremeTraits.length > 0 && (
          <div className="px-4 py-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-1.5 mb-2.5">
              <Brain size={11} className="text-purple-400" />
              <span className="text-[10px] font-medium text-white/50 uppercase tracking-[0.1em]">
                Personality
              </span>
            </div>
            <div className="space-y-1.5">
              {extremeTraits.map(({ key, val }) => (
                <PersonalityBar
                  key={key}
                  label={PERSONALITY_LABELS[key]}
                  value={val}
                />
              ))}
            </div>
          </div>
        )}

        {/* ── Needs Section ───────────────────────────────── */}
        {entity.state.needs && (
          <div className="px-4 py-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-1.5 mb-2.5">
              <Heart size={11} className="text-cyan-400" />
              <span className="text-[10px] font-medium text-white/50 uppercase tracking-[0.1em]">
                Needs
              </span>
            </div>
            <div className="space-y-1.5">
              {(Object.entries(entity.state.needs) as [keyof NeedsState, number][]).map(([key, val]) => {
                const config = NEED_LABELS[key];
                if (!config) return null;
                return (
                  <NeedBar
                    key={key}
                    label={config.label}
                    value={val}
                    icon={config.icon}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* ── Emotional State / Meta-Awareness ────────────── */}
        <div className="px-4 py-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-1.5 mb-2.5">
            <Eye size={11} className="text-purple-300" />
            <span className="text-[10px] font-medium text-white/50 uppercase tracking-[0.1em]">
              Awareness
            </span>
          </div>

          {/* Current action / mood */}
          {entity.state.currentAction && (
            <div className="mb-2 px-2.5 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.04]">
              <div className="text-[9px] text-white/30 uppercase tracking-wider mb-0.5">Current State</div>
              <div className="text-[11px] text-white/70 capitalize">
                {entity.state.currentAction}
              </div>
            </div>
          )}

          {/* Meta-awareness bar */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-white/40">Meta-Awareness</span>
              <span className="text-[10px] font-medium text-white/60">{awarenessLevel.label}</span>
            </div>
            <div className="h-[6px] bg-white/[0.06] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${awarenessLevel.color} transition-all duration-700`}
                style={{ width: `${Math.round(entity.metaAwareness * 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-[8px] text-white/20 font-mono">
              <span>Dormant</span>
              <span>{entity.metaAwareness.toFixed(2)}</span>
              <span>Transcendent</span>
            </div>
          </div>
        </div>

        {/* ── Relationships (top 3) ───────────────────────── */}
        {relationships.length > 0 && (
          <div className="px-4 py-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-1.5 mb-2.5">
              <Users size={11} className="text-cyan-300" />
              <span className="text-[10px] font-medium text-white/50 uppercase tracking-[0.1em]">
                Relationships
              </span>
              <span className="text-[9px] text-white/20 ml-auto">{relationships.length}</span>
            </div>
            <div className="space-y-2">
              {relationships.map((rel) => {
                const trustNorm = (rel.trust + 100) / 200; // normalize -100..100 to 0..1
                const trustColor = rel.trust >= 0 ? 'from-yellow-600 to-green-500' : 'from-red-600 to-yellow-600';
                return (
                  <div
                    key={rel.id}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-[10px] text-white/70 truncate">{rel.name}</div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[8px] text-white/30">Trust</span>
                        <div className="flex-1 h-[3px] bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full bg-gradient-to-r ${trustColor} transition-all`}
                            style={{ width: `${Math.round(trustNorm * 100)}%` }}
                          />
                        </div>
                        <span className="text-[8px] font-mono text-white/30">{Math.round(rel.trust)}</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-center gap-0.5 flex-shrink-0">
                      <div className="flex gap-0.5">
                        {[0, 1, 2, 3, 4].map(i => (
                          <div
                            key={i}
                            className={`w-1 h-1 rounded-full ${
                              i < Math.round(rel.familiarity / 20) ? 'bg-cyan-400' : 'bg-white/[0.08]'
                            }`}
                          />
                        ))}
                      </div>
                      <span className="text-[7px] text-white/20">familiar</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Recent Activity ─────────────────────────────── */}
        {recentActivity.length > 0 && (
          <div className="px-4 py-3">
            <div className="flex items-center gap-1.5 mb-2.5">
              <Activity size={11} className="text-white/40" />
              <span className="text-[10px] font-medium text-white/50 uppercase tracking-[0.1em]">
                Recent Activity
              </span>
            </div>
            <div className="space-y-1">
              {recentActivity.map((act) => (
                <div
                  key={act.id}
                  className="flex items-start gap-2 px-2 py-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                >
                  <Flame size={9} className="text-white/20 mt-0.5 flex-shrink-0" />
                  <span className="text-[10px] text-white/50 leading-relaxed flex-1">
                    {act.text}
                  </span>
                  {act.tick !== undefined && (
                    <span className="text-[8px] font-mono text-white/20 flex-shrink-0">
                      T:{act.tick}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Bottom padding for scrolling */}
        <div className="h-2" />
      </div>

      {/* Inline keyframes for slide-in animation */}
      <style>{`
        @keyframes slideInRight {
          from {
            opacity: 0;
            transform: translateX(24px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        .animate-slideInRight {
          animation: slideInRight 0.25s ease-out;
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.08);
          border-radius: 2px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.15);
        }
      `}</style>
    </div>
  );
}
