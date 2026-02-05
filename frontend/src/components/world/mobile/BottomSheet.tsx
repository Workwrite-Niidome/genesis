/**
 * BottomSheet — Reusable 4-state draggable bottom sheet for mobile.
 *
 * States: closed → peek (120px) → half (50vh) → full (92vh)
 * Based on the v2 MobileAISheet drag pattern with snap-to-state logic.
 */
import { useRef, useState, useCallback } from 'react';
import type { SheetState } from '../../../stores/mobileStoreV3';

const PEEK_HEIGHT = 120;
const HALF_RATIO = 0.5;
const FULL_RATIO = 0.92;

interface BottomSheetProps {
  state: SheetState;
  onStateChange: (state: SheetState) => void;
  children: React.ReactNode;
  /** Content shown in peek mode (above the fold). */
  peekContent?: React.ReactNode;
}

export function BottomSheet({ state, onStateChange, children, peekContent }: BottomSheetProps) {
  const dragStart = useRef<{ y: number; height: number } | null>(null);
  const [dragOffset, setDragOffset] = useState(0);

  const getHeight = useCallback((s: SheetState): number => {
    const vh = window.innerHeight;
    switch (s) {
      case 'closed': return 0;
      case 'peek': return PEEK_HEIGHT;
      case 'half': return vh * HALF_RATIO;
      case 'full': return vh * FULL_RATIO;
    }
  }, []);

  const onTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.touches[0];
    dragStart.current = { y: touch.clientY, height: getHeight(state) };
  }, [state, getHeight]);

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

    if (currentHeight < PEEK_HEIGHT * 0.5) {
      onStateChange('closed');
    } else if (currentHeight < vh * 0.35) {
      onStateChange('peek');
    } else if (currentHeight < vh * 0.7) {
      onStateChange('half');
    } else {
      onStateChange('full');
    }

    dragStart.current = null;
    setDragOffset(0);
  }, [dragOffset, onStateChange]);

  if (state === 'closed') return null;

  const baseHeight = getHeight(state);
  const currentHeight = Math.max(0, Math.min(window.innerHeight * FULL_RATIO, baseHeight + dragOffset));

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50 transition-[height] duration-300 ease-out"
      style={{
        height: dragStart.current ? currentHeight : baseHeight,
        transition: dragStart.current ? 'none' : undefined,
      }}
    >
      <div className="h-full flex flex-col bg-black/90 backdrop-blur-xl rounded-t-2xl border-t border-x border-white/10 shadow-[0_-8px_40px_rgba(0,0,0,0.5)] overflow-hidden">
        {/* Drag handle */}
        <div
          className="flex-shrink-0 flex flex-col items-center pt-2 pb-1 cursor-grab"
          style={{ minHeight: 44 }}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
        >
          <div className="w-8 h-1 rounded-full bg-white/20" />
        </div>

        {/* Peek content (always visible when sheet is open) */}
        {peekContent && (
          <div className="flex-shrink-0 px-4 pb-2">
            {peekContent}
          </div>
        )}

        {/* Scrollable content (half / full) */}
        {(state === 'half' || state === 'full') && (
          <div className="flex-1 overflow-y-auto overflow-x-hidden">
            {children}
          </div>
        )}
      </div>
    </div>
  );
}
