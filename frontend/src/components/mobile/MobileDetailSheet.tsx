import { useTranslation } from 'react-i18next';
import { ArrowLeft } from 'lucide-react';
import { useDetailStore, type DetailItemType } from '../../stores/detailStore';
import {
  ThoughtDetail,
  EventDetail,
  InteractionDetail,
  ArtifactDetail,
  ConceptDetail,
  MemoryDetail,
  GodFeedDetail,
} from '../observer/detail/DetailPanels';

const titleKeys: Record<DetailItemType, string> = {
  thought: 'detail_thought',
  event: 'detail_event',
  interaction: 'detail_interaction',
  artifact: 'detail_artifact',
  concept: 'detail_concept',
  memory: 'detail_memory',
  god_feed: 'detail_god',
};

export default function MobileDetailSheet() {
  const { t } = useTranslation();
  const { itemType, itemData, closeDetail } = useDetailStore();

  if (!itemType || !itemData) return null;

  const title = t(titleKeys[itemType] || 'Details');

  return (
    <div className="fixed inset-0 z-[200] flex flex-col bg-bg">
      {/* Film grain */}
      <div className="noise-overlay" />

      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-3 bg-surface/95 backdrop-blur-xl border-b border-border safe-top flex-shrink-0">
        <button
          onClick={closeDetail}
          className="p-2 -ml-2 rounded-lg active:bg-white/[0.08] text-text-3 touch-target"
        >
          <ArrowLeft size={18} />
        </button>
        <span className="text-[14px] font-semibold text-text tracking-wide">
          {title}
        </span>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-4 safe-bottom">
        {itemType === 'thought' && <ThoughtDetail data={itemData} t={t} />}
        {itemType === 'event' && <EventDetail data={itemData} t={t} />}
        {itemType === 'interaction' && <InteractionDetail data={itemData} t={t} />}
        {itemType === 'artifact' && <ArtifactDetail data={itemData} t={t} />}
        {itemType === 'concept' && <ConceptDetail data={itemData} t={t} />}
        {itemType === 'memory' && <MemoryDetail data={itemData} t={t} />}
        {itemType === 'god_feed' && <GodFeedDetail data={itemData} t={t} />}
      </main>
    </div>
  );
}
