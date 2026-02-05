/**
 * MobileChatInput — Floating action button + input overlay for mobile chat.
 *
 * Tap the button to reveal a text input. Messages are sent via the same
 * /api/v3/chat/send endpoint and appear as speech bubbles in the 3D world,
 * indistinguishable from AI entity speech.
 */
import { useState, useRef, useCallback } from 'react';
import { api } from '../../../services/api';

interface MobileChatInputProps {
  /** Current camera world position, used as the speech origin. */
  getCameraPosition: () => { x: number; y: number; z: number } | null;
}

export function MobileChatInput({ getCameraPosition }: MobileChatInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const open = useCallback(() => {
    setIsOpen(true);
    requestAnimationFrame(() => inputRef.current?.focus());
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    setMessage('');
  }, []);

  const send = useCallback(async () => {
    const text = message.trim();
    if (!text || sending) return;

    setSending(true);
    try {
      const pos = getCameraPosition() ?? { x: 0, y: 0, z: 0 };
      await api.chat.send(text, pos, 'Observer');
    } catch (err) {
      console.warn('[GENESIS] Mobile chat send failed:', err);
    } finally {
      setSending(false);
      setMessage('');
      close();
    }
  }, [message, sending, getCameraPosition, close]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      send();
    }
  };

  // Floating action button (closed state)
  if (!isOpen) {
    return (
      <button
        onClick={open}
        className="fixed bottom-[72px] right-4 z-30 w-12 h-12 rounded-full bg-purple-600/80 backdrop-blur-sm shadow-lg shadow-purple-900/40 flex items-center justify-center active:scale-95 transition-transform"
        aria-label="Open chat"
      >
        {/* Chat icon — simple speech bubble SVG */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-5 h-5 text-white"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </button>
    );
  }

  // Input overlay (open state)
  return (
    <div className="fixed inset-x-0 bottom-[56px] z-30 px-3 pb-2">
      {/* Backdrop tap to close */}
      <div className="fixed inset-0 z-0" onClick={close} />

      <div className="relative z-10 flex items-center gap-2 bg-black/80 backdrop-blur-sm rounded-xl border border-white/10 px-3 py-2">
        <input
          ref={inputRef}
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Say something..."
          maxLength={300}
          disabled={sending}
          className="flex-1 bg-transparent text-white placeholder-white/30 outline-none font-mono"
          style={{ fontSize: '16px' }}
          autoComplete="off"
          autoCapitalize="sentences"
        />
        <button
          onClick={send}
          disabled={sending || !message.trim()}
          className="px-3 py-1.5 rounded-lg text-sm font-mono font-bold bg-purple-600 hover:bg-purple-500 disabled:bg-white/10 disabled:text-white/30 text-white transition-colors flex-shrink-0"
        >
          Send
        </button>
        <button
          onClick={close}
          className="px-2 py-1.5 rounded-lg text-sm font-mono text-white/50 active:text-white/80 transition-colors flex-shrink-0"
        >
          X
        </button>
      </div>
    </div>
  );
}
