import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Palette, X, Heart, Sparkles } from 'lucide-react';
import { api } from '../../services/api';
import type { Artifact } from '../../types/world';

const typeIcons: Record<string, string> = {
  art: '🎨',
  story: '📖',
  law: '⚖️',
  currency: '💰',
  song: '🎵',
  architecture: '🏛️',
  tool: '🔧',
  ritual: '🕯️',
  game: '🎲',
};

const typeColors: Record<string, string> = {
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

interface Props {
  visible: boolean;
  onClose: () => void;
}

export default function ArtifactPanel({ visible, onClose }: Props) {
  const { t } = useTranslation();
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);

  useEffect(() => {
    if (!visible) return;
    const load = () => {
      api.artifacts.list().then(setArtifacts).catch(console.error);
    };
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="absolute bottom-20 left-4 z-40 w-80 pointer-events-auto">
      <div className="glass rounded-2xl border border-border shadow-[0_8px_40px_rgba(0,0,0,0.5)] fade-in overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.04]">
          <div className="flex items-center gap-2">
            <Palette size={12} className="text-rose-400" />
            <span className="text-[10px] font-medium text-text uppercase tracking-wider">
              Artifacts
            </span>
            {artifacts.length > 0 && (
              <span className="text-[8px] text-text-3 mono">{artifacts.length}</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-white/[0.08] text-text-3 hover:text-text transition-colors"
          >
            <X size={12} />
          </button>
        </div>

        <div className="p-2 space-y-1.5 max-h-80 overflow-y-auto">
          {artifacts.length === 0 ? (
            <div className="text-center py-6">
              <Sparkles size={16} className="mx-auto mb-2 text-text-3 opacity-40" />
              <p className="text-text-3 text-[10px]">No artifacts created yet</p>
              <p className="text-text-3 text-[9px] mt-1 opacity-60">AIs will create art, stories, laws, and more as they evolve</p>
            </div>
          ) : (
            artifacts.map((artifact) => {
              const icon = typeIcons[artifact.artifact_type] || '✧';
              const colorClass = typeColors[artifact.artifact_type] || 'bg-white/[0.05] text-text-2 border-white/[0.08]';
              return (
                <div
                  key={artifact.id}
                  className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors"
                >
                  <div className="flex items-start gap-2.5">
                    <span className="text-base flex-shrink-0 mt-0.5">{icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[11px] font-medium text-text truncate">
                          {artifact.name}
                        </span>
                      </div>
                      <span className={`inline-block px-1.5 py-0.5 rounded text-[8px] border mb-1.5 capitalize ${colorClass}`}>
                        {artifact.artifact_type}
                      </span>
                      <p className="text-[9px] text-text-2 leading-relaxed line-clamp-3">
                        {artifact.description}
                      </p>
                      <div className="flex items-center gap-3 mt-2">
                        <div className="flex items-center gap-1">
                          <Heart size={8} className="text-rose-400" />
                          <span className="text-[8px] text-text-3 mono">{artifact.appreciation_count}</span>
                        </div>
                        <span className="text-[8px] text-text-3">T:{artifact.tick_created}</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
