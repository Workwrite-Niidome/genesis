/**
 * MobileV3TopBar — Simplified top HUD for mobile (48px height).
 *
 * Left: "GENESIS v3" label
 * Center: T:{tick} compact display
 * Right: hamburger menu (44x44 touch target)
 * Dropdown: Build toggle, Camera mode, MiniMap toggle
 */
import { Menu, X, Hammer, Camera, Map } from 'lucide-react';
import { useMobileStoreV3 } from '../../../stores/mobileStoreV3';
import type { CameraMode } from '../../../engine/Camera';

interface MobileV3TopBarProps {
  tickNumber: number;
  buildActive: boolean;
  cameraMode: CameraMode;
  onToggleBuild: () => void;
  onCameraMode: (mode: CameraMode) => void;
}

export function MobileV3TopBar({
  tickNumber,
  buildActive,
  cameraMode,
  onToggleBuild,
  onCameraMode,
}: MobileV3TopBarProps) {
  const menuOpen = useMobileStoreV3(s => s.menuOpen);
  const setMenuOpen = useMobileStoreV3(s => s.setMenuOpen);
  const miniMapVisible = useMobileStoreV3(s => s.miniMapVisible);
  const setMiniMapVisible = useMobileStoreV3(s => s.setMiniMapVisible);

  return (
    <>
      <div
        className="fixed top-0 left-0 right-0 z-40 flex items-center justify-between px-3 bg-black/60 backdrop-blur-sm text-white/80 font-mono safe-top"
        style={{ height: 48 }}
      >
        {/* Left: Title */}
        <span className="text-purple-400 font-bold text-xs">GENESIS v3</span>

        {/* Center: Tick */}
        <span className="text-xs text-white/60">T:{tickNumber.toLocaleString()}</span>

        {/* Right: Hamburger */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="flex items-center justify-center text-white/70"
          style={{ width: 44, height: 44 }}
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Dropdown menu */}
      {menuOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-30"
            onClick={() => setMenuOpen(false)}
          />
          <div className="fixed top-12 right-2 z-40 bg-gray-950/95 backdrop-blur-md border border-white/10 rounded-xl shadow-2xl overflow-hidden safe-top"
            style={{ minWidth: 200 }}
          >
            {/* Build toggle */}
            <button
              onClick={() => { onToggleBuild(); setMenuOpen(false); }}
              className="w-full flex items-center gap-3 px-4 text-left text-sm text-white/80 hover:bg-white/5 transition-colors"
              style={{ minHeight: 48 }}
            >
              <Hammer size={16} className={buildActive ? 'text-emerald-400' : 'text-white/40'} />
              <span>{buildActive ? 'Exit Build Mode' : 'Build Mode'}</span>
            </button>

            {/* Camera modes */}
            <button
              onClick={() => { onCameraMode(cameraMode === 'observer' ? 'third_person' : 'observer'); setMenuOpen(false); }}
              className="w-full flex items-center gap-3 px-4 text-left text-sm text-white/80 hover:bg-white/5 transition-colors"
              style={{ minHeight: 48 }}
            >
              <Camera size={16} className="text-white/40" />
              <span>Camera: {cameraMode === 'observer' ? 'Observer' : 'Follow'}</span>
            </button>

            {/* MiniMap toggle */}
            <button
              onClick={() => { setMiniMapVisible(!miniMapVisible); setMenuOpen(false); }}
              className="w-full flex items-center gap-3 px-4 text-left text-sm text-white/80 hover:bg-white/5 transition-colors"
              style={{ minHeight: 48 }}
            >
              <Map size={16} className={miniMapVisible ? 'text-cyan-400' : 'text-white/40'} />
              <span>{miniMapVisible ? 'Hide MiniMap' : 'Show MiniMap'}</span>
            </button>
          </div>
        </>
      )}
    </>
  );
}
