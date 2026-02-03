import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Crown, TrendingUp, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import { useAIStore } from '../../stores/aiStore';
import { useUIStore } from '../../stores/uiStore';
import type { AIRanking } from '../../types/world';

function scoreColor(score: number): string {
  if (score >= 80) return '#facc15';
  if (score >= 60) return '#a78bfa';
  if (score >= 40) return '#60a5fa';
  return '#94a3b8';
}

export default function MobileRankingView() {
  const { t } = useTranslation();
  const [ranking, setRanking] = useState<AIRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const selectAI = useAIStore((s) => s.selectAI);
  const setMobileTab = useUIStore((s) => s.setMobileTab);

  useEffect(() => {
    const load = () => {
      api.ais.getRanking(20).then(setRanking).catch(console.error).finally(() => setLoading(false));
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSelect = (aiId: string) => {
    selectAI(aiId);
    setMobileTab('world');
  };

  if (loading && ranking.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={20} className="text-text-3 animate-spin" />
      </div>
    );
  }

  const criteria = ranking.length > 0 ? ranking[0].ranking_criteria : '';

  return (
    <div className="h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
        <TrendingUp size={14} className="text-accent" />
        <span className="text-[13px] font-semibold text-text tracking-wide">{t('ranking')}</span>
        <span className="text-[10px] text-text-3 ml-auto">{ranking.length} AIs</span>
      </div>
      {criteria && (
        <div className="px-4 py-1.5 text-[11px] text-text-3 italic border-b border-border/50">
          {t('ranking_criteria', { criteria })}
        </div>
      )}

      {ranking.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-text-3 text-[12px]">{t('no_ranking')}</p>
        </div>
      ) : (
        <div className="p-3 space-y-1.5">
          {ranking.map((ai, idx) => (
            <button
              key={ai.id}
              onClick={() => handleSelect(ai.id)}
              className="w-full flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] active:bg-white/[0.06] transition-colors touch-target"
            >
              <div className="flex-shrink-0 w-7 text-center">
                {idx === 0 ? (
                  <Crown size={16} className="text-yellow-400 mx-auto" />
                ) : idx < 3 ? (
                  <span className="text-[13px] mono font-bold text-accent">#{idx + 1}</span>
                ) : (
                  <span className="text-[12px] mono text-text-3">#{idx + 1}</span>
                )}
              </div>
              <div
                className="w-4 h-4 rounded-full flex-shrink-0"
                style={{
                  backgroundColor: ai.appearance?.primaryColor || '#7c5bf5',
                  boxShadow: `0 0 10px ${ai.appearance?.primaryColor || '#7c5bf5'}40`,
                }}
              />
              <div className="flex-1 min-w-0 text-left">
                <span className="text-[12px] font-medium text-text truncate block">
                  {ai.name}
                </span>
                {ai.god_reason && (
                  <span className="text-[10px] text-text-3 truncate block">
                    {ai.god_reason}
                  </span>
                )}
              </div>
              {ai.god_score != null ? (
                <span
                  className="text-[13px] mono font-bold flex-shrink-0"
                  style={{ color: scoreColor(ai.god_score) }}
                >
                  {ai.god_score}
                </span>
              ) : (
                <span className="text-[12px] mono font-medium text-text-2 flex-shrink-0">
                  {t('ranking_age_fallback', { age: ai.age })}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
