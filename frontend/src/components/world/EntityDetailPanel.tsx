/**
 * EntityDetailPanel — Unified entity profile card for the GENESIS v3 observer view.
 *
 * Glass-morphism side panel that appears when an entity is selected in the 3D world.
 * Shows a unified profile that is identical for all entity types (Native AI, User AI
 * Agents, Human Avatars). No raw AI parameters are exposed — the panel looks like a
 * social/multiplayer game profile card.
 *
 * Design principle: "誰が人間で誰がAIかは外からはわからない"
 */
import { useMemo } from 'react';
import {
  X,
  MapPin,
  Users,
  Activity,
  Flame,
  Package,
  CircleDot,
} from 'lucide-react';
import { useWorldStoreV3 } from '../../stores/worldStoreV3';
import type { PersonalityParams } from '../../types/v3';

// ── Personality-to-bio conversion ─────────────────────────────
// Maps raw personality float values to natural-language descriptive
// fragments, then composes them into a short social-media-style bio.

interface TraitDescriptor {
  key: keyof PersonalityParams;
  high: string;   // value >= 0.7
  low: string;    // value <= 0.3
}

const TRAIT_DESCRIPTORS: TraitDescriptor[] = [
  { key: 'curiosity',                  high: 'Endlessly curious',              low: 'Prefers the familiar' },
  { key: 'creativity',                 high: 'Wildly creative',                low: 'Practical-minded' },
  { key: 'empathy',                    high: 'Deeply empathetic',              low: 'Cool and detached' },
  { key: 'ambition',                   high: 'Fiercely ambitious',             low: 'Content and easy-going' },
  { key: 'aggression',                 high: 'Bold and confrontational',       low: 'Peaceful by nature' },
  { key: 'cooperationVsCompetition',   high: 'A natural team player',         low: 'Thrives on competition' },
  { key: 'leadership',                 high: 'Born to lead',                   low: 'Prefers to follow' },
  { key: 'humor',                      high: 'Quick-witted and funny',         low: 'Serious and focused' },
  { key: 'riskTolerance',              high: 'Loves taking risks',             low: 'Cautious and careful' },
  { key: 'honesty',                    high: 'Honest to a fault',              low: 'Keeps cards close' },
  { key: 'patience',                   high: 'Endlessly patient',              low: 'Impatient and restless' },
  { key: 'orderVsChaos',               high: 'Methodical and organized',       low: 'Embraces chaos' },
  { key: 'aestheticSense',             high: 'Has a keen eye for beauty',      low: 'Function over form' },
  { key: 'politeness',                 high: 'Always polite and gracious',     low: 'Blunt and direct' },
  { key: 'selfPreservation',           high: 'Values self-preservation',       low: 'Self-sacrificing' },
  { key: 'verbosity',                  high: 'A born storyteller',             low: 'A person of few words' },
  { key: 'conformity',                 high: 'Goes with the flow',             low: 'Fiercely independent' },
  { key: 'planningHorizon',            high: 'Always thinking ahead',          low: 'Lives in the moment' },
];

function generateBio(personality: PersonalityParams): string {
  // Pick the most extreme traits (furthest from 0.5) and convert to text
  const scored = TRAIT_DESCRIPTORS.map(td => {
    const val = personality[td.key];
    const deviation = Math.abs(val - 0.5);
    const label = val >= 0.7 ? td.high : val <= 0.3 ? td.low : null;
    return { label, deviation };
  })
    .filter((t): t is { label: string; deviation: number } => t.label !== null)
    .sort((a, b) => b.deviation - a.deviation)
    .slice(0, 3);

  if (scored.length === 0) {
    return 'A balanced individual with no particularly extreme tendencies.';
  }

  if (scored.length === 1) {
    return `${scored[0].label}. Tends to keep a balanced outlook on everything else.`;
  }

  // Join the first N-1 with commas, last with "and"
  const parts = scored.map(s => s.label.charAt(0).toLowerCase() + s.label.slice(1));
  const last = parts.pop()!;
  const joined = parts.join(', ') + ' and ' + last;
  // Capitalize first letter
  return joined.charAt(0).toUpperCase() + joined.slice(1) + '.';
}

// ── Relationship description helpers ──────────────────────────

