import { useTranslation } from 'react-i18next';
import { Play, Pause, FastForward, Rewind, SkipForward } from 'lucide-react';
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

  return (
    <div className="h-10 flex items-center gap-4 px-4 glass-panel rounded-none border-b-0 border-x-0 z-50">
      {/* Playback controls */}
      <div className="flex items-center gap-1">
        <button
          onClick={slower}
          className="p-1 rounded hover:bg-panel-hover text-text-secondary hover:text-text-primary transition-colors"
          title="Slower"
        >
          <Rewind size={14} />
        </button>

        <button
          onClick={() => setPaused(!isPaused)}
          className="p-1.5 rounded-lg hover:bg-panel-hover text-text-primary transition-colors"
        >
          {isPaused ? <Play size={16} /> : <Pause size={16} />}
        </button>

        <button
          onClick={faster}
          className="p-1 rounded hover:bg-panel-hover text-text-secondary hover:text-text-primary transition-colors"
          title="Faster"
        >
          <FastForward size={14} />
        </button>
      </div>

      {/* Speed indicator */}
      <div className="text-xs font-mono text-text-secondary">
        <span className="text-glow-cyan">x{timeSpeed}</span>
        {isPaused && <span className="ml-2 text-glow-orange">{t('paused')}</span>}
      </div>

      {/* Timeline bar */}
      <div className="flex-1 h-1 bg-void-lighter rounded-full overflow-hidden relative mx-4">
        <div
          className="h-full bg-gradient-to-r from-glow-cyan/50 to-glow-purple/50 rounded-full transition-all"
          style={{ width: `${Math.min(100, (tickNumber / Math.max(tickNumber, 100)) * 100)}%` }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-glow-cyan shadow-[0_0_8px_rgba(79,195,247,0.5)]"
          style={{ left: `${Math.min(100, (tickNumber / Math.max(tickNumber, 100)) * 100)}%` }}
        />
      </div>

      {/* Tick counter */}
      <div className="text-xs font-mono text-text-secondary whitespace-nowrap">
        {t('tick')} <span className="text-glow-cyan">{tickNumber.toLocaleString()}</span>
      </div>
    </div>
  );
}
