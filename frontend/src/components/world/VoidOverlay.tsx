import { useTranslation } from 'react-i18next';
import { useWorldStore } from '../../stores/worldStore';
import { api } from '../../services/api';
import { useState } from 'react';

export default function VoidOverlay() {
  const { t } = useTranslation();
  const { godAiPhase, fetchState } = useWorldStore();
  const [loading, setLoading] = useState(false);
  const [genesisText, setGenesisText] = useState<string | null>(null);

  if (godAiPhase !== 'pre_genesis') return null;

  const handleGenesis = async () => {
    setLoading(true);
    try {
      const result = await api.world.genesis();
      if (result.success) {
        setGenesisText(result.god_response);
        setTimeout(fetchState, 6000);
      }
    } catch (e) {
      console.error('Genesis failed:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="absolute inset-0 flex items-center justify-center z-30">
      <div className="text-center max-w-md mx-auto px-6">
        {!genesisText ? (
          <div className="fade-in">
            {/* Void symbol */}
            <div className="relative w-20 h-20 mx-auto mb-8">
              <div className="absolute inset-0 rounded-full border border-accent/20 pulse-glow" />
              <div className="absolute inset-2 rounded-full border border-accent/10" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-accent/60 pulse-glow" />
              </div>
            </div>

            <h2 className="text-lg font-light tracking-[0.15em] text-text mb-2">
              {t('void_state')}
            </h2>
            <p className="text-text-3 text-xs mb-10 tracking-wide">
              {t('genesis_waiting')}
            </p>

            <button
              onClick={handleGenesis}
              disabled={loading}
              className="group relative px-8 py-2.5 text-xs font-medium tracking-[0.1em]
                         text-accent border border-accent/20 rounded-lg
                         hover:border-accent/40 hover:bg-accent-dim
                         transition-all duration-300
                         disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span>{loading ? t('god_speaking') : t('genesis_btn')}</span>
              {loading && (
                <div className="absolute inset-0 rounded-lg shimmer" />
              )}
            </button>
          </div>
        ) : (
          <div className="fade-in panel rounded-xl p-6 max-h-[65vh] overflow-y-auto border-accent/10">
            <div className="text-accent text-[10px] tracking-[0.2em] font-medium mb-4 uppercase">
              {t('genesis_word')}
            </div>
            <div className="text-text text-[13px] leading-[1.8] whitespace-pre-wrap font-light">
              {genesisText}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
