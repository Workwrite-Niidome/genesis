import { useTranslation } from 'react-i18next';
import { useWorldStore } from '../../stores/worldStore';
import { api } from '../../services/api';
import { useState, useEffect } from 'react';

export default function VoidOverlay() {
  const { t } = useTranslation();
  const { godAiPhase, fetchState } = useWorldStore();
  const [loading, setLoading] = useState(false);
  const [genesisText, setGenesisText] = useState<string | null>(null);
  const [revealed, setRevealed] = useState('');

  if (godAiPhase !== 'pre_genesis') return null;

  // Typewriter reveal for genesis text
  useEffect(() => {
    if (!genesisText) return;
    let i = 0;
    const timer = setInterval(() => {
      i++;
      setRevealed(genesisText.slice(0, i));
      if (i >= genesisText.length) clearInterval(timer);
    }, 25);
    return () => clearInterval(timer);
  }, [genesisText]);

  const handleGenesis = async () => {
    setLoading(true);
    try {
      const result = await api.world.genesis();
      if (result.success) {
        setGenesisText(result.god_response);
        setTimeout(fetchState, 8000);
      }
    } catch (e) {
      console.error('Genesis failed:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="absolute inset-0 flex items-center justify-center z-30">
      {/* Radial ambient glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(circle at 50% 50%, rgba(124,91,245,0.04) 0%, transparent 60%)',
        }}
      />

      <div className="text-center max-w-lg mx-auto px-6 relative">
        {!genesisText ? (
          <div className="fade-in-up">
            {/* Void symbol - animated concentric rings */}
            <div className="relative w-28 h-28 mx-auto mb-10">
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="absolute inset-0 rounded-full border pulse-ring"
                  style={{
                    borderColor: `rgba(124, 91, 245, ${0.15 - i * 0.03})`,
                    inset: `${i * 8}px`,
                    animationDelay: `${i * 0.5}s`,
                    animationDuration: `${3 + i * 0.5}s`,
                  }}
                />
              ))}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-2.5 h-2.5 rounded-full bg-accent pulse-glow" />
              </div>
            </div>

            <h2 className="text-xl font-light tracking-[0.2em] text-text mb-3 uppercase">
              {t('void_state')}
            </h2>
            <p className="text-text-3 text-[12px] mb-12 tracking-wide leading-relaxed">
              {t('genesis_waiting')}
            </p>

            <button
              onClick={handleGenesis}
              disabled={loading}
              className="group relative px-10 py-3 text-[11px] font-medium tracking-[0.15em] uppercase
                         text-accent border border-accent/20 rounded-xl
                         hover:border-accent/40 hover:bg-accent-dim hover:shadow-[0_0_30px_rgba(124,91,245,0.15)]
                         transition-all duration-500
                         disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <span className="relative z-10">
                {loading ? t('god_speaking') : t('genesis_btn')}
              </span>
              {loading && (
                <div className="absolute inset-0 rounded-xl overflow-hidden">
                  <div className="shimmer w-full h-full" />
                </div>
              )}
              {!loading && (
                <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                  style={{
                    background: 'radial-gradient(circle at center, rgba(124,91,245,0.08), transparent 70%)',
                  }}
                />
              )}
            </button>
          </div>
        ) : (
          <div className="fade-in-slow">
            {/* Genesis response */}
            <div className="glass rounded-2xl p-8 max-h-[65vh] overflow-y-auto border border-accent/10
                          shadow-[0_0_60px_rgba(124,91,245,0.08)]">
              <div className="flex items-center gap-2 mb-5">
                <div className="w-1.5 h-1.5 rounded-full bg-accent pulse-glow" />
                <span className="text-accent text-[10px] tracking-[0.25em] font-medium uppercase">
                  {t('genesis_word')}
                </span>
              </div>
              <div className="text-text text-[13px] leading-[2] whitespace-pre-wrap font-light">
                {revealed}
                {revealed.length < (genesisText?.length || 0) && (
                  <span className="inline-block w-0.5 h-4 bg-accent/60 ml-0.5 animate-pulse align-text-bottom" />
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
