import { Grid3x3 } from 'lucide-react';
import { useWorldStore } from '../../stores/worldStore';
import { useUIStore } from '../../stores/uiStore';
import LanguageSwitcher from '../ui/LanguageSwitcher';

export default function MobileHeader() {
  const { tickNumber, aiCount, godAiPhase } = useWorldStore();
  const { showGrid, toggleGrid } = useUIStore();

  return (
    <header className="flex items-center justify-between px-4 py-2.5 bg-surface/95 backdrop-blur-xl border-b border-border safe-top">
      {/* Left: Branding */}
      <div className="flex items-center gap-2">
        <div className="relative">
          <div className="w-1.5 h-1.5 rounded-full bg-accent" />
          <div className="absolute inset-0 w-1.5 h-1.5 rounded-full bg-accent pulse-glow" />
        </div>
        <span className="text-[13px] font-semibold tracking-[0.15em] text-text">GENESIS</span>
      </div>

      {/* Center: Compact stats */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1 text-[10px]">
          <span className="text-text-3">T:</span>
          <span className="mono font-medium text-cyan">{tickNumber.toLocaleString()}</span>
        </div>
        <div className="flex items-center gap-1 text-[10px]">
          <span className="text-text-3">AI:</span>
          <span className="mono font-medium text-green">{aiCount}</span>
        </div>
        <div className={`w-1.5 h-1.5 rounded-full ${godAiPhase === 'post_genesis' ? 'bg-green' : 'bg-orange'}`} />
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-1">
        <button
          onClick={toggleGrid}
          className="p-2 rounded-lg text-text-3 hover:text-text-2 hover:bg-surface-3/60 transition-all duration-150"
          title="Toggle grid"
        >
          <Grid3x3 size={16} className={showGrid ? 'text-accent' : ''} />
        </button>
        <LanguageSwitcher />
      </div>
    </header>
  );
}
