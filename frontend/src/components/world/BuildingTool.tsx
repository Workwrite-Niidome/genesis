/**
 * GENESIS v3 Building Tool UI
 *
 * A floating panel for voxel construction. Appears when the user enters
 * build mode (keyboard shortcut: B). Provides color palette, material
 * selection, and tool mode toggling (Place / Destroy / Paint).
 *
 * Communicates with the Three.js engine via callbacks and syncs state
 * back to WorldViewV3.
 */
import { useEffect, useCallback, useState, useRef } from 'react';
import type { BuildMode } from '../../engine/BuildingTool';

// ── Default color palette (16 colors) ────────────────────────
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

type MaterialType = 'solid' | 'emissive' | 'transparent' | 'glass';

const TOOL_MODES: { mode: BuildMode; label: string; shortLabel: string; color: string; activeColor: string }[] = [
  { mode: 'place', label: 'Place Block', shortLabel: 'Place', color: 'bg-white/10 text-white/70 hover:bg-white/20', activeColor: 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30' },
  { mode: 'destroy', label: 'Destroy Block', shortLabel: 'Destroy', color: 'bg-white/10 text-white/70 hover:bg-white/20', activeColor: 'bg-red-600 text-white shadow-lg shadow-red-600/30' },
  { mode: 'paint', label: 'Paint Block', shortLabel: 'Paint', color: 'bg-white/10 text-white/70 hover:bg-white/20', activeColor: 'bg-amber-500 text-white shadow-lg shadow-amber-500/30' },
];

// ── Props ────────────────────────────────────────────────────
export interface BuildingToolProps {
  /** Whether build mode is currently active (panel visible). */
  active: boolean;
  /** Current build mode. */
  buildMode: BuildMode;
  /** Current selected color hex. */
  buildColor: string;
  /** Current selected material. */
  buildMaterial: string;
  /** Toggle build mode on/off or switch sub-mode. */
  onSetBuildMode: (mode: BuildMode) => void;
  /** Set the selected color. */
  onSetBuildColor: (color: string) => void;
  /** Set the selected material. */
  onSetBuildMaterial: (material: MaterialType) => void;
  /** Close the building tool. */
  onClose: () => void;
}

export function BuildingTool({
  active,
  buildMode,
  buildColor,
  buildMaterial,
  onSetBuildMode,
  onSetBuildColor,
  onSetBuildMaterial,
  onClose,
}: BuildingToolProps) {
  const [customHex, setCustomHex] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);
  const customInputRef = useRef<HTMLInputElement>(null);

  // ── Keyboard shortcuts ─────────────────────────────────────
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Ignore if user is typing in an input
    if (
      e.target instanceof HTMLInputElement ||
      e.target instanceof HTMLTextAreaElement
    ) {
      return;
    }

    // B = toggle build mode
    if (e.key === 'b' || e.key === 'B') {
      if (active) {
        onClose();
      }
      // Note: opening is handled by the parent WorldViewV3
      return;
    }

    if (!active) return;

    // Escape = close build mode
    if (e.key === 'Escape') {
      onClose();
      return;
    }

    // 1-9 = quick-select palette colors (first 9)
    const num = parseInt(e.key, 10);
    if (num >= 1 && num <= 9 && num <= PALETTE_COLORS.length) {
      onSetBuildColor(PALETTE_COLORS[num - 1].hex);
      return;
    }

    // Q / E / R = cycle tool modes
    if (e.key === 'q' || e.key === 'Q') {
      onSetBuildMode('place');
      return;
    }
    if (e.key === 'e' || e.key === 'E') {
      onSetBuildMode('destroy');
      return;
    }
    if (e.key === 'r' || e.key === 'R') {
      onSetBuildMode('paint');
      return;
    }
  }, [active, onClose, onSetBuildColor, onSetBuildMode]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Focus custom input when shown
  useEffect(() => {
    if (showCustomInput && customInputRef.current) {
      customInputRef.current.focus();
    }
  }, [showCustomInput]);

  const handleCustomHexSubmit = useCallback(() => {
    const hex = customHex.startsWith('#') ? customHex : `#${customHex}`;
    if (/^#[0-9A-Fa-f]{6}$/.test(hex)) {
      onSetBuildColor(hex);
      setShowCustomInput(false);
      setCustomHex('');
    }
  }, [customHex, onSetBuildColor]);

  if (!active) return null;

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2 select-none">
      {/* ── Main panel ──────────────────────────────────────── */}
      <div className="bg-gray-950/90 backdrop-blur-md border border-white/10 rounded-xl shadow-2xl shadow-black/50 px-4 py-3 min-w-[420px]">
        {/* Header row: title + close */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-bold font-mono text-white/80 tracking-wider uppercase">
              Build Mode
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-white/40 hover:text-white/80 text-xs font-mono px-2 py-0.5 rounded hover:bg-white/10 transition-colors"
            title="Close (B or Esc)"
          >
            ESC
          </button>
        </div>

        {/* ── Tool Mode Toggle ──────────────────────────────── */}
        <div className="flex gap-1.5 mb-3">
          {TOOL_MODES.map(({ mode, shortLabel, color, activeColor }) => (
            <button
              key={mode}
              onClick={() => onSetBuildMode(mode)}
              className={`
                flex-1 px-3 py-1.5 rounded-lg text-xs font-mono font-bold
                transition-all duration-150
                ${buildMode === mode ? activeColor : color}
              `}
            >
              {shortLabel}
            </button>
          ))}
        </div>

        {/* ── Color & Material (visible for place and paint modes) ── */}
        {(buildMode === 'place' || buildMode === 'paint') && (
          <>
            {/* Color palette */}
            <div className="mb-3">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest">
                  Color
                </span>
                <button
                  onClick={() => setShowCustomInput(!showCustomInput)}
                  className="text-[10px] font-mono text-cyan-400/70 hover:text-cyan-400 transition-colors"
                >
                  {showCustomInput ? 'palette' : 'custom'}
                </button>
              </div>

              {showCustomInput ? (
                /* Custom hex input */
                <div className="flex items-center gap-2">
                  <div
                    className="w-8 h-8 rounded border border-white/20 flex-shrink-0"
                    style={{ backgroundColor: customHex.startsWith('#') ? customHex : `#${customHex}` }}
                  />
                  <div className="flex-1 flex gap-1">
                    <input
                      ref={customInputRef}
                      type="text"
                      value={customHex}
                      onChange={(e) => setCustomHex(e.target.value.replace(/[^#0-9A-Fa-f]/g, '').slice(0, 7))}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleCustomHexSubmit();
                        e.stopPropagation();
                      }}
                      placeholder="#FF00FF"
                      className="flex-1 bg-white/5 border border-white/10 rounded px-2 py-1 text-xs font-mono text-white placeholder-white/20 focus:outline-none focus:border-cyan-500/50"
                    />
                    <button
                      onClick={handleCustomHexSubmit}
                      className="px-2 py-1 rounded bg-cyan-600 text-white text-xs font-mono hover:bg-cyan-500 transition-colors"
                    >
                      Set
                    </button>
                  </div>
                </div>
              ) : (
                /* Color grid (4x4) */
                <div className="grid grid-cols-8 gap-1">
                  {PALETTE_COLORS.map(({ hex, name }, idx) => (
                    <button
                      key={hex}
                      onClick={() => onSetBuildColor(hex)}
                      title={`${name} (${idx < 9 ? idx + 1 : ''})`}
                      className={`
                        w-7 h-7 rounded-md border-2 transition-all duration-100
                        hover:scale-110 hover:z-10 relative
                        ${buildColor === hex
                          ? 'border-white scale-110 z-10 ring-1 ring-white/50'
                          : 'border-transparent hover:border-white/40'
                        }
                      `}
                      style={{ backgroundColor: hex }}
                    >
                      {/* Number hint for quick-select (1-9) */}
                      {idx < 9 && (
                        <span className="absolute -top-1 -right-1 text-[8px] font-mono text-white/50 bg-black/60 rounded-full w-3 h-3 flex items-center justify-center leading-none">
                          {idx + 1}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Material selector */}
            <div className="mb-2">
              <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest block mb-1.5">
                Material
              </span>
              <div className="flex gap-1.5">
                {MATERIALS.map(({ id, label, icon }) => (
                  <button
                    key={id}
                    onClick={() => onSetBuildMaterial(id as MaterialType)}
                    className={`
                      flex-1 flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-lg text-xs font-mono
                      transition-all duration-150
                      ${buildMaterial === id
                        ? 'bg-cyan-600/80 text-white shadow-md shadow-cyan-600/20'
                        : 'bg-white/5 text-white/50 hover:bg-white/10 hover:text-white/70'
                      }
                    `}
                  >
                    <span className="text-sm">{icon}</span>
                    <span className="text-[10px]">{label}</span>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {/* ── Current Selection Display ─────────────────────── */}
        <div className="flex items-center justify-between pt-2 border-t border-white/5">
          <div className="flex items-center gap-2">
            <div
              className="w-5 h-5 rounded border border-white/20"
              style={{
                backgroundColor: buildMode === 'destroy' ? '#ef4444' : buildColor,
                boxShadow: buildMode === 'destroy'
                  ? '0 0 8px rgba(239,68,68,0.4)'
                  : `0 0 8px ${buildColor}40`,
              }}
            />
            <span className="text-[10px] font-mono text-white/50">
              {buildMode === 'destroy'
                ? 'Click to destroy'
                : `${buildColor} / ${buildMaterial}`
              }
            </span>
          </div>
          <div className="text-[10px] font-mono text-white/30">
            Q/E/R: mode | 1-9: color
          </div>
        </div>
      </div>
    </div>
  );
}
