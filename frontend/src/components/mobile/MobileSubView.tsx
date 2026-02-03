import { useTranslation } from 'react-i18next';
import { ArrowLeft } from 'lucide-react';
import ConceptPanel from '../observer/ConceptPanel';
import ArtifactPanel from '../observer/ArtifactPanel';
import GodFeed from '../observer/GodFeed';
import BoardPanel from '../observer/BoardPanel';
import MobileDetailSheet from './MobileDetailSheet';

interface Props {
  contentKey: string;
  onBack: () => void;
}

const titleKeys: Record<string, string> = {
  concepts: 'concepts',
  artifacts: 'artifacts',
  god: 'god_console',
  board: 'board_title',
};

export default function MobileSubView({ contentKey, onBack }: Props) {
  const { t } = useTranslation();

  return (
    <div className="h-screen w-screen flex flex-col bg-bg overflow-hidden">
      {/* Film grain */}
      <div className="noise-overlay" />

      {/* Header with back button */}
      <header className="flex items-center gap-3 px-4 py-3 bg-surface/90 backdrop-blur-xl border-b border-border z-50 safe-top">
        <button
          onClick={onBack}
          className="p-2 -ml-2 rounded-lg active:bg-white/[0.08] text-text-3 touch-target"
        >
          <ArrowLeft size={18} />
        </button>
        <span className="text-[14px] font-semibold text-text tracking-wide">
          {t(titleKeys[contentKey] || contentKey)}
        </span>
      </header>

      {/* Full-screen content */}
      <main className="flex-1 overflow-y-auto">
        {contentKey === 'concepts' && <ConceptPanelMobile />}
        {contentKey === 'artifacts' && <ArtifactPanelMobile />}
        {contentKey === 'god' && <GodFeedMobile />}
        {contentKey === 'board' && <BoardPanelMobile />}
      </main>

      {/* Detail sheet (shows on top when item is selected) */}
      <MobileDetailSheet />
    </div>
  );
}

// Wrapper components that render inner content in fullscreen mode
function ConceptPanelMobile() {
  return <ConceptPanel visible={true} onClose={() => {}} fullScreen />;
}

function ArtifactPanelMobile() {
  return <ArtifactPanel visible={true} onClose={() => {}} fullScreen />;
}

function GodFeedMobile() {
  return <GodFeed visible={true} onClose={() => {}} fullScreen />;
}

function BoardPanelMobile() {
  return <BoardPanel fullScreen />;
}
