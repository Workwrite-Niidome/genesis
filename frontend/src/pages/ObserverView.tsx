import { useState } from 'react';
import { TrendingUp, Lightbulb, Eye, Palette } from 'lucide-react';
import WorldCanvas from '../components/world/WorldCanvas';
import ObserverHeader from '../components/observer/ObserverHeader';
import AIDetailCard from '../components/observer/AIDetailCard';
import ObserverChat from '../components/observer/ObserverChat';
import ObserverFeed from '../components/observer/ObserverFeed';
import DeployPanel from '../components/observer/DeployPanel';
import RankingPanel from '../components/observer/RankingPanel';
import ConceptPanel from '../components/observer/ConceptPanel';
import ArtifactPanel from '../components/observer/ArtifactPanel';
import GodFeed from '../components/observer/GodFeed';

export default function ObserverView() {
  const [showRanking, setShowRanking] = useState(false);
  const [showConcepts, setShowConcepts] = useState(false);
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [showGodFeed, setShowGodFeed] = useState(false);

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
        <ObserverChat />
        <RankingPanel visible={showRanking} onClose={() => setShowRanking(false)} />
        <ConceptPanel visible={showConcepts} onClose={() => setShowConcepts(false)} />
        <ArtifactPanel visible={showArtifacts} onClose={() => setShowArtifacts(false)} />
        <GodFeed visible={showGodFeed} onClose={() => setShowGodFeed(false)} />

        {/* Panel toggle buttons */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 pointer-events-auto">
          <button
            onClick={() => setShowRanking(!showRanking)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-medium transition-all ${
              showRanking
                ? 'bg-accent/20 text-accent border border-accent/30'
                : 'glass border border-border text-text-3 hover:text-text hover:border-white/[0.1]'
            }`}
          >
            <TrendingUp size={11} />
            Ranking
          </button>
          <button
            onClick={() => setShowConcepts(!showConcepts)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-medium transition-all ${
              showConcepts
                ? 'bg-cyan/20 text-cyan border border-cyan/30'
                : 'glass border border-border text-text-3 hover:text-text hover:border-white/[0.1]'
            }`}
          >
            <Lightbulb size={11} />
            Concepts
          </button>
          <button
            onClick={() => setShowArtifacts(!showArtifacts)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-medium transition-all ${
              showArtifacts
                ? 'bg-rose-400/20 text-rose-400 border border-rose-400/30'
                : 'glass border border-border text-text-3 hover:text-text hover:border-white/[0.1]'
            }`}
          >
            <Palette size={11} />
            Artifacts
          </button>
          <button
            onClick={() => setShowGodFeed(!showGodFeed)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-medium transition-all ${
              showGodFeed
                ? 'bg-accent/20 text-accent border border-accent/30'
                : 'glass border border-border text-text-3 hover:text-text hover:border-white/[0.1]'
            }`}
          >
            <Eye size={11} />
            God
          </button>
        </div>
      </div>

      {/* Deploy modal (manages its own visibility) */}
      <DeployPanel />
    </div>
  );
}
