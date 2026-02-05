/**
 * MobileBuildSheet — Build tool as bottom sheet for mobile.
 *
 * Tool mode buttons: 48px height, 14px text
 * Color palette: 8-column grid, 40x40 swatches (up from 28x28)
 * Material buttons: 44px height
 * No keyboard shortcut hints (not relevant on touch)
 */
import { useState, useCallback } from 'react';
import { useMobileStoreV3 } from '../../../stores/mobileStoreV3';
import { BottomSheet } from './BottomSheet';
import type { BuildMode } from '../../../engine/BuildingTool';
import type { SheetState } from '../../../stores/mobileStoreV3';

type MaterialType = 'solid' | 'emissive' | 'transparent' | 'glass';

const PALETTE_COLORS = [
  { hex: '#FF0000', name: 'Red' },
  { hex: '#FF6B00', name: 'Orange' },
  { hex: '#FFD700', name: 'Gold' },
  { hex: '#00FF00', name: 'Green' },
  { hex: '#00CED1', name: 'Teal' },
  { hex: '#0066FF', name: 'Blue' },
  { hex: '#8B00FF', name: 'Purple' },
  { hex: '#FF69B4', name: 'Pink' },
  { hex: '#FFFFFF', name: 'White' },
  { hex: '#C0C0C0', name: 'Silver' },
  { hex: '#808080', name: 'Gray' },
  { hex: '#404040', name: 'Dark Gray' },
  { hex: '#000000', name: 'Black' },
  { hex: '#8B4513', name: 'Brown' },
  { hex: '#228B22', name: 'Forest' },
  { hex: '#FFE4C4', name: 'Bisque' },
] as const;

const MATERIALS = [
  { id: 'solid', label: 'Solid', icon: '\u25A0' },
  { id: 'emissive', label: 'Glow', icon: '\u2600' },
  { id: 'transparent', label: 'Clear', icon: '\u25CB' },
  { id: 'glass', label: 'Glass', icon: '\u25C7' },
] as const;

