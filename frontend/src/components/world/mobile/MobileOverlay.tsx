/**
 * MobileOverlay — Reusable full-screen overlay for mobile.
 *
 * Used for Timeline and God Chat overlays.
 * Slides up from bottom, fixed inset-0, with header and scrollable content.
 */
import { X } from 'lucide-react';

interface MobileOverlayProps {
  visible: boolean;
  onClose: () => void;
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  /** Extra class names for the header background */
  headerClassName?: string;
}

export function MobileOverlay({ visible, onClose, title, icon, children, headerClassName }: MobileOverlayProps) {
  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black/95 backdrop-blur-lg sheet-up safe-top">
      {/* Header */}
      <div className={`flex items-center justify-between px-4 flex-shrink-0 ${headerClassName || ''}`}
        style={{ minHeight: 48 }}
      >
        <div className="flex items-center gap-2">
          {icon}
          <h2 className="text-sm font-semibold text-white/90 tracking-wide">{title}</h2>
        </div>
        <button
          onClick={onClose}
          className="flex items-center justify-center text-white/50 hover:text-white/90 transition-colors"
          style={{ width: 44, height: 44 }}
        >
          <X size={20} />
        </button>
      </div>

      {/* Content — flex column so children can use flex-1/flex-shrink-0 */}
      <div className="flex-1 overflow-hidden flex flex-col min-h-0">
        {children}
      </div>

      {/* Safe area bottom padding */}
      <div className="safe-bottom" />

    </div>
  );
}
