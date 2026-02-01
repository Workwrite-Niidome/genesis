import { useTranslation } from 'react-i18next';
import { Eye, Grid3x3, Rocket } from 'lucide-react';
import { useWorldStore } from '../../stores/worldStore';
import { useUIStore } from '../../stores/uiStore';
import { useDeployStore } from '../../stores/deployStore';
import LanguageSwitcher from '../ui/LanguageSwitcher';

export default function ObserverHeader() {
  const { t } = useTranslation();
  const { tickNumber, aiCount, godAiPhase } = useWorldStore();
  const { showGrid, toggleGrid } = useUIStore();
  const { togglePanel, remainingDeploys, maxDeploys } = useDeployStore();

  return (
    <header className="absolute top-0 left-0 right-0 z-50 pointer-events-none">
      <div className="flex items-center justify-between px-5 py-3 pointer-events-auto">
        {/* Left: Branding */}
        <div className="flex items-center gap-3 glass rounded-xl px-4 py-2 border border-border">
          <div className="relative">
            <div className="w-1.5 h-1.5 rounded-full bg-accent" />
            <div className="absolute inset-0 w-1.5 h-1.5 rounded-full bg-accent pulse-glow" />
          </div>
          <span className="text-sm font-semibold tracking-[0.2em] text-text">GENESIS</span>
          <div className="w-px h-3.5 bg-border" />
          <div className="flex items-center gap-1">
            <Eye size={11} className="text-text-3" />
            <span className="text-[10px] text-text-3 tracking-wide">{t('observer_mode')}</span>
          </div>
        </div>

        {/* Center: Live stats */}
        <div className="flex items-center gap-4 glass rounded-xl px-4 py-2 border border-border">
          <div className="flex items-center gap-1.5 text-[11px]">
            <span className="text-text-3">{t('tick')}</span>
            <span className="mono font-medium text-cyan">{tickNumber.toLocaleString()}</span>
          </div>
          <div className="w-px h-3 bg-border" />
          <div className="flex items-center gap-1.5 text-[11px]">
            <span className="text-text-3">{t('ais')}</span>
            <span className="mono font-medium text-green">{aiCount}</span>
          </div>
          <div className="w-px h-3 bg-border" />
          <div className="flex items-center gap-1 text-[10px]">
            <div className={`w-1 h-1 rounded-full ${godAiPhase === 'post_genesis' ? 'bg-green' : 'bg-orange'}`} />
            <span className="text-text-3">{godAiPhase === 'pre_genesis' ? t('pre_genesis') : t('post_genesis')}</span>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Deploy Agent button */}
          <button
            onClick={togglePanel}
            className="glass rounded-xl px-3.5 py-2 border border-cyan/20 flex items-center gap-2 text-cyan
                       hover:bg-cyan/10 hover:border-cyan/30 hover:shadow-[0_0_12px_rgba(88,213,240,0.1)]
                       transition-all duration-200"
          >
            <Rocket size={12} />
            <span className="text-[10px] font-medium tracking-wide">{t('deploy_title')}</span>
            <span className="badge bg-cyan/15 text-cyan text-[9px] mono">
              {remainingDeploys}/{maxDeploys}
            </span>
          </button>

          {/* Grid toggle */}
          <button
            onClick={toggleGrid}
            className={`glass rounded-xl px-3 py-2 border border-border flex items-center gap-1.5
                       transition-colors ${showGrid ? 'text-text-2' : 'text-text-3 opacity-50'}`}
            title="Toggle grid"
          >
            <Grid3x3 size={12} />
          </button>

          {/* Language switcher */}
          <LanguageSwitcher />
        </div>
      </div>
    </header>
  );
}
