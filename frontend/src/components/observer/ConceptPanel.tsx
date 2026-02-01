import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Lightbulb, Users } from 'lucide-react';
import { api } from '../../services/api';
import { useDetailStore } from '../../stores/detailStore';
import type { Concept } from '../../types/world';
import DraggablePanel from '../ui/DraggablePanel';

interface Props {
  visible: boolean;
  onClose: () => void;
}

export default function ConceptPanel({ visible, onClose }: Props) {
  const { t } = useTranslation();
  const [concepts, setConcepts] = useState<Concept[]>([]);

  useEffect(() => {
    if (!visible) return;
    const load = () => {
      api.concepts.list().then(setConcepts).catch(console.error);
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [visible]);

  return (
    <DraggablePanel
      title={t('concepts')}
      icon={<Lightbulb size={12} className="text-cyan" />}
      visible={visible}
      onClose={onClose}
      defaultX={340}
      defaultY={140}
      defaultWidth={300}
      defaultHeight={400}
      minWidth={240}
      minHeight={200}
    >
      <div className="p-2 space-y-1.5">
        {concepts.length === 0 ? (
          <div className="text-center py-4">
            <p className="text-text-3 text-[11px]">{t('no_concepts')}</p>
          </div>
        ) : (
          concepts.map((concept) => (
            <button
              key={concept.id}
              onClick={() => useDetailStore.getState().openDetail('concept', concept)}
              className="w-full text-left p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[12px] font-medium text-cyan">
                  {concept.name}
                </span>
                <div className="flex items-center gap-1">
                  <Users size={10} className="text-text-3" />
                  <span className="text-[10px] mono text-text-3">
                    {concept.adoption_count}
                  </span>
                </div>
              </div>
              {concept.category && (
                <span className="inline-block px-1.5 py-0.5 rounded text-[9px] bg-accent/10 text-accent mb-1 capitalize">
                  {t(`category_${concept.category}`, concept.category)}
                </span>
              )}
              <p className="text-[11px] text-text-2 leading-relaxed line-clamp-2">
                {concept.definition}
              </p>
              <div className="flex items-center gap-1 mt-1">
                <span className="text-[9px] text-text-3">T:{concept.tick_created}</span>
              </div>
            </button>
          ))
        )}
      </div>
    </DraggablePanel>
  );
}
