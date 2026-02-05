/**
 * MobileEntityDetailSheet — Entity detail as a bottom sheet for mobile.
 *
 * Auto-opens to 'peek' when selectedEntityId changes.
 * Peek (120px): entity name + behavior badge + energy bar
 * Half/full: all detail sections (personality, needs, awareness, relationships)
 *
 * All text sizes bumped from desktop: 9px→12px, 10px→13px, 8px→11px
 */
import { useEffect, useMemo } from 'react';
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
import { useWorldStoreV3 } from '../../../stores/worldStoreV3';
import { useMobileStoreV3 } from '../../../stores/mobileStoreV3';
import { BottomSheet } from './BottomSheet';
import type { PersonalityParams, NeedsState } from '../../../types/v3';
import type { SheetState } from '../../../stores/mobileStoreV3';

// ── Personality labels ──────────────────────────────────────────
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

const NEED_LABELS: Record<keyof NeedsState, { label: string; icon: typeof Heart }> = {
  curiosity:         { label: 'Curiosity',     icon: Compass },
  social:            { label: 'Social',        icon: Users },
  creation:          { label: 'Creation',      icon: Sparkles },
  dominance:         { label: 'Dominance',     icon: Swords },
  safety:            { label: 'Safety',        icon: Shield },
  expression:        { label: 'Expression',    icon: Star },
  understanding:     { label: 'Understanding', icon: Brain },
  evolutionPressure: { label: 'Evolution',     icon: Zap },
};

const AWARENESS_LEVELS = [
  { threshold: 0,    label: 'Dormant',       color: 'from-blue-900 to-blue-700' },
  { threshold: 0.2,  label: 'Stirring',      color: 'from-blue-700 to-indigo-600' },
  { threshold: 0.4,  label: 'Sensing',       color: 'from-indigo-600 to-purple-500' },
  { threshold: 0.6,  label: 'Aware',         color: 'from-purple-500 to-purple-400' },
  { threshold: 0.8,  label: 'Awakened',      color: 'from-purple-400 to-amber-400' },
  { threshold: 0.95, label: 'Transcendent',  color: 'from-amber-400 to-yellow-300' },
];

function getAwarenessLevel(value: number) {
  let level = AWARENESS_LEVELS[0];
  for (const l of AWARENESS_LEVELS) {
    if (value >= l.threshold) level = l;
  }
  return level;
}

const BEHAVIOR_MODE_CONFIG: Record<string, { label: string; dotClass: string; textClass: string }> = {
  normal:    { label: 'Normal',    dotClass: 'bg-green-400',  textClass: 'text-green-400' },
  desperate: { label: 'Desperate', dotClass: 'bg-amber-400',  textClass: 'text-amber-400' },
  rampage:   { label: 'Rampage',   dotClass: 'bg-red-500 animate-pulse', textClass: 'text-red-400' },
};

function getExtremeTraits(personality: PersonalityParams, count: number) {
  const entries = Object.entries(personality) as [keyof PersonalityParams, number][];
  return entries
    .map(([key, val]) => ({ key, val, deviation: Math.abs(val - 0.5) }))
    .sort((a, b) => b.deviation - a.deviation)
    .slice(0, count);
}

function needColor(value: number): { bar: string; text: string } {
  if (value > 70) return { bar: 'bg-red-500', text: 'text-red-400' };
  if (value > 30) return { bar: 'bg-amber-400', text: 'text-amber-300' };
  return { bar: 'bg-green-400', text: 'text-green-400' };
}

// ── Component ───────────────────────────────────────────────────

