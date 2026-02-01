import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { TrendingUp, Lightbulb, Eye, Palette, ScrollText, BookOpen } from 'lucide-react';
import WorldCanvas from '../components/world/WorldCanvas';
import ObserverHeader from '../components/observer/ObserverHeader';
import AIDetailCard from '../components/observer/AIDetailCard';
import BoardPanel from '../components/observer/BoardPanel';
import ObserverFeed from '../components/observer/ObserverFeed';
import DeployPanel from '../components/observer/DeployPanel';
import RankingPanel from '../components/observer/RankingPanel';
import ConceptPanel from '../components/observer/ConceptPanel';
import ArtifactPanel from '../components/observer/ArtifactPanel';
import GodFeed from '../components/observer/GodFeed';
import WorldArchive from '../components/observer/WorldArchive';
import { useUIStore } from '../stores/uiStore';
import { useSagaStore } from '../stores/sagaStore';

export default function ObserverView() {
  const { t } = useTranslation();
  const [showRanking, setShowRanking] = useState(false);
  const [showConcepts, setShowConcepts] = useState(false);
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [showGodFeed, setShowGodFeed] = useState(false);
  const { showArchive, toggleArchive, observerChatExpanded } = useUIStore();
  const { hasNewChapter } = useSagaStore();

  return (
    <div className="h-screen w-screen relative bg-bg overflow-hidden">
      {/* Film grain */}
      <div className="noise-overlay" />

      {/* Full-bleed 3D canvas */}
      <div className="absolute inset-0">
        <WorldCanvas showGenesis={false} />
      </div>

      {/* Floating overlays — pointer-events-none container so clicks pass to canvas */}
      <div className="absolute inset-0 pointer-events-none z-30">
        <ObserverHeader />
        <AIDetailCard />
        <ObserverFeed />
        <RankingPanel visible={showRanking} onClose={() => setShowRanking(false)} />
        <ConceptPanel visible={showConcepts} onClose={() => setShowConcepts(false)} />
        <ArtifactPanel visible={showArtifacts} onClose={() => setShowArtifacts(false)} />
        <GodFeed visible={showGodFeed} onClose={() => setShowGodFeed(false)} />
        <WorldArchive visible={showArchive} onClose={toggleArchive} />
      </div>

      {/* Panel toggle buttons — above board, z-50 */}
      <div
        className={`absolute left-1/2 -translate-x-1/2 flex gap-2 z-50 transition-all duration-200 ${
          observerChatExpanded ? 'bottom-[340px]' : 'bottom-[56px]'
        }`}
      >
        <button
          onClick={() => setShowRanking(!showRanking)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-medium transition-all ${
            showRanking
              ? 'bg-accent/20 text-accent border border-accent/30'
              : 'glass border border-border text-text-3 hover:text-text hover:border-white/[0.1]'
          }`}
        >
          <TrendingUp size={12} />
          Ranking
        </button>
        <button
          onClick={() => setShowConcepts(!showConcepts)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-medium transition-all ${
            showConcepts
              ? 'bg-cyan/20 text-cyan border border-cyan/30'
              : 'glass border border-border text-text-3 hover:text-text hover:border-white/[0.1]'
          }`}
        >
          <Lightbulb size={12} />
          Concepts
        </button>
        <button
          onClick={() => setShowArtifacts(!showArtifacts)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-medium transition-all ${
            showArtifacts
              ? 'bg-rose-400/20 text-rose-400 border border-rose-400/30'
              : 'glass border border-border text-text-3 hover:text-text hover:border-white/[0.1]'
          }`}
        >
          <Palette size={12} />
          Artifacts
        </button>
        <button
          onClick={() => setShowGodFeed(!showGodFeed)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-medium transition-all ${
            showGodFeed
              ? 'bg-accent/20 text-accent border border-accent/30'
              : 'glass border border-border text-text-3 hover:text-text hover:border-white/[0.1]'
          }`}
        >
          <Eye size={12} />
          God
        </button>
        <button
          onClick={toggleArchive}
          className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-medium transition-all ${
            showArchive
              ? 'text-text border'
              : 'glass border border-border text-text-3 hover:text-text hover:border-white/[0.1]'
          }`}
          style={showArchive ? { backgroundColor: 'rgba(212,165,116,0.2)', borderColor: 'rgba(212,165,116,0.3)', color: '#d4a574' } : undefined}
        >
          <BookOpen size={12} />
          {t('saga_tab')} / Archive
          {hasNewChapter && (
            <span
              className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full animate-pulse"
              style={{ backgroundColor: '#d4a574' }}
            />
          )}
        </button>
      </div>

      {/* Board panel at bottom — z-40 */}
      <div className="absolute inset-0 pointer-events-none z-40">
        <BoardPanel />
      </div>

      {/* Deploy modal (manages its own visibility) */}
      <DeployPanel />
    </div>
  );
}
