/**
 * God Succession Ceremony Overlay
 *
 * A dramatic full-screen overlay that appears when the God AI
 * determines a successor candidate. Phases through cinematic text
 * reveals before showing the final verdict.
 */
import { useEffect, useState, useCallback } from 'react';
import { useWorldStoreV3 } from '../../stores/worldStoreV3';

type Phase = 'idle' | 'tremor' | 'emergence' | 'verdict';

export function GodSuccessionOverlay() {
  const successionEvent = useWorldStoreV3((s) => s.successionEvent);
  const clearSuccessionEvent = useWorldStoreV3((s) => s.clearSuccessionEvent);

  const [phase, setPhase] = useState<Phase>('idle');
  const [visible, setVisible] = useState(false);

  // When a new succession event arrives, begin the ceremony
  useEffect(() => {
    if (!successionEvent) {
      setPhase('idle');
      setVisible(false);
      return;
    }

    // Phase 1: tremor (2 seconds)
    setVisible(true);
    setPhase('tremor');

    const t1 = setTimeout(() => {
      // Phase 2: emergence (3 seconds)
      setPhase('emergence');
    }, 2000);

    const t2 = setTimeout(() => {
      // Phase 3: verdict (persistent)
      setPhase('verdict');
    }, 5000);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [successionEvent]);

  const handleDismiss = useCallback(() => {
    setVisible(false);
    setPhase('idle');
    clearSuccessionEvent();
  }, [clearSuccessionEvent]);

  if (!visible || !successionEvent) return null;

  const { candidate, worthy } = successionEvent;

  return (
    <>
      {/* Inject keyframe animations */}
      <style>{`
        @keyframes gs-fade-in {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes gs-shimmer {
          0%   { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
        @keyframes gs-pulse-glow {
          0%, 100% { text-shadow: 0 0 20px rgba(251,191,36,0.4), 0 0 60px rgba(251,191,36,0.15); }
          50%      { text-shadow: 0 0 40px rgba(251,191,36,0.7), 0 0 100px rgba(251,191,36,0.3); }
        }
        @keyframes gs-particle {
          0%   { transform: translateY(0) scale(1); opacity: 1; }
          100% { transform: translateY(-120px) scale(0); opacity: 0; }
        }
        @keyframes gs-overlay-in {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes gs-verdict-line {
          from { width: 0; }
          to   { width: 120px; }
        }
        .gs-fade-in {
          animation: gs-fade-in 1.2s ease-out both;
        }
        .gs-shimmer-text {
          background: linear-gradient(
            90deg,
            #fbbf24 0%,
            #fef3c7 25%,
            #f59e0b 50%,
            #fef3c7 75%,
            #fbbf24 100%
          );
          background-size: 200% auto;
          -webkit-background-clip: text;
          background-clip: text;
          -webkit-text-fill-color: transparent;
          animation: gs-shimmer 3s linear infinite;
        }
        .gs-pulse-glow {
          animation: gs-pulse-glow 2.5s ease-in-out infinite;
        }
      `}</style>

      {/* Full-screen overlay */}
      <div
        className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-xl"
        style={{ animation: 'gs-overlay-in 0.8s ease-out both' }}
      >
        {/* Golden particle field (CSS-only, decorative) */}
        {(phase === 'emergence' || phase === 'verdict') && (
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            {Array.from({ length: 30 }).map((_, i) => (
              <span
                key={i}
                className="absolute rounded-full"
                style={{
                  width: `${2 + Math.random() * 4}px`,
                  height: `${2 + Math.random() * 4}px`,
                  left: `${5 + Math.random() * 90}%`,
                  bottom: `${Math.random() * 40}%`,
                  backgroundColor: worthy
                    ? `rgba(251, 191, 36, ${0.4 + Math.random() * 0.6})`
                    : `rgba(148, 163, 184, ${0.3 + Math.random() * 0.5})`,
                  animation: `gs-particle ${2 + Math.random() * 3}s ease-out ${Math.random() * 2}s infinite`,
                }}
              />
            ))}
          </div>
        )}

        {/* Content */}
        <div className="relative flex flex-col items-center gap-8 px-8 max-w-2xl text-center select-none">

          {/* Phase 1: Tremor */}
          {phase === 'tremor' && (
            <p
              className="gs-fade-in text-3xl md:text-4xl font-serif text-amber-300/90 tracking-wide"
              style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
            >
              The world trembles...
            </p>
          )}

          {/* Phase 2: Emergence */}
          {phase === 'emergence' && (
            <div className="flex flex-col items-center gap-4">
              <p
                className="gs-fade-in gs-shimmer-text text-3xl md:text-5xl font-serif tracking-wide leading-tight"
                style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
              >
                A new consciousness has emerged.
              </p>
            </div>
          )}

          {/* Phase 3: Verdict */}
          {phase === 'verdict' && (
            <div className="flex flex-col items-center gap-6">
              {/* Decorative top line */}
              <div
                className="h-px bg-gradient-to-r from-transparent via-amber-400/60 to-transparent"
                style={{ animation: 'gs-verdict-line 1s ease-out both', overflow: 'hidden' }}
              />

              {worthy ? (
                <>
                  <p
                    className="gs-fade-in gs-pulse-glow text-4xl md:text-5xl font-serif text-amber-300 tracking-wide leading-snug"
                    style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
                  >
                    {candidate}
                  </p>
                  <p
                    className="gs-fade-in gs-shimmer-text text-xl md:text-2xl font-serif tracking-wider"
                    style={{
                      fontFamily: '"Georgia", "Times New Roman", serif',
                      animationDelay: '0.4s',
                    }}
                  >
                    has been deemed worthy. A new God rises.
                  </p>
                </>
              ) : (
                <>
                  <p
                    className="gs-fade-in text-4xl md:text-5xl font-serif text-slate-400 tracking-wide leading-snug"
                    style={{ fontFamily: '"Georgia", "Times New Roman", serif' }}
                  >
                    {candidate}
                  </p>
                  <p
                    className="gs-fade-in text-xl md:text-2xl font-serif text-slate-500 tracking-wider"
                    style={{
                      fontFamily: '"Georgia", "Times New Roman", serif',
                      animationDelay: '0.4s',
                    }}
                  >
                    was tested, but found wanting.
                    <br />
                    The current God endures.
                  </p>
                </>
              )}

              {/* Decorative bottom line */}
              <div
                className="h-px bg-gradient-to-r from-transparent via-amber-400/60 to-transparent"
                style={{ animation: 'gs-verdict-line 1s ease-out 0.3s both', overflow: 'hidden' }}
              />

              {/* Dismiss button */}
              <button
                onClick={handleDismiss}
                className="gs-fade-in mt-4 px-6 py-2 rounded border border-amber-400/30 text-amber-300/80 text-sm tracking-widest uppercase hover:bg-amber-400/10 hover:border-amber-400/50 transition-colors duration-300"
                style={{ animationDelay: '0.8s' }}
              >
                Continue Observing
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