const TOOL_MODES: { mode: BuildMode; label: string; color: string; activeColor: string }[] = [
  { mode: 'place', label: 'Place', color: 'bg-white/10 text-white/70', activeColor: 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30' },
  { mode: 'destroy', label: 'Destroy', color: 'bg-white/10 text-white/70', activeColor: 'bg-red-600 text-white shadow-lg shadow-red-600/30' },
  { mode: 'paint', label: 'Paint', color: 'bg-white/10 text-white/70', activeColor: 'bg-amber-500 text-white shadow-lg shadow-amber-500/30' },
];

interface MobileBuildSheetProps {
  buildMode: BuildMode;
  buildColor: string;
  buildMaterial: string;
  onSetBuildMode: (mode: BuildMode) => void;
  onSetBuildColor: (color: string) => void;
  onSetBuildMaterial: (material: MaterialType) => void;
  onClose: () => void;
}

export function MobileBuildSheet({
  buildMode,
  buildColor,
  buildMaterial,
  onSetBuildMode,
  onSetBuildColor,
  onSetBuildMaterial,
  onClose,
}: MobileBuildSheetProps) {
  const buildSheetState = useMobileStoreV3(s => s.buildSheetState);
  const setBuildSheetState = useMobileStoreV3(s => s.setBuildSheetState);
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customHex, setCustomHex] = useState('');

  const handleStateChange = (state: SheetState) => {
    setBuildSheetState(state);
    if (state === 'closed') {
      onClose();
    }
  };

  const handleCustomHexSubmit = useCallback(() => {
    const hex = customHex.startsWith('#') ? customHex : `#${customHex}`;
    if (/^#[0-9A-Fa-f]{6}$/.test(hex)) {
      onSetBuildColor(hex);
      setShowCustomInput(false);
      setCustomHex('');
    }
  }, [customHex, onSetBuildColor]);

  const peekContent = (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-[13px] font-bold font-mono text-white/80 tracking-wider uppercase">
          Build Mode
        </span>
      </div>
      <div className="flex items-center gap-2">
        <div
          className="w-6 h-6 rounded border border-white/20"
          style={{
            backgroundColor: buildMode === 'destroy' ? '#ef4444' : buildColor,
          }}
        />
        <span className="text-[12px] font-mono text-white/50">
          {buildMode === 'destroy' ? 'Destroy' : buildColor}
        </span>
      </div>
    </div>
  );

  return (
    <BottomSheet
      state={buildSheetState}
      onStateChange={handleStateChange}
      peekContent={peekContent}
    >
      <div className="px-4 pb-6 space-y-4">
        {/* Tool Mode Toggle */}
        <div className="flex gap-2">
          {TOOL_MODES.map(({ mode, label, color, activeColor }) => (
            <button
              key={mode}
              onClick={() => onSetBuildMode(mode)}
              className={`flex-1 rounded-lg text-[14px] font-mono font-bold transition-all duration-150 ${
                buildMode === mode ? activeColor : color
              }`}
              style={{ height: 48 }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Color & Material (visible for place and paint modes) */}
        {(buildMode === 'place' || buildMode === 'paint') && (
          <>
            {/* Color palette */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[12px] font-mono text-white/40 uppercase tracking-widest">
                  Color
                </span>
                <button
                  onClick={() => setShowCustomInput(!showCustomInput)}
                  className="text-[12px] font-mono text-cyan-400/70"
                >
                  {showCustomInput ? 'palette' : 'custom'}
                </button>
              </div>

              {showCustomInput ? (
                <div className="flex items-center gap-2">
                  <div
                    className="rounded border border-white/20 flex-shrink-0"
                    style={{
                      width: 40,
                      height: 40,
                      backgroundColor: customHex.startsWith('#') ? customHex : `#${customHex}`,
                    }}
                  />
                  <div className="flex-1 flex gap-2">
                    <input
                      type="text"
                      value={customHex}
                      onChange={(e) => setCustomHex(e.target.value.replace(/[^#0-9A-Fa-f]/g, '').slice(0, 7))}
                      placeholder="#FF00FF"
                      className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 text-[14px] font-mono text-white placeholder-white/20 focus:outline-none focus:border-cyan-500/50"
                      style={{ height: 44 }}
                    />
                    <button
                      onClick={handleCustomHexSubmit}
                      className="px-4 rounded-lg bg-cyan-600 text-white text-[14px] font-mono"
                      style={{ height: 44 }}
                    >
                      Set
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-8 gap-1.5">
                  {PALETTE_COLORS.map(({ hex, name }) => (
                    <button
                      key={hex}
                      onClick={() => onSetBuildColor(hex)}
                      title={name}
                      className={`rounded-lg border-2 transition-all duration-100 ${
                        buildColor === hex
                          ? 'border-white scale-110 z-10 ring-1 ring-white/50'
                          : 'border-transparent'
                      }`}
                      style={{ width: 40, height: 40, backgroundColor: hex }}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Material selector */}
            <div>
              <span className="text-[12px] font-mono text-white/40 uppercase tracking-widest block mb-2">
                Material
              </span>
              <div className="flex gap-2">
                {MATERIALS.map(({ id, label, icon }) => (
                  <button
                    key={id}
                    onClick={() => onSetBuildMaterial(id as MaterialType)}
                    className={`flex-1 flex flex-col items-center gap-1 rounded-lg text-[14px] font-mono transition-all duration-150 ${
                      buildMaterial === id
                        ? 'bg-cyan-600/80 text-white shadow-md shadow-cyan-600/20'
                        : 'bg-white/5 text-white/50'
                    }`}
                    style={{ height: 44 }}
                  >
                    <span className="text-base">{icon}</span>
                    <span className="text-[11px]">{label}</span>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Current Selection */}
        <div className="flex items-center justify-between pt-2 border-t border-white/5">
          <div className="flex items-center gap-2">
            <div
              className="w-6 h-6 rounded border border-white/20"
              style={{
                backgroundColor: buildMode === 'destroy' ? '#ef4444' : buildColor,
                boxShadow: buildMode === 'destroy'
                  ? '0 0 8px rgba(239,68,68,0.4)'
                  : `0 0 8px ${buildColor}40`,
              }}
            />
            <span className="text-[12px] font-mono text-white/50">
              {buildMode === 'destroy'
                ? 'Tap to destroy'
                : `${buildColor} / ${buildMaterial}`
              }
            </span>
          </div>
        </div>
      </div>
    </BottomSheet>
  );
}