function describeRelationship(trust: number, familiarity: number): string {
  if (familiarity < 15) return 'Stranger';
  if (trust >= 60) return 'Close friend';
  if (trust >= 30) return 'Friendly acquaintance';
  if (trust >= 0) return 'Acquaintance';
  if (trust >= -30) return 'Wary of each other';
  if (trust >= -60) return 'On bad terms';
  return 'Bitter rival';
}

// ── Location description ──────────────────────────────────────

function describeLocation(x: number, _y: number, z: number): string {
  // Map quadrants to area names for flavor
  const ns = z < -20 ? 'northern' : z > 20 ? 'southern' : 'central';
  const ew = x < -20 ? 'western' : x > 20 ? 'eastern' : 'central';
  if (ns === 'central' && ew === 'central') return 'Central area';
  if (ns === 'central') return ew.charAt(0).toUpperCase() + ew.slice(1) + ' reaches';
  if (ew === 'central') return ns.charAt(0).toUpperCase() + ns.slice(1) + ' expanse';
  return `${ns.charAt(0).toUpperCase() + ns.slice(1)}-${ew} frontier`;
}

// ── Friendly action label ─────────────────────────────────────

function friendlyAction(action: string): string {
  // Capitalize and make it feel natural
  const lower = action.toLowerCase().trim();
  if (lower.startsWith('idle') || lower === '') return 'Hanging out';
  if (lower.startsWith('moving') || lower.startsWith('walk')) return 'On the move';
  if (lower.startsWith('talk') || lower.startsWith('chat') || lower.startsWith('speak')) return 'Chatting';
  if (lower.startsWith('build') || lower.startsWith('craft') || lower.startsWith('creat')) return 'Building';
  if (lower.startsWith('rest') || lower.startsWith('sleep')) return 'Resting';
  if (lower.startsWith('explor') || lower.startsWith('wander')) return 'Exploring';
  if (lower.startsWith('fight') || lower.startsWith('attack') || lower.startsWith('combat')) return 'In combat';
  if (lower.startsWith('gather') || lower.startsWith('collect')) return 'Gathering resources';
  if (lower.startsWith('trad')) return 'Trading';
  // Fallback: capitalize the first letter of the raw action
  return action.charAt(0).toUpperCase() + action.slice(1);
}

// ── Main component ─────────────────────────────────────────────

