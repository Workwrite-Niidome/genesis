import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { TrendingUp, Crown, X } from 'lucide-react';
import { api } from '../../services/api';
import { useAIStore } from '../../stores/aiStore';
import type { AIRanking } from '../../types/world';

interface Props {
  visible: boolean;
  onClose: () => void;
}

export default function RankingPanel({ visible, onClose }: Props) {
  const { t } = useTranslation();
  const [ranking, setRanking] = useState<AIRanking[]>([]);
  const selectAI = useAIStore((s) => s.selectAI);

  useEffect(() => {
    if (!visible) return;
    const load = () => {
      api.ais.getRanking(10).then(setRanking).catch(console.error);
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="absolute bottom-20 left-4 z-40 w-72 pointer-events-auto">
      <div className="glass rounded-2xl border border-border shadow-[0_8px_40px_rgba(0,0,0,0.5)] fade-in overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.04]">
          <div className="flex items-center gap-2">
            <TrendingUp size={12} className="text-accent" />
            <span className="text-[10px] font-medium text-text uppercase tracking-wider">
              {t('ranking')}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-white/[0.08] text-text-3 hover:text-text transition-colors"
          >
            <X size={12} />
          </button>
        </div>

        <div className="p-2 space-y-1 max-h-64 overflow-y-auto">
          {ranking.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-text-3 text-[10px]">{t('no_ranking')}</p>
            </div>
          ) : (
            ranking.map((ai, idx) => (
              <button
                key={ai.id}
                onClick={() => selectAI(ai.id)}
                className="w-full flex items-center gap-2 p-2 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] transition-colors text-left"
              >
                <div className="flex-shrink-0 w-5 text-center">
                  {idx === 0 ? (
                    <Crown size={12} className="text-yellow-400 mx-auto" />
                  ) : (
                    <span className="text-[10px] mono text-text-3">#{idx + 1}</span>
                  )}
                </div>
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{
                    backgroundColor: ai.appearance?.primaryColor || '#7c5bf5',
                    boxShadow: `0 0 8px ${ai.appearance?.primaryColor || '#7c5bf5'}40`,
                  }}
                />
                <div className="flex-1 min-w-0">
                  <span className="text-[10px] font-medium text-text truncate block">
                    {ai.name}
                  </span>
                </div>
                <span className="text-[10px] mono font-medium text-accent flex-shrink-0">
                  {ai.evolution_score.toFixed(1)}
                </span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
