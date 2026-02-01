import { useRef, useState, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { X, ChevronUp } from 'lucide-react';
import { useAIStore } from '../../stores/aiStore';
import { AIDetailContent } from '../observer/AIDetailCard';

type SheetState = 'closed' | 'peek' | 'half' | 'full';

const PEEK_HEIGHT = 120;
const HALF_RATIO = 0.5;
const FULL_RATIO = 0.92;

export default function MobileAISheet() {
  const { t } = useTranslation();
  const { selectedAI } = useAIStore();
  const [sheetState, setSheetState] = useState<SheetState>('closed');
  const sheetRef = useRef<HTMLDivElement>(null);
  const dragStart = useRef<{ y: number; height: number } | null>(null);
  const [dragOffset, setDragOffset] = useState(0);

  // Open to peek when an AI is selected
  useEffect(() => {
    if (selectedAI) {
      setSheetState('peek');
    } else {
      setSheetState('closed');
    }
  }, [selectedAI?.id]);

  const getHeight = useCallback((state: SheetState): number => {
    const vh = window.innerHeight;
    switch (state) {
      case 'closed': return 0;
      case 'peek': return PEEK_HEIGHT;
      case 'half': return vh * HALF_RATIO;
      case 'full': return vh * FULL_RATIO;
    }
  }, []);

  const onTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.touches[0];
    dragStart.current = { y: touch.clientY, height: getHeight(sheetState) };
  }, [sheetState, getHeight]);

  const onTouchMove = useCallback((e: React.TouchEvent) => {
    if (!dragStart.current) return;
    const touch = e.touches[0];
    const dy = dragStart.current.y - touch.clientY;
    setDragOffset(dy);
  }, []);

  const onTouchEnd = useCallback(() => {
    if (!dragStart.current) return;
    const currentHeight = dragStart.current.height + dragOffset;
    const vh = window.innerHeight;

    // Snap to nearest state
    if (currentHeight < PEEK_HEIGHT * 0.5) {
      setSheetState('closed');
      useAIStore.getState().selectAI(null);
    } else if (currentHeight < vh * 0.35) {
      setSheetState('peek');
    } else if (currentHeight < vh * 0.7) {
      setSheetState('half');
    } else {
      setSheetState('full');
    }

    dragStart.current = null;
    setDragOffset(0);
  }, [dragOffset]);

  if (!selectedAI || sheetState === 'closed') return null;

  const baseHeight = getHeight(sheetState);
  const currentHeight = Math.max(0, Math.min(window.innerHeight * FULL_RATIO, baseHeight + dragOffset));

  const color = selectedAI.appearance?.primaryColor || '#7c5bf5';

  return (
    <div
      ref={sheetRef}
      className="absolute bottom-0 left-0 right-0 z-50 transition-[height] duration-300 ease-out"
      style={{
        height: dragStart.current ? currentHeight : baseHeight,
        transition: dragStart.current ? 'none' : undefined,
      }}
    >
      <div className="h-full flex flex-col bg-surface/95 backdrop-blur-xl rounded-t-2xl border-t border-x border-border shadow-[0_-8px_40px_rgba(0,0,0,0.5)] overflow-hidden">
        {/* Drag handle */}
        <div
          className="flex-shrink-0 flex flex-col items-center pt-2 pb-1 cursor-grab touch-target"
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
        >
          <div className="w-8 h-1 rounded-full bg-white/20" />
        </div>

        {/* Peek header - always visible */}
        <div className="flex items-center gap-3 px-4 pb-2 flex-shrink-0">
          <div
            className="w-8 h-8 rounded-full flex-shrink-0"
            style={{
              backgroundColor: color,
              boxShadow: `0 0 16px ${color}40`,
            }}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[13px] font-medium text-text truncate">
                {selectedAI.name || `Entity ${selectedAI.id.slice(0, 8)}`}
              </span>
              <span className={`badge text-[8px] ${selectedAI.is_alive ? 'bg-green-dim text-green' : 'bg-orange-dim text-orange'}`}>
                {selectedAI.is_alive ? t('alive') : t('dead')}
              </span>
            </div>
            <div className="text-[10px] text-text-3 mt-0.5">
              {t('evolution_score')}: <span className="mono text-accent">{(selectedAI.state?.evolution_score ?? 0).toFixed(1)}</span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {sheetState === 'peek' && (
              <button
                onClick={() => setSheetState('half')}
                className="p-1.5 rounded-lg hover:bg-white/[0.08] text-text-3"
              >
                <ChevronUp size={16} />
              </button>
            )}
            <button
              onClick={() => {
                setSheetState('closed');
                useAIStore.getState().selectAI(null);
              }}
              className="p-1.5 rounded-lg hover:bg-white/[0.08] text-text-3"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Scrollable content - only visible in half/full */}
        {(sheetState === 'half' || sheetState === 'full') && (
          <div className="flex-1 overflow-y-auto">
            <AIDetailContent />
          </div>
        )}
      </div>
    </div>
  );
}
