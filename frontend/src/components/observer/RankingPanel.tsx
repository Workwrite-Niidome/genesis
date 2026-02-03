import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { TrendingUp, Crown } from 'lucide-react';
import { api } from '../../services/api';
import { useAIStore } from '../../stores/aiStore';
import type { AIRanking } from '../../types/world';
import DraggablePanel from '../ui/DraggablePanel';

interface Props {
  visible: boolean;
  onClose: () => void;
}

function scoreColor(score: number): string {
  if (score >= 80) return '#facc15';
  if (score >= 60) return '#a78bfa';
  if (score >= 40) return '#60a5fa';
  return '#94a3b8';
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

  const criteria = ranking.length > 0 ? ranking[0].ranking_criteria : '';

  return (
    <DraggablePanel
      title={t('ranking')}
      icon={<TrendingUp size={12} className="text-accent" />}
      visible={visible}
      onClose={onClose}
      defaultX={20}
      defaultY={140}
      defaultWidth={300}
      defaultHeight={400}
      minWidth={240}
      minHeight={200}
    >
      <div className="p-2 space-y-1">
        {criteria && (
          <div className="text-[10px] text-text-3 px-1 pb-1 italic">
            {t('ranking_criteria', { criteria })}
          </div>
        )}
        {ranking.length === 0 ? (
          <div className="text-center py-4">
            <p className="text-text-3 text-[11px]">{t('no_ranking')}</p>
          </div>
        ) : (
          ranking.map((ai, idx) => (
            <button
              key={ai.id}
              onClick={() => selectAI(ai.id)}
              className="w-full flex items-center gap-2 p-2 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] transition-colors text-left group"
              title={ai.god_reason || undefined}
            >
              <div className="flex-shrink-0 w-5 text-center">
                {idx === 0 ? (
                  <Crown size={12} className="text-yellow-400 mx-auto" />
                ) : (
                  <span className="text-[11px] mono text-text-3">#{idx + 1}</span>
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
                <span className="text-[11px] font-medium text-text truncate block">
                  {ai.name}
                </span>
                {ai.god_reason && (
                  <span className="text-[9px] text-text-3 truncate block">
                    {ai.god_reason}
                  </span>
                )}
              </div>
              {ai.god_score != null ? (
                <span
                  className="text-[11px] mono font-bold flex-shrink-0"
                  style={{ color: scoreColor(ai.god_score) }}
                >
                  {ai.god_score}
                </span>
              ) : (
                <span className="text-[11px] mono font-medium text-text-2 flex-shrink-0">
                  {t('ranking_age_fallback', { age: ai.age })}
                </span>
              )}
            </button>
          ))
        )}
      </div>
    </DraggablePanel>
  );
}
