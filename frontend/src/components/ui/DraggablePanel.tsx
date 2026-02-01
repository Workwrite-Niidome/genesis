import { useState, useRef, useCallback, useEffect } from 'react';
import { X, GripHorizontal } from 'lucide-react';

// Global z-index counter shared across all DraggablePanel instances
let globalZ = 100;

interface DraggablePanelProps {
  title: string;
  icon?: React.ReactNode;
  visible: boolean;
  onClose: () => void;
  children: React.ReactNode;
  defaultX?: number;
  defaultY?: number;
  defaultWidth?: number;
  defaultHeight?: number;
  minWidth?: number;
  minHeight?: number;
  maxWidth?: number;
  maxHeight?: number;
  headerExtra?: React.ReactNode;
}

export default function DraggablePanel({
  title,
  icon,
  visible,
  onClose,
  children,
  defaultX,
  defaultY,
  defaultWidth = 340,
  defaultHeight = 480,
  minWidth = 260,
  minHeight = 200,
  maxWidth = 800,
  maxHeight = 900,
  headerExtra,
}: DraggablePanelProps) {
  const [pos, setPos] = useState({ x: defaultX ?? 100, y: defaultY ?? 80 });
  const [size, setSize] = useState({ w: defaultWidth, h: defaultHeight });
  const [dragging, setDragging] = useState(false);
  const [resizing, setResizing] = useState(false);
  const [zBoost, setZBoost] = useState(0);
  const dragOffset = useRef({ x: 0, y: 0 });
  const resizeStart = useRef({ x: 0, y: 0, w: 0, h: 0 });

  const bringToFront = useCallback(() => {
    globalZ += 1;
    setZBoost(globalZ);
  }, []);

  // ---- Drag ----
  const onDragStart = useCallback(
    (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).closest('button')) return;
      e.preventDefault();
      bringToFront();
      setDragging(true);
      dragOffset.current = { x: e.clientX - pos.x, y: e.clientY - pos.y };
    },
    [pos, bringToFront],
  );

  useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => {
      const nx = Math.max(0, Math.min(window.innerWidth - 60, e.clientX - dragOffset.current.x));
      const ny = Math.max(0, Math.min(window.innerHeight - 40, e.clientY - dragOffset.current.y));
      setPos({ x: nx, y: ny });
    };
    const onUp = () => setDragging(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [dragging]);

  // ---- Resize ----
  const onResizeStart = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      bringToFront();
      setResizing(true);
      resizeStart.current = { x: e.clientX, y: e.clientY, w: size.w, h: size.h };
    },
    [size, bringToFront],
  );

  useEffect(() => {
    if (!resizing) return;
    const onMove = (e: MouseEvent) => {
      const dw = e.clientX - resizeStart.current.x;
      const dh = e.clientY - resizeStart.current.y;
      setSize({
        w: Math.max(minWidth, Math.min(maxWidth, resizeStart.current.w + dw)),
        h: Math.max(minHeight, Math.min(maxHeight, resizeStart.current.h + dh)),
      });
    };
    const onUp = () => setResizing(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [resizing, minWidth, minHeight, maxWidth, maxHeight]);

  // Reset position when becoming visible
  useEffect(() => {
    if (visible) {
      setPos({ x: defaultX ?? 100, y: defaultY ?? 80 });
      setSize({ w: defaultWidth, h: defaultHeight });
      bringToFront();
    }
  }, [visible]);

  if (!visible) return null;

  return (
    <div
      className="fixed pointer-events-auto fade-in"
      style={{
        left: pos.x,
        top: pos.y,
        width: size.w,
        height: size.h,
        zIndex: 60 + zBoost,
        userSelect: dragging || resizing ? 'none' : undefined,
      }}
      onMouseDown={bringToFront}
    >
      <div className="h-full flex flex-col glass rounded-2xl border border-border shadow-[0_8px_40px_rgba(0,0,0,0.5)] overflow-hidden">
        {/* Draggable header */}
        <div
          className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.04] flex-shrink-0 cursor-move select-none"
          onMouseDown={onDragStart}
        >
          <div className="flex items-center gap-2">
            <GripHorizontal size={12} className="text-text-3 opacity-40" />
            {icon}
            <span className="text-[12px] font-semibold text-text uppercase tracking-wider">
              {title}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {headerExtra}
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-white/[0.08] text-text-3 hover:text-text transition-colors"
            >
              <X size={13} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden">
          {children}
        </div>

        {/* Resize handle */}
        <div
          className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize opacity-30 hover:opacity-80 transition-opacity"
          onMouseDown={onResizeStart}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" className="text-text-3">
            <path d="M14 16L16 14M9 16L16 9M4 16L16 4" stroke="currentColor" strokeWidth="1.5" fill="none" />
          </svg>
        </div>
      </div>
    </div>
  );
}