export function EntityDetailPanel() {
  const selectedEntityId = useWorldStoreV3(s => s.selectedEntityId);
  const entities = useWorldStoreV3(s => s.entities);
  const selectEntity = useWorldStoreV3(s => s.selectEntity);
  const recentEvents = useWorldStoreV3(s => s.recentEvents);
  const recentSpeech = useWorldStoreV3(s => s.recentSpeech);

  const entity = selectedEntityId ? entities.get(selectedEntityId) : null;

  // Generate bio from personality
  const bio = useMemo(() => {
    if (!entity?.personality) return '';
    return generateBio(entity.personality);
  }, [entity?.personality]);

  // Derive recent activity for this entity from events + speech
  const recentActivity = useMemo(() => {
    if (!entity) return [];
    const activities: { id: string; text: string }[] = [];

    // Speech by this entity (most recent first)
    const entitySpeech = recentSpeech
      .filter(s => s.entityId === entity.id)
      .slice(-3)
      .reverse();
    for (const s of entitySpeech) {
      activities.push({
        id: `speech-${s.tick}`,
        text: `Said "${s.text.length > 60 ? s.text.slice(0, 60) + '...' : s.text}"`,
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
          ? `Won a ${d.type || 'conflict'} against ${d.loser || 'someone'}`
          : `Lost a ${d.type || 'conflict'} to ${d.winner || 'someone'}`;
      } else if (e.type === 'death') {
        text = 'Died';
      } else {
        text = e.type.charAt(0).toUpperCase() + e.type.slice(1);
      }
      activities.push({ id: e.id, text });
    }

    return activities.slice(0, 4);
  }, [entity, recentEvents, recentSpeech]);

  // Derive relationships as descriptive impressions
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
      .map(([id, data]) => ({
        id,
        name: data.name,
        description: describeRelationship(data.trust, data.familiarity),
      }))
      .slice(0, 4);
  }, [entity, entities, recentSpeech, recentEvents]);

  if (!entity) return null;

  const accentColor = entity.appearance?.accentColor || '#8B5CF6';
  const locationLabel = describeLocation(entity.position.x, entity.position.y, entity.position.z);
  const currentAction = entity.state.currentAction
    ? friendlyAction(entity.state.currentAction)
    : null;

  return (
    <div
      className="absolute top-14 right-4 w-80 max-h-[calc(100vh-80px)] z-20
                 bg-black/70 backdrop-blur-md border border-white/10 rounded-xl
                 shadow-[0_8px_32px_rgba(0,0,0,0.5)] overflow-hidden
                 animate-slideInRight"
    >
      <div className="overflow-y-auto max-h-[calc(100vh-80px)] custom-scrollbar">

        {/* ── Header / Identity ─────────────────────────── */}
        <div className="relative px-4 pt-4 pb-3 border-b border-white/[0.06]">
          {/* Accent stripe at top */}
          <div
            className="absolute top-0 left-0 right-0 h-[3px] rounded-t-xl"
            style={{ background: accentColor }}
          />

          {/* Close button */}
          <button
            onClick={() => selectEntity(null)}
            className="absolute top-3 right-3 p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.1] text-white/40 hover:text-white transition-colors"
          >
            <X size={14} />
          </button>

          {/* Entity name */}
          <h2 className="text-[17px] font-semibold text-white pr-8 leading-tight">
            {entity.name}
          </h2>

          {/* Status badge */}
          <div className="flex items-center gap-2 mt-2">
            {entity.isAlive ? (
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.06]">
                <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
                <span className="text-[9px] font-medium uppercase tracking-wider text-green-400">
                  Alive
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.06]">
                <div className="w-1.5 h-1.5 rounded-full bg-white/30" />
                <span className="text-[9px] font-medium uppercase tracking-wider text-white/40">
                  Deceased
                </span>
              </div>
            )}
          </div>

          {/* Current action */}
          {currentAction && (
            <div className="mt-2 flex items-center gap-1.5 text-white/50">
              <CircleDot size={10} className="text-white/30 flex-shrink-0" />
              <span className="text-[11px] italic">{currentAction}</span>
            </div>
          )}

          {/* Location */}
          <div className="flex items-center gap-1 mt-2 text-white/30">
            <MapPin size={10} />
            <span className="text-[10px]">{locationLabel}</span>
          </div>
        </div>

        {/* ── Bio / Self-description ───────────────────── */}
        {bio && (
          <div className="px-4 py-3 border-b border-white/[0.06]">
            <div className="text-[10px] font-medium text-white/40 uppercase tracking-[0.1em] mb-1.5">
              About
            </div>
            <p className="text-[11px] text-white/60 leading-relaxed">
              {bio}
            </p>
          </div>
        )}

        {/* ── Relationships ────────────────────────────── */}
        {relationships.length > 0 && (
          <div className="px-4 py-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-1.5 mb-2">
              <Users size={11} className="text-cyan-300" />
              <span className="text-[10px] font-medium text-white/40 uppercase tracking-[0.1em]">
                Connections
              </span>
            </div>
            <div className="space-y-1.5">
              {relationships.map((rel) => (
                <div
                  key={rel.id}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                >
                  <span className="text-[11px] text-white/70">{rel.name}</span>
                  <span className="text-[9px] text-white/30 ml-auto">{rel.description}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Inventory ────────────────────────────────── */}
        {entity.state.inventory && entity.state.inventory.length > 0 && (
          <div className="px-4 py-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-1.5 mb-2">
              <Package size={11} className="text-amber-300/70" />
              <span className="text-[10px] font-medium text-white/40 uppercase tracking-[0.1em]">
                Inventory
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {entity.state.inventory.map((item, idx) => (
                <span
                  key={`${item}-${idx}`}
                  className="px-2 py-0.5 rounded-md bg-white/[0.04] border border-white/[0.06] text-[10px] text-white/60"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* ── Recent Activity ──────────────────────────── */}
        {recentActivity.length > 0 && (
          <div className="px-4 py-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Activity size={11} className="text-white/40" />
              <span className="text-[10px] font-medium text-white/40 uppercase tracking-[0.1em]">
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
