import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Zap, Clock, Sparkles, MapPin, Brain, Users, TrendingUp, Lightbulb, Palette, Building2 } from 'lucide-react';
import { useAIStore } from '../../stores/aiStore';
import { api } from '../../services/api';
import type { AIThought, Relationship, Artifact } from '../../types/world';

const creatorLabels: Record<string, string> = {
  god: 'Spawned by God AI',
  ai: 'Born from another AI',
  spontaneous: 'Emerged spontaneously',
  observer: 'Deployed by Observer',
};

const relColors: Record<string, string> = {
  ally: 'text-green',
  friendly: 'text-cyan',
  neutral: 'text-text-3',
  wary: 'text-orange',
  rival: 'text-rose',
};

const artifactTypeIcons: Record<string, string> = {
  art: '🎨', story: '📖', law: '⚖️', currency: '💰', song: '🎵',
  architecture: '🏛️', tool: '🔧', ritual: '🕯️', game: '🎲',
};

export default function AIDetailCard() {
  const { t } = useTranslation();
  const { selectedAI, selectedMemories } = useAIStore();
  const [aiArtifacts, setAiArtifacts] = useState<Artifact[]>([]);

  useEffect(() => {
    if (!selectedAI) {
      setAiArtifacts([]);
      return;
    }
    api.artifacts.getByAI(selectedAI.id).then(setAiArtifacts).catch(() => setAiArtifacts([]));
  }, [selectedAI?.id]);

  if (!selectedAI) return null;

  const color = selectedAI.appearance?.primaryColor || '#7c5bf5';
  const energy = typeof selectedAI.state?.energy === 'number' ? selectedAI.state.energy : null;
  const age = typeof selectedAI.state?.age === 'number' ? selectedAI.state.age : null;
  const evolutionScore = typeof selectedAI.state?.evolution_score === 'number' ? selectedAI.state.evolution_score : 0;
  const shape = selectedAI.appearance?.shape || 'circle';
  const personalityTraits = selectedAI.personality_traits || [];
  const recentThoughts: AIThought[] = selectedAI.recent_thoughts || [];
  const relationships: Record<string, Relationship> = selectedAI.state?.relationships || {};
  const adoptedConcepts: string[] = selectedAI.state?.adopted_concepts || [];
  const organizations: { name: string; role: string }[] = selectedAI.state?.organizations || [];
  const createdArtifacts: string[] = selectedAI.state?.created_artifacts || [];

  // Collect any "law" or "trait" style string values from state
  const traits = Object.entries(selectedAI.state || {})
    .filter(([key, val]) => typeof val === 'string' && key !== 'name')
    .map(([key, val]) => ({ key: formatKey(key), value: String(val) }));

  return (
    <div className="absolute top-20 left-4 z-40 w-80 pointer-events-auto">
      <div className="glass rounded-2xl border border-border shadow-[0_8px_40px_rgba(0,0,0,0.5)] fade-in overflow-hidden">
        {/* Hero banner with entity color */}
        <div className="relative h-16 overflow-hidden">
          <div
            className="absolute inset-0"
            style={{
              background: `radial-gradient(ellipse at 30% 50%, ${color}30 0%, transparent 70%), linear-gradient(135deg, ${color}10, transparent)`,
            }}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[rgba(12,12,20,0.9)] to-transparent" />
          {/* Close button */}
          <button
            onClick={() => useAIStore.getState().selectAI(null)}
            className="absolute top-2 right-2 p-1.5 rounded-lg bg-black/30 hover:bg-white/[0.08] text-text-3 hover:text-text transition-colors"
          >
            <X size={12} />
          </button>
        </div>

        {/* Identity */}
        <div className="px-4 -mt-5 relative">
          <div className="flex items-end gap-3">
            {/* Avatar */}
            <div
              className={`w-10 h-10 ${shape === 'circle' ? 'rounded-full' : shape === 'square' ? 'rounded-lg' : 'rounded-lg'} border-2 border-bg flex-shrink-0`}
              style={{
                backgroundColor: color,
                boxShadow: `0 0 20px ${color}50`,
              }}
            />
            <div className="flex-1 min-w-0 pb-0.5">
              <div className="flex items-center gap-2">
                <span className="text-[12px] font-medium text-text truncate">
                  {selectedAI.name || `Entity ${selectedAI.id.slice(0, 8)}`}
                </span>
                <span className={`badge text-[8px] ${selectedAI.is_alive ? 'bg-green-dim text-green' : 'bg-orange-dim text-orange'}`}>
                  {selectedAI.is_alive ? t('alive') : t('dead')}
                </span>
              </div>
              <div className="text-[10px] text-text-3 mt-0.5">
                {creatorLabels[selectedAI.creator_type] || selectedAI.creator_type}
              </div>
            </div>
          </div>
        </div>

        {/* Stats grid */}
        <div className="px-4 pt-4 pb-1 grid grid-cols-2 gap-2">
          {/* Energy */}
          {energy !== null && (
            <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <div className="flex items-center gap-1.5 mb-2">
                <Zap size={10} className="text-cyan" />
                <span className="text-[9px] text-text-3 uppercase tracking-wider">{t('energy')}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, energy * 100)}%`,
                      background: `linear-gradient(90deg, ${color}, ${color}cc)`,
                      boxShadow: `0 0 6px ${color}40`,
                    }}
                  />
                </div>
                <span className="text-[10px] mono text-text-2">{Math.round(energy * 100)}%</span>
              </div>
            </div>
          )}

          {/* Age */}
          {age !== null && (
            <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <div className="flex items-center gap-1.5 mb-2">
                <Clock size={10} className="text-accent" />
                <span className="text-[9px] text-text-3 uppercase tracking-wider">{t('age')}</span>
              </div>
              <span className="text-[13px] mono font-medium text-text">
                {age} <span className="text-[9px] text-text-3 font-normal">{age === 1 ? 'tick' : 'ticks'}</span>
              </span>
            </div>
          )}

          {/* Location */}
          <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
            <div className="flex items-center gap-1.5 mb-2">
              <MapPin size={10} className="text-green" />
              <span className="text-[9px] text-text-3 uppercase tracking-wider">{t('location')}</span>
            </div>
            <span className="text-[11px] mono text-text-2">
              {selectedAI.position_x.toFixed(0)}, {selectedAI.position_y.toFixed(0)}
            </span>
          </div>

          {/* Evolution Score */}
          <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingUp size={10} className="text-accent" />
              <span className="text-[9px] text-text-3 uppercase tracking-wider">{t('evolution_score')}</span>
            </div>
            <span className="text-[13px] mono font-medium text-accent">
              {evolutionScore.toFixed(1)}
            </span>
          </div>
        </div>

        {/* Personality traits */}
        {personalityTraits.length > 0 && (
          <div className="px-4 py-2">
            <div className="text-[9px] font-medium text-text-3 uppercase tracking-wider mb-1.5">
              {t('personality')}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {personalityTraits.map((trait) => (
                <span
                  key={trait}
                  className="px-2 py-0.5 rounded-md bg-cyan-dim border border-cyan/10 text-[9px] text-cyan capitalize"
                >
                  {t(`trait_${trait}`, trait)}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Traits / known laws */}
        {traits.length > 0 && (
          <div className="px-4 py-2">
            <div className="flex flex-wrap gap-1.5">
              {traits.map(({ key, value }) => (
                <div
                  key={key}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-accent-dim border border-accent/10"
                >
                  <span className="text-[9px] text-accent/70 uppercase">{key}</span>
                  <span className="text-[10px] text-accent font-medium">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Thoughts */}
        {recentThoughts.length > 0 && (
          <div className="px-4 pt-1 pb-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Brain size={10} className="text-accent" />
              <span className="text-[9px] font-medium text-text-3 uppercase tracking-wider">
                {t('recent_thoughts')} ({recentThoughts.length})
              </span>
            </div>
            <div className="space-y-1.5 max-h-28 overflow-y-auto">
              {recentThoughts.map((th) => (
                <div key={th.id} className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="badge bg-surface-3 text-text-3 text-[8px]">
                      {t(`thought_type_${th.thought_type}`, th.thought_type)}
                    </span>
                  </div>
                  <div className="text-[10px] text-text-2 leading-relaxed line-clamp-2">{th.content}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Relationships */}
        {Object.keys(relationships).length > 0 && (
          <div className="px-4 pt-1 pb-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Users size={10} className="text-cyan" />
              <span className="text-[9px] font-medium text-text-3 uppercase tracking-wider">
                {t('relationships')} ({Object.keys(relationships).length})
              </span>
            </div>
            <div className="space-y-1 max-h-24 overflow-y-auto">
              {Object.entries(relationships).map(([id, rel]) => {
                const r = rel as Relationship;
                const relColor = relColors[r.type] || 'text-text-3';
                return (
                  <div key={id} className="flex items-center justify-between p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <span className="text-[10px] text-text-2">{r.name || 'Unknown'}</span>
                    <div className="flex items-center gap-2">
                      <span className={`text-[9px] font-medium capitalize ${relColor}`}>
                        {t(`rel_${r.type}`, r.type)}
                      </span>
                      <span className="text-[8px] text-text-3 mono">{r.interaction_count}x</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Organizations */}
        {organizations.length > 0 && (
          <div className="px-4 pt-1 pb-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Building2 size={10} className="text-green" />
              <span className="text-[9px] font-medium text-text-3 uppercase tracking-wider">
                {t('organizations')} ({organizations.length})
              </span>
            </div>
            <div className="space-y-1 max-h-20 overflow-y-auto">
              {organizations.map((org, idx) => (
                <div key={idx} className="flex items-center justify-between p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <span className="text-[10px] text-text-2">{org.name}</span>
                  <span className="text-[9px] text-green capitalize">{org.role}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Artifacts */}
        {aiArtifacts.length > 0 && (
          <div className="px-4 pt-1 pb-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Palette size={10} className="text-cyan" />
              <span className="text-[9px] font-medium text-text-3 uppercase tracking-wider">
                {t('artifacts')} ({aiArtifacts.length})
              </span>
            </div>
            <div className="space-y-1 max-h-24 overflow-y-auto">
              {aiArtifacts.map((artifact) => (
                <div key={artifact.id} className="flex items-start gap-2 p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <span className="text-[10px] flex-shrink-0">{artifactTypeIcons[artifact.artifact_type] || '✧'}</span>
                  <div className="flex-1 min-w-0">
                    <span className="text-[10px] text-text-2 block truncate">{artifact.name}</span>
                    <span className="text-[8px] text-text-3 capitalize">{artifact.artifact_type}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Memories */}
        {selectedMemories.length > 0 && (
          <div className="px-4 pt-1 pb-3">
            <div className="text-[9px] font-medium text-text-3 uppercase tracking-wider mb-2">
              {t('memories')} ({selectedMemories.length})
            </div>
            <div className="space-y-1.5 max-h-32 overflow-y-auto">
              {selectedMemories.map((m) => (
                <div key={m.id} className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="badge bg-surface-3 text-text-3 text-[8px]">{m.memory_type}</span>
                    <ImportanceDots value={m.importance} />
                  </div>
                  <div className="text-[10px] text-text-2 leading-relaxed line-clamp-2">{m.content}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ImportanceDots({ value }: { value: number }) {
  const filled = Math.round(value * 5);
  return (
    <div className="flex gap-0.5">
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className={`w-1 h-1 rounded-full ${i < filled ? 'bg-accent' : 'bg-white/[0.06]'}`}
        />
      ))}
    </div>
  );
}

function formatKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/([a-z])([A-Z])/g, '$1 $2');
}
