import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Palette, Heart, Sparkles } from 'lucide-react';
import { api } from '../../services/api';
import { useDetailStore } from '../../stores/detailStore';
import type { Artifact } from '../../types/world';
import DraggablePanel from '../ui/DraggablePanel';
import { PixelArtThumb } from '../media/PixelArt';

const typeIcons: Record<string, string> = {
  art: '🎨', story: '📖', law: '⚖️', currency: '💰', song: '🎵',
  architecture: '🏛️', tool: '🔧', ritual: '🕯️', game: '🎲', code: '💻',
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
  code: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
};

const ARTIFACT_TYPES = ['all', 'art', 'song', 'story', 'tool', 'architecture', 'law', 'code', 'ritual', 'game', 'currency'] as const;

interface Props {
  visible: boolean;
  onClose: () => void;
  fullScreen?: boolean;
}

export default function ArtifactPanel({ visible, onClose, fullScreen }: Props) {
  const { t } = useTranslation();
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [typeFilter, setTypeFilter] = useState<string>('all');

  useEffect(() => {
    if (!visible) return;
    const load = () => {
      api.artifacts.list({}).then(setArtifacts).catch(console.error);
    };
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, [visible]);

  const filteredArtifacts = typeFilter === 'all'
    ? artifacts
    : artifacts.filter((a) => a.artifact_type === typeFilter);

  // Get counts per type for tabs
  const typeCounts = artifacts.reduce((acc, a) => {
    acc[a.artifact_type] = (acc[a.artifact_type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const content = (
    <div className={`flex flex-col ${fullScreen ? 'h-full' : ''}`}>
      {/* Type filter tabs */}
      <div className="flex items-center gap-1 px-3 py-2 border-b border-border overflow-x-auto flex-shrink-0">
        {ARTIFACT_TYPES.map((type) => {
          const count = type === 'all' ? artifacts.length : (typeCounts[type] || 0);
          if (type !== 'all' && count === 0) return null;
          return (
            <button
              key={type}
              onClick={() => setTypeFilter(type)}
              className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] whitespace-nowrap transition-all ${
                typeFilter === type
                  ? 'bg-white/[0.08] text-text'
                  : 'text-text-3 hover:text-text-2'
              }`}
            >
              {type !== 'all' && <span>{typeIcons[type] || '✧'}</span>}
              <span className="capitalize">{type === 'all' ? 'All' : type}</span>
              {count > 0 && <span className="text-[9px] text-text-3">({count})</span>}
            </button>
          );
        })}
      </div>

      {/* Artifact list */}
      <div className={`overflow-y-auto p-2 space-y-1.5 ${fullScreen ? 'flex-1' : ''}`}>
        {filteredArtifacts.length === 0 ? (
          <div className="text-center py-6">
            <Sparkles size={16} className="mx-auto mb-2 text-text-3 opacity-40" />
            <p className="text-text-3 text-[11px]">No artifacts created yet</p>
            <p className="text-text-3 text-[10px] mt-1 opacity-60">AIs will create art, stories, laws, and more</p>
          </div>
        ) : (
          filteredArtifacts.map((artifact) => {
            const icon = typeIcons[artifact.artifact_type] || '✧';
            const colorClass = typeColors[artifact.artifact_type] || 'bg-white/[0.05] text-text-2 border-white/[0.08]';
            return (
              <button
                key={artifact.id}
                onClick={() => useDetailStore.getState().openDetail('artifact', artifact)}
                className="w-full text-left p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-colors cursor-pointer touch-target"
              >
                <div className="flex items-start gap-2.5">
                  {artifact.artifact_type === 'art' ? (
                    <div className="flex-shrink-0 mt-0.5">
                      <PixelArtThumb artifact={artifact} />
                    </div>
                  ) : (
                    <span className="text-lg flex-shrink-0 mt-0.5">{icon}</span>
                  )}
                  <div className="flex-1 min-w-0">
                    <span className="text-[12px] font-medium text-text truncate block mb-1">
                      {artifact.name}
                    </span>
                    <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] border mb-1.5 capitalize ${colorClass}`}>
                      {artifact.artifact_type}
                    </span>
                    <p className="text-[11px] text-text-2 leading-relaxed line-clamp-3">
                      {artifact.description}
                    </p>
                    <div className="flex items-center gap-3 mt-2">
                      <div className="flex items-center gap-1">
                        <Heart size={9} className="text-rose-400" />
                        <span className="text-[9px] text-text-3 mono">{artifact.appreciation_count}</span>
                      </div>
                      <span className="text-[9px] text-text-3">T:{artifact.tick_created}</span>
                    </div>
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );

  if (fullScreen) return content;

  return (
    <DraggablePanel
      title="Artifacts"
      icon={<Palette size={12} className="text-rose-400" />}
      visible={visible}
      onClose={onClose}
      defaultX={20}
      defaultY={160}
      defaultWidth={340}
      defaultHeight={450}
      minWidth={280}
      minHeight={200}
      headerExtra={
        artifacts.length > 0 ? (
          <span className="text-[10px] text-text-3 mono mr-1">{artifacts.length}</span>
        ) : undefined
      }
    >
      {content}
    </DraggablePanel>
  );
}