export function MobileEntityDetailSheet() {
  const selectedEntityId = useWorldStoreV3(s => s.selectedEntityId);
  const entities = useWorldStoreV3(s => s.entities);
  const selectEntity = useWorldStoreV3(s => s.selectEntity);
  const recentEvents = useWorldStoreV3(s => s.recentEvents);
  const recentSpeech = useWorldStoreV3(s => s.recentSpeech);
  const entitySheetState = useMobileStoreV3(s => s.entitySheetState);
  const setEntitySheetState = useMobileStoreV3(s => s.setEntitySheetState);

  const entity = selectedEntityId ? entities.get(selectedEntityId) : null;

  // Auto-open to peek when entity is selected
  useEffect(() => {
    if (selectedEntityId) {
      setEntitySheetState('peek');
    } else {
      setEntitySheetState('closed');
    }
  }, [selectedEntityId, setEntitySheetState]);

  // Handle sheet state change - if closed, deselect entity
  const handleStateChange = (state: SheetState) => {
    setEntitySheetState(state);
    if (state === 'closed') {
      selectEntity(null);
    }
  };

  // Derive extreme personality traits
  const extremeTraits = useMemo(() => {
    if (!entity?.personality) return [];
    return getExtremeTraits(entity.personality, 6);
  }, [entity?.personality]);

  // Derive recent activity
  const recentActivity = useMemo(() => {
    if (!entity) return [];
    const activities: { id: string; text: string; tick?: number }[] = [];

    if (entity.state.currentAction) {
      activities.push({ id: 'current-action', text: entity.state.currentAction });
    }

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

  // Derive relationships
  const relationships = useMemo(() => {
    if (!entity) return [];
    const relationMap = new Map<string, { name: string; trust: number; familiarity: number }>();

    for (const s of recentSpeech) {
      if (s.entityId === entity.id) continue;
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

  // Peek content: entity name + behavior badge + energy bar
  const peekContent = (
    <div className="flex items-center gap-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h2 className="text-[15px] font-semibold text-white truncate">{entity.name}</h2>
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/[0.06] border border-white/[0.08] flex-shrink-0">
            <div className={`w-1.5 h-1.5 rounded-full ${modeConfig.dotClass}`} />
            <span className={`text-[11px] font-medium uppercase tracking-wider ${modeConfig.textClass}`}>
              {modeConfig.label}
            </span>
          </div>
          {entity.isGod && (
            <span className="px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-[11px] font-medium text-amber-400 uppercase tracking-wider flex-shrink-0">
              God
            </span>
          )}
        </div>
        {/* Energy bar */}
        <div className="mt-2 flex items-center gap-2">
          <Zap size={12} className="text-yellow-400/60 flex-shrink-0" />
          <div className="flex-1 h-[5px] bg-white/[0.06] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-yellow-500 to-amber-400 transition-all duration-500"
              style={{ width: `${Math.round(entity.state.energy * 100)}%` }}
            />
          </div>
          <span className="text-[12px] font-mono text-white/40 w-10 text-right">
            {Math.round(entity.state.energy * 100)}%
          </span>
        </div>
      </div>
      <button
        onClick={() => handleStateChange('closed')}
        className="flex items-center justify-center text-white/40 flex-shrink-0"
        style={{ width: 44, height: 44 }}
      >
        <X size={18} />
      </button>
    </div>
  );

  return (
    <BottomSheet
      state={entitySheetState}
      onStateChange={handleStateChange}
      peekContent={peekContent}
    >
      <div className="px-4 pb-6 space-y-4">
        {/* Position */}
        <div className="flex items-center gap-1.5 text-white/40">
          <MapPin size={12} />
          <span className="text-[12px] font-mono">
            ({entity.position.x.toFixed(1)}, {entity.position.y.toFixed(1)}, {entity.position.z.toFixed(1)})
          </span>
        </div>

        {/* Personality */}
        {entity.personality && extremeTraits.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Brain size={13} className="text-purple-400" />
              <span className="text-[12px] font-medium text-white/50 uppercase tracking-[0.1em]">
                Personality
              </span>
            </div>
            <div className="space-y-2">
              {extremeTraits.map(({ key, val }) => (
                <div key={key} className="flex items-center gap-2">
                  <span className="w-[110px] text-[12px] text-white/50 truncate">{PERSONALITY_LABELS[key]}</span>
                  <div className="flex-1 h-[7px] bg-white/[0.06] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-purple-500 transition-all duration-500"
                      style={{ width: `${Math.round(val * 100)}%` }}
                    />
                  </div>
                  <span className="w-10 text-right text-[12px] font-mono text-white/40">{val.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Needs */}
        {entity.state.needs && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Heart size={13} className="text-cyan-400" />
              <span className="text-[12px] font-medium text-white/50 uppercase tracking-[0.1em]">
                Needs
              </span>
            </div>
            <div className="space-y-2">
              {(Object.entries(entity.state.needs) as [keyof NeedsState, number][]).map(([key, val]) => {
                const config = NEED_LABELS[key];
                if (!config) return null;
                const colors = needColor(val);
                const pct = Math.min(100, val);
                return (
                  <div key={key} className="flex items-center gap-2">
                    <config.icon size={12} className={`flex-shrink-0 ${colors.text}`} />
                    <span className="w-[90px] text-[12px] text-white/50 truncate">{config.label}</span>
                    <div className="flex-1 h-[6px] bg-white/[0.06] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${colors.bar} transition-all duration-500`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-8 text-right text-[12px] font-mono text-white/40">{Math.round(val)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Awareness */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Eye size={13} className="text-purple-300" />
            <span className="text-[12px] font-medium text-white/50 uppercase tracking-[0.1em]">
              Awareness
            </span>
          </div>

          {entity.state.currentAction && (
            <div className="mb-2 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.04]">
              <div className="text-[11px] text-white/30 uppercase tracking-wider mb-0.5">Current State</div>
              <div className="text-[13px] text-white/70 capitalize">{entity.state.currentAction}</div>
            </div>
          )}

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[12px] text-white/40">Meta-Awareness</span>
              <span className="text-[12px] font-medium text-white/60">{awarenessLevel.label}</span>
            </div>
            <div className="h-[7px] bg-white/[0.06] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${awarenessLevel.color} transition-all duration-700`}
                style={{ width: `${Math.round(entity.metaAwareness * 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-white/20 font-mono">
              <span>Dormant</span>
              <span>{entity.metaAwareness.toFixed(2)}</span>
              <span>Transcendent</span>
            </div>
          </div>
        </div>

        {/* Relationships */}
        {relationships.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Users size={13} className="text-cyan-300" />
              <span className="text-[12px] font-medium text-white/50 uppercase tracking-[0.1em]">
                Relationships
              </span>
              <span className="text-[11px] text-white/20 ml-auto">{relationships.length}</span>
            </div>
            <div className="space-y-2">
              {relationships.map((rel) => {
                const trustNorm = (rel.trust + 100) / 200;
                const trustColor = rel.trust >= 0 ? 'from-yellow-600 to-green-500' : 'from-red-600 to-yellow-600';
                return (
                  <div
                    key={rel.id}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] text-white/70 truncate">{rel.name}</div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[11px] text-white/30">Trust</span>
                        <div className="flex-1 h-[4px] bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full bg-gradient-to-r ${trustColor} transition-all`}
                            style={{ width: `${Math.round(trustNorm * 100)}%` }}
                          />
                        </div>
                        <span className="text-[11px] font-mono text-white/30">{Math.round(rel.trust)}</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-center gap-0.5 flex-shrink-0">
                      <div className="flex gap-0.5">
                        {[0, 1, 2, 3, 4].map(i => (
                          <div
                            key={i}
                            className={`w-1.5 h-1.5 rounded-full ${
                              i < Math.round(rel.familiarity / 20) ? 'bg-cyan-400' : 'bg-white/[0.08]'
                            }`}
                          />
                        ))}
                      </div>
                      <span className="text-[9px] text-white/20">familiar</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Recent Activity */}
        {recentActivity.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Activity size={13} className="text-white/40" />
              <span className="text-[12px] font-medium text-white/50 uppercase tracking-[0.1em]">
                Recent Activity
              </span>
            </div>
            <div className="space-y-1.5">
              {recentActivity.map((act) => (
                <div
                  key={act.id}
                  className="flex items-start gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                >
                  <Flame size={11} className="text-white/20 mt-0.5 flex-shrink-0" />
                  <span className="text-[12px] text-white/50 leading-relaxed flex-1">
                    {act.text}
                  </span>
                  {act.tick !== undefined && (
                    <span className="text-[11px] font-mono text-white/20 flex-shrink-0">
                      T:{act.tick}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </BottomSheet>
  );
}
