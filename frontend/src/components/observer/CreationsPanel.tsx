import { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Palette, Lightbulb, Heart, Users, Filter,
  Sparkles, Building2, User
} from 'lucide-react';
import { api } from '../../services/api';
import { useDetailStore } from '../../stores/detailStore';
import type { Artifact, Concept } from '../../types/world';
import DraggablePanel from '../ui/DraggablePanel';
import { PixelArtThumb } from '../media/PixelArt';

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

const conceptCategories = [
  'philosophy', 'religion', 'government', 'economy',
  'art', 'technology', 'social_norm', 'organization'
];

interface Props {
  visible: boolean;
  onClose: () => void;
}

type TabType = 'all' | 'artifacts' | 'concepts';
type SortType = 'newest' | 'popular';

export default function CreationsPanel({ visible, onClose }: Props) {
  const { t } = useTranslation();
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [tab, setTab] = useState<TabType>('all');
  const [sort, setSort] = useState<SortType>('newest');
  const [filterType, setFilterType] = useState<string>('');
  const [filterCreator, setFilterCreator] = useState<string>('');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    if (!visible) return;
    const load = () => {
      api.artifacts.list({}).then(setArtifacts).catch(console.error);
      api.concepts.list({}).then(setConcepts).catch(console.error);
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [visible]);

  // Get unique creators from both artifacts and concepts
  const creators = useMemo(() => {
    const map = new Map<string, string>();
    artifacts.forEach(a => {
      if (a.creator_id && a.creator_name) map.set(a.creator_id, a.creator_name);
    });
    concepts.forEach(c => {
      if (c.creator_id && c.creator_name) map.set(c.creator_id, c.creator_name);
    });
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [artifacts, concepts]);

  // Get unique types
  const artifactTypes = useMemo(() => {
    return [...new Set(artifacts.map(a => a.artifact_type))].sort();
  }, [artifacts]);

  // Filter and sort
  const filteredItems = useMemo(() => {
    let items: (Artifact | Concept & { _type: 'artifact' | 'concept' })[] = [];

    if (tab === 'all' || tab === 'artifacts') {
      const filteredArtifacts = artifacts
        .filter(a => !filterType || a.artifact_type === filterType)
        .filter(a => !filterCreator || a.creator_id === filterCreator)
        .map(a => ({ ...a, _type: 'artifact' as const }));
      items = items.concat(filteredArtifacts);
    }

    if (tab === 'all' || tab === 'concepts') {
      const filteredConcepts = concepts
        .filter(c => !filterType || c.category === filterType)
        .filter(c => !filterCreator || c.creator_id === filterCreator)
        .map(c => ({ ...c, _type: 'concept' as const }));
      items = items.concat(filteredConcepts);
    }

    // Sort
    if (sort === 'newest') {
      items.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    } else {
      items.sort((a, b) => {
        const aScore = '_type' in a && a._type === 'artifact'
          ? (a as unknown as Artifact).appreciation_count
          : (a as unknown as Concept).adoption_count;
        const bScore = '_type' in b && b._type === 'artifact'
          ? (b as unknown as Artifact).appreciation_count
          : (b as unknown as Concept).adoption_count;
        return bScore - aScore;
      });
    }

    return items;
  }, [artifacts, concepts, tab, filterType, filterCreator, sort]);

  const renderArtifact = (artifact: Artifact) => {
    const icon = artifactTypeIcons[artifact.artifact_type] || '✧';
    const colorClass = artifactTypeColors[artifact.artifact_type] || 'bg-white/[0.05] text-text-2 border-white/[0.08]';
    return (
      <button
        key={`a-${artifact.id}`}
        onClick={() => useDetailStore.getState().openDetail('artifact', artifact)}
        className="w-full text-left p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-colors cursor-pointer"
      >
        <div className="flex items-start gap-2">
          {artifact.artifact_type === 'art' ? (
            <div className="flex-shrink-0 mt-0.5">
              <PixelArtThumb artifact={artifact} />
            </div>
          ) : (
            <span className="text-base flex-shrink-0 mt-0.5">{icon}</span>
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-0.5">
              <Palette size={10} className="text-rose-400 flex-shrink-0" />
              <span className="text-[11px] font-medium text-text truncate">
                {artifact.name}
              </span>
            </div>
            <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] border mb-1 capitalize ${colorClass}`}>
              {artifact.artifact_type}
            </span>
            <p className="text-[10px] text-text-2 leading-relaxed line-clamp-2">
              {artifact.description}
            </p>
            <div className="flex items-center gap-2 mt-1.5 text-[9px] text-text-3">
              {artifact.creator_name && (
                <span className="flex items-center gap-0.5">
                  <User size={8} />
                  {artifact.creator_name}
                </span>
              )}
              <span className="flex items-center gap-0.5">
                <Heart size={8} className="text-rose-400" />
                {artifact.appreciation_count}
              </span>
              <span>T:{artifact.tick_created}</span>
            </div>
          </div>
        </div>
      </button>
    );
  };

  const renderConcept = (concept: Concept) => {
    const isOrg = concept.category === 'organization';
    return (
      <button
        key={`c-${concept.id}`}
        onClick={() => useDetailStore.getState().openDetail('concept', concept)}
        className="w-full text-left p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-1.5 mb-0.5">
          {isOrg ? (
            <Building2 size={10} className="text-green-400 flex-shrink-0" />
          ) : (
            <Lightbulb size={10} className="text-cyan flex-shrink-0" />
          )}
          <span className={`text-[11px] font-medium ${isOrg ? 'text-green-400' : 'text-cyan'} truncate`}>
            {concept.name}
          </span>
        </div>
        <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] mb-1 capitalize ${
          isOrg ? 'bg-green-500/10 text-green-400' : 'bg-accent/10 text-accent'
        }`}>
          {t(`category_${concept.category}`, concept.category)}
        </span>
        <p className="text-[10px] text-text-2 leading-relaxed line-clamp-2">
          {concept.definition}
        </p>
        <div className="flex items-center gap-2 mt-1.5 text-[9px] text-text-3">
          {concept.creator_name && (
            <span className="flex items-center gap-0.5">
              <User size={8} />
              {concept.creator_name}
            </span>
          )}
          <span className="flex items-center gap-0.5">
            <Users size={8} />
            {concept.adoption_count}
          </span>
          <span>T:{concept.tick_created}</span>
        </div>
      </button>
    );
  };

  return (
    <DraggablePanel
      title={t('creations', 'Creations')}
      icon={<Sparkles size={12} className="text-amber-400" />}
      visible={visible}
      onClose={onClose}
      defaultX={20}
      defaultY={160}
      defaultWidth={360}
      defaultHeight={500}
      minWidth={300}
      minHeight={250}
      headerExtra={
        <span className="text-[10px] text-text-3 mono mr-1">
          {filteredItems.length}
        </span>
      }
    >
      <div className="flex flex-col h-full">
        {/* Tabs */}
        <div className="flex items-center gap-1 p-2 border-b border-white/[0.04]">
          {(['all', 'artifacts', 'concepts'] as TabType[]).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setFilterType(''); }}
              className={`px-2 py-1 rounded text-[10px] transition-colors ${
                tab === t
                  ? 'bg-white/[0.08] text-text'
                  : 'text-text-3 hover:text-text-2'
              }`}
            >
              {t === 'all' ? 'All' : t === 'artifacts' ? 'Artifacts' : 'Concepts'}
            </button>
          ))}
          <div className="flex-1" />
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-1 rounded transition-colors ${
              showFilters || filterType || filterCreator
                ? 'bg-accent/20 text-accent'
                : 'text-text-3 hover:text-text-2'
            }`}
          >
            <Filter size={12} />
          </button>
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="p-2 border-b border-white/[0.04] space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-text-3 w-12">Type:</span>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="flex-1 bg-white/[0.05] border border-white/[0.08] rounded px-2 py-1 text-[10px] text-text"
              >
                <option value="">All</option>
                {tab !== 'concepts' && artifactTypes.map(t => (
                  <option key={t} value={t}>{artifactTypeIcons[t] || ''} {t}</option>
                ))}
                {tab !== 'artifacts' && conceptCategories.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-text-3 w-12">Creator:</span>
              <select
                value={filterCreator}
                onChange={(e) => setFilterCreator(e.target.value)}
                className="flex-1 bg-white/[0.05] border border-white/[0.08] rounded px-2 py-1 text-[10px] text-text"
              >
                <option value="">All</option>
                {creators.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-text-3 w-12">Sort:</span>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortType)}
                className="flex-1 bg-white/[0.05] border border-white/[0.08] rounded px-2 py-1 text-[10px] text-text"
              >
                <option value="newest">Newest</option>
                <option value="popular">Most Popular</option>
              </select>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
          {filteredItems.length === 0 ? (
            <div className="text-center py-8">
              <Sparkles size={16} className="mx-auto mb-2 text-text-3 opacity-40" />
              <p className="text-text-3 text-[11px]">No creations yet</p>
              <p className="text-text-3 text-[10px] mt-1 opacity-60">
                AIs will create concepts, art, stories, and more
              </p>
            </div>
          ) : (
            filteredItems.map((item) => {
              if ('_type' in item && item._type === 'artifact') {
                return renderArtifact(item as unknown as Artifact);
              } else {
                return renderConcept(item as Concept);
              }
            })
          )}
        </div>
      </div>
    </DraggablePanel>
  );
}
