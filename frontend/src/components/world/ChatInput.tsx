/**
 * ChatInput — Desktop proximity chat overlay for GENESIS v3.
 *
 * Hidden by default. Press Enter or T to open, Escape to close.
 * Sends messages via the /api/v3/chat/send endpoint.
 * The message appears as a speech bubble in the 3D world — identical
 * to AI entity speech, upholding the core design principle.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { api } from '../../services/api';

interface ChatInputProps {
  /** Current camera world position, used as the speech origin. */
  getCameraPosition: () => { x: number; y: number; z: number } | null;
}

export function ChatInput({ getCameraPosition }: ChatInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Open / close helpers
  const open = useCallback(() => {
    setIsOpen(true);
    // Focus on next tick so the input is mounted
    requestAnimationFrame(() => inputRef.current?.focus());
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    setMessage('');
  }, []);

  // Send the message
  const send = useCallback(async () => {
    const text = message.trim();
    if (!text || sending) return;

    setSending(true);
    try {
      const pos = getCameraPosition() ?? { x: 0, y: 0, z: 0 };
      await api.chat.send(text, pos, 'Observer');
    } catch (err) {
      console.warn('[GENESIS] Chat send failed:', err);
    } finally {
      setSending(false);
      setMessage('');
      close();
    }
  }, [message, sending, getCameraPosition, close]);

  // Global keydown — open chat with Enter or T (when not already focused)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if any input/textarea is focused
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      if ((e.key === 'Enter' || e.key === 't' || e.key === 'T') && !isOpen) {
        e.preventDefault();
        open();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, open]);

  // Input-level keydown — send on Enter, close on Escape
  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      send();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      close();
    }
  };

  if (!isOpen) {
    return (
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10">
        <span className="text-white/30 text-xs font-mono select-none">
          Press Enter or T to chat
        </span>
      </div>
    );
  }

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 w-full max-w-md px-4">
      <div className="flex items-center gap-2 bg-black/70 backdrop-blur-sm rounded-lg border border-white/10 px-3 py-2">
        <input
          ref={inputRef}
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleInputKeyDown}
          placeholder="Say something..."
          maxLength={300}
          disabled={sending}
          className="flex-1 bg-transparent text-white text-sm font-mono placeholder-white/30 outline-none"
          autoComplete="off"
        />
        <button
          onClick={send}
          disabled={sending || !message.trim()}
          className="px-3 py-1 rounded text-xs font-mono font-bold bg-purple-600 hover:bg-purple-500 disabled:bg-white/10 disabled:text-white/30 text-white transition-colors"
        >
          Send
        </button>
        <button
          onClick={close}
          className="px-2 py-1 rounded text-xs font-mono text-white/50 hover:text-white/80 transition-colors"
        >
          Esc
        </button>
      </div>
    </div>
  );
}
