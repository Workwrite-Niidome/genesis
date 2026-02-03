import { useTranslation } from 'react-i18next';
import { Eye } from 'lucide-react';
import { useWorldStore } from '../../stores/worldStore';
import LanguageSwitcher from '../ui/LanguageSwitcher';

export default function MobileHeader() {
  const { t } = useTranslation();
  const { tickNumber, aiCount, godAiPhase } = useWorldStore();

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
        <LanguageSwitcher />
      </div>
    </header>
  );
}
