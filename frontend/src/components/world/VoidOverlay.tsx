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
        setTimeout(() => {
          fetchState();
        }, 5000);
      }
    } catch (e) {
      console.error('Genesis failed:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="absolute inset-0 flex items-center justify-center z-30 pointer-events-auto">
      <div className="text-center max-w-lg mx-auto px-8">
        {!genesisText ? (
          <div className="fade-in">
            <div className="text-6xl mb-6 pulse-slow text-glow-cyan glow-text">
              ∅
            </div>
            <h2 className="text-2xl font-light tracking-wider text-star mb-2">
              {t('void_state')}
            </h2>
            <p className="text-text-secondary text-sm mb-8">
              {t('genesis_waiting')}
            </p>
            <button
              onClick={handleGenesis}
              disabled={loading}
              className="px-6 py-3 rounded-lg border border-glow-cyan/30 text-glow-cyan
                         hover:bg-glow-cyan/10 hover:border-glow-cyan/60
                         transition-all duration-300 text-sm tracking-wider
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t('god_speaking') : t('genesis_btn')}
            </button>
          </div>
        ) : (
          <div className="fade-in glass-panel p-8 glow-border max-h-[70vh] overflow-y-auto">
            <div className="text-glow-cyan text-xs tracking-widest mb-4 uppercase">
              {t('genesis_word')}
            </div>
            <div className="text-star text-sm leading-relaxed whitespace-pre-wrap">
              {genesisText}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
