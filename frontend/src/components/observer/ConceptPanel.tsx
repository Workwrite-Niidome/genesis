import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Lightbulb, X, Users } from 'lucide-react';
import { api } from '../../services/api';
import type { Concept } from '../../types/world';

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

  if (!visible) return null;

  return (
    <div className="absolute bottom-20 right-4 z-40 w-72 pointer-events-auto">
      <div className="glass rounded-2xl border border-border shadow-[0_8px_40px_rgba(0,0,0,0.5)] fade-in overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.04]">
          <div className="flex items-center gap-2">
            <Lightbulb size={12} className="text-cyan" />
            <span className="text-[10px] font-medium text-text uppercase tracking-wider">
              {t('concepts')}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-white/[0.08] text-text-3 hover:text-text transition-colors"
          >
            <X size={12} />
          </button>
        </div>

        <div className="p-2 space-y-1.5 max-h-64 overflow-y-auto">
          {concepts.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-text-3 text-[10px]">{t('no_concepts')}</p>
            </div>
          ) : (
            concepts.map((concept) => (
              <div
                key={concept.id}
                className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] font-medium text-cyan">
                    {concept.name}
                  </span>
                  <div className="flex items-center gap-1">
                    <Users size={9} className="text-text-3" />
                    <span className="text-[9px] mono text-text-3">
                      {concept.adoption_count}
                    </span>
                  </div>
                </div>
                {concept.category && (
                  <span className="inline-block px-1.5 py-0.5 rounded text-[8px] bg-accent/10 text-accent mb-1 capitalize">
                    {t(`category_${concept.category}`, concept.category)}
                  </span>
                )}
                <p className="text-[9px] text-text-2 leading-relaxed line-clamp-2">
                  {concept.definition}
                </p>
                <div className="flex items-center gap-1 mt-1">
                  <span className="text-[8px] text-text-3">T:{concept.tick_created}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
