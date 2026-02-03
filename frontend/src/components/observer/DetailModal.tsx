import { useTranslation } from 'react-i18next';
import {
  Brain,
  Radio,
  Palette,
  Lightbulb,
  Eye,
  BookOpen,
  MessageCircle,
} from 'lucide-react';
import DraggablePanel from '../ui/DraggablePanel';
import { useDetailStore, type DetailItemType } from '../../stores/detailStore';
import { useIsMobile } from '../../hooks/useIsMobile';
import {
  ThoughtDetail,
  EventDetail,
  InteractionDetail,
  ArtifactDetail,
  ConceptDetail,
  MemoryDetail,
  GodFeedDetail,
} from './detail/DetailPanels';

/* ═══════════════════════════════════════════════════════════
   Configuration
   ═══════════════════════════════════════════════════════════ */

const panelConfig: Record<
  DetailItemType,
  { titleKey: string; fallbackTitle: string; icon: React.ReactNode }
> = {
  thought: {
    titleKey: 'detail_thought',
    fallbackTitle: 'Thought',
    icon: <Brain size={12} className="text-accent" />,
  },
  event: {
    titleKey: 'detail_event',
    fallbackTitle: 'Event',
    icon: <Radio size={12} className="text-cyan" />,
  },
  interaction: {
    titleKey: 'detail_interaction',
    fallbackTitle: 'Interaction',
    icon: <MessageCircle size={12} className="text-rose-400" />,
  },
  artifact: {
    titleKey: 'detail_artifact',
    fallbackTitle: 'Artifact',
    icon: <Palette size={12} className="text-rose-400" />,
  },
  concept: {
    titleKey: 'detail_concept',
    fallbackTitle: 'Concept',
    icon: <Lightbulb size={12} className="text-cyan" />,
  },
  memory: {
    titleKey: 'detail_memory',
    fallbackTitle: 'Memory',
    icon: <BookOpen size={12} className="text-accent" />,
  },
  god_feed: {
    titleKey: 'detail_god',
    fallbackTitle: 'God Observation',
    icon: <Eye size={12} className="text-accent" />,
  },
};

/* ═══════════════════════════════════════════════════════════
   Main component
   ═══════════════════════════════════════════════════════════ */

export default function DetailModal() {
  const { t } = useTranslation();
  const { itemType, itemData, closeDetail } = useDetailStore();
  const isMobile = useIsMobile();

  // On mobile, MobileDetailSheet handles this
  if (isMobile) return null;
  if (!itemType || !itemData) return null;

  const config = panelConfig[itemType];
  const title = t(config.titleKey, config.fallbackTitle);

  return (
    <DraggablePanel
      title={title}
      icon={config.icon}
      visible={true}
      onClose={closeDetail}
      defaultX={Math.round(window.innerWidth / 2 - 240)}
      defaultY={Math.round(window.innerHeight * 0.1)}
      defaultWidth={480}
      defaultHeight={580}
      minWidth={340}
      minHeight={250}
      maxWidth={750}
      maxHeight={900}
    >
      <div className="p-4">
        {itemType === 'thought' && <ThoughtDetail data={itemData} t={t} />}
        {itemType === 'event' && <EventDetail data={itemData} t={t} />}
        {itemType === 'interaction' && <InteractionDetail data={itemData} t={t} />}
        {itemType === 'artifact' && <ArtifactDetail data={itemData} t={t} />}
        {itemType === 'concept' && <ConceptDetail data={itemData} t={t} />}
        {itemType === 'memory' && <MemoryDetail data={itemData} t={t} />}
        {itemType === 'god_feed' && <GodFeedDetail data={itemData} t={t} />}
      </div>
    </DraggablePanel>
  );
}
