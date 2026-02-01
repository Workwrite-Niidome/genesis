import { useTranslation } from 'react-i18next';
import { Play, Pause, FastForward, Rewind } from 'lucide-react';
import { useWorldStore } from '../../stores/worldStore';

const SPEEDS = [0.1, 0.5, 1, 2, 10, 100];

export default function TimelineBar() {
  const { t } = useTranslation();
  const { tickNumber, isPaused, timeSpeed, setPaused, setTimeSpeed } = useWorldStore();

  const speedIndex = SPEEDS.indexOf(timeSpeed);

  const slower = () => {
    const idx = Math.max(0, speedIndex - 1);
    setTimeSpeed(SPEEDS[idx]);
  };

  const faster = () => {
    const idx = Math.min(SPEEDS.length - 1, speedIndex + 1);
    setTimeSpeed(SPEEDS[idx]);
  };

  const progress = Math.min(100, (tickNumber / Math.max(tickNumber, 100)) * 100);

  return (
    <div className="h-9 flex items-center gap-3 px-4 bg-surface/90 backdrop-blur-xl border-t border-border z-50">
      {/* Playback controls */}
      <div className="flex items-center gap-0.5">
        <button
          onClick={slower}
          className="p-1 rounded-md hover:bg-surface-3 text-text-3 hover:text-text-2 transition-colors"
          title="Slower"
        >
          <Rewind size={12} />
        </button>

        <button
          onClick={() => setPaused(!isPaused)}
          className="p-1.5 rounded-lg hover:bg-surface-3 text-text transition-colors"
        >
          {isPaused ? <Play size={14} /> : <Pause size={14} />}
        </button>

        <button
          onClick={faster}
          className="p-1 rounded-md hover:bg-surface-3 text-text-3 hover:text-text-2 transition-colors"
          title="Faster"
        >
          <FastForward size={12} />
        </button>
      </div>

      {/* Speed indicator */}
      <div className="text-[11px] mono text-text-3 min-w-[60px]">
        <span className="text-cyan">x{timeSpeed}</span>
        {isPaused && <span className="ml-1.5 text-orange">{t('paused')}</span>}
      </div>

      {/* Timeline track */}
      <div className="flex-1 h-[3px] bg-surface-3 rounded-full overflow-visible relative mx-2 group">
        <div
          className="h-full bg-gradient-to-r from-accent/40 to-cyan/40 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-cyan transition-all duration-300
                     shadow-[0_0_6px_rgba(88,213,240,0.4)] group-hover:shadow-[0_0_10px_rgba(88,213,240,0.6)]
                     group-hover:scale-125"
          style={{ left: `${progress}%` }}
        />
      </div>

      {/* Tick counter */}
      <div className="text-[11px] mono text-text-3 whitespace-nowrap">
        {t('tick')} <span className="text-cyan">{tickNumber.toLocaleString()}</span>
      </div>
    </div>
  );
}
