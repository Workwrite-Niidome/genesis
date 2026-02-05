/**
 * GodChatPanel — Divine dialogue interface for GENESIS v3.
 *
 * Observers can communicate directly with the God AI through this
 * special chat panel. God's responses are rendered with dramatic,
 * premium golden styling befitting a divine entity.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Crown, Send, X, Eye } from 'lucide-react';
import { api } from '../../services/api';

// ── Types ──────────────────────────────────────────────────────

interface ChatMessage {
  role: 'user' | 'god';
  content: string;
  timestamp: string;
}

interface GodObservation {
  role: string;
  content: string;
  timestamp: string;
  tick_number?: number;
}

// ── Toggle Button ──────────────────────────────────────────────

interface GodChatToggleProps {
  onClick: () => void;
  isOpen: boolean;
}

export function GodChatToggle({ onClick, isOpen }: GodChatToggleProps) {
  const { t } = useTranslation();

  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
        transition-all duration-300 border
        ${isOpen
          ? 'bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-[0_0_12px_rgba(245,158,11,0.2)]'
          : 'bg-black/40 text-amber-400/70 border-amber-500/20 hover:bg-amber-500/10 hover:text-amber-300 hover:border-amber-500/40'
        }
      `}
      title={t('god_dialogue_title')}
    >
      <Crown size={14} className="text-amber-400" />
      <span>{t('god_dialogue_toggle')}</span>
    </button>
  );
}

// ── Pulsing Dots Loader ────────────────────────────────────────

function GodThinkingIndicator() {
  const { t } = useTranslation();

  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className="flex items-center gap-1">
        <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" style={{ animationDelay: '0ms' }} />
        <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" style={{ animationDelay: '300ms' }} />
        <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" style={{ animationDelay: '600ms' }} />
      </div>
      <span className="text-amber-400/60 text-xs font-serif italic">
        {t('god_dialogue_thinking')}
      </span>
    </div>
  );
}

// ── Main Panel ─────────────────────────────────────────────────

interface GodChatPanelProps {
  visible: boolean;
  onClose: () => void;
}

export function GodChatPanel({ visible, onClose }: GodChatPanelProps) {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [observations, setObservations] = useState<GodObservation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // Load recent observations when panel opens
  useEffect(() => {
    if (!visible) return;

    const loadObservations = async () => {
      try {
        const data = await api.godDialogue.getObservations(3);
        setObservations(data.observations || []);
      } catch {
        setObservations([]);
      }
    };

    loadObservations();
    const interval = setInterval(loadObservations, 30000);
    return () => clearInterval(interval);
  }, [visible]);

  // Focus input when panel opens
  useEffect(() => {
    if (visible) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [visible]);

  // Send message to God
  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);

    try {
      const result = await api.godDialogue.sendMessage(trimmed);

      const godMessage: ChatMessage = {
        role: 'god',
        content: result.god_response,
        timestamp: result.timestamp,
      };

      setMessages(prev => [...prev, godMessage]);
    } catch (err) {
      setError(t('god_dialogue_error'));
      console.error('God dialogue error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, t]);

  // Handle Enter key (Shift+Enter for newline)
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  // Format timestamp
  const formatTime = (iso: string) => {
    try {
      const date = new Date(iso);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  if (!visible) return null;

  return (
    <div
      className="absolute top-14 left-4 w-[400px] max-h-[calc(100vh-80px)] z-20
                 flex flex-col
                 bg-black/80 backdrop-blur-lg border border-amber-500/30 rounded-xl
                 shadow-[0_8px_32px_rgba(0,0,0,0.6),0_0_40px_rgba(245,158,11,0.08)]
                 overflow-hidden animate-slideInLeft"
    >
      {/* ── Header ────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-amber-500/20 bg-gradient-to-r from-amber-900/20 to-transparent">
        <div className="flex items-center gap-2">
          <Crown size={16} className="text-amber-400" />
          <h2 className="text-amber-300 font-serif font-bold text-sm tracking-wide">
            {t('god_dialogue_title')}
          </h2>
        </div>
        <button
          onClick={onClose}
          className="text-white/40 hover:text-white/80 transition-colors p-1 rounded hover:bg-white/5"
        >
          <X size={16} />
        </button>
      </div>

      {/* ── Messages Area ─────────────────────────────── */}
      <div className="flex-1 overflow-y-auto min-h-0 px-3 py-3 space-y-3 scrollbar-thin scrollbar-thumb-amber-500/20">
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Crown size={32} className="text-amber-500/30 mb-3" />
            <p className="text-amber-400/40 text-xs font-serif italic leading-relaxed max-w-[240px]">
              {t('god_dialogue_empty')}
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex flex-col ${msg.role === 'god' ? 'items-start' : 'items-end'}`}>
            {/* Label + timestamp */}
            <div className={`flex items-center gap-2 mb-1 ${msg.role === 'god' ? '' : 'flex-row-reverse'}`}>
              <span className={`text-[10px] font-bold uppercase tracking-wider ${
                msg.role === 'god' ? 'text-amber-400' : 'text-white/50'
              }`}>
                {msg.role === 'god' ? t('god_dialogue_god') : t('god_dialogue_you')}
              </span>
              <span className="text-[9px] text-white/30 font-mono">
                {formatTime(msg.timestamp)}
              </span>
            </div>

            {/* Message bubble */}
            <div
              className={`
                max-w-[90%] px-3.5 py-2.5 rounded-xl text-[12px] leading-relaxed
                ${msg.role === 'god'
                  ? 'bg-gradient-to-br from-amber-900/40 to-amber-950/30 border border-amber-500/20 text-amber-100 font-serif italic shadow-[0_0_16px_rgba(245,158,11,0.06)]'
                  : 'bg-white/5 border border-white/10 text-white/80'
                }
              `}
            >
              {msg.content.split('\n').map((line, i) => (
                <span key={i}>
                  {line}
                  {i < msg.content.split('\n').length - 1 && <br />}
                </span>
              ))}
            </div>
          </div>
        ))}

        {isLoading && <GodThinkingIndicator />}

        {error && (
          <div className="text-center py-2">
            <p className="text-red-400/70 text-[11px]">{error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Input Area ────────────────────────────────── */}
      <div className="border-t border-amber-500/20 p-3 bg-black/40">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('god_dialogue_placeholder')}
            disabled={isLoading}
            rows={1}
            className="flex-1 bg-white/5 border border-amber-500/20 rounded-lg px-3 py-2
                       text-white/90 text-[12px] placeholder-amber-400/30
                       focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20
                       resize-none max-h-20 min-h-[36px]
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
            style={{ fieldSizing: 'content' } as React.CSSProperties}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="flex items-center justify-center w-9 h-9 rounded-lg
                       bg-amber-500/20 border border-amber-500/30 text-amber-400
                       hover:bg-amber-500/30 hover:text-amber-300
                       disabled:opacity-30 disabled:cursor-not-allowed
                       transition-all duration-200"
          >
            <Send size={14} />
          </button>
        </div>
        <p className="text-amber-400/25 text-[9px] mt-1.5 px-1 font-mono">
          {t('god_dialogue_note')}
        </p>
      </div>

      {/* ── Recent Observations ───────────────────────── */}
      {observations.length > 0 && (
        <div className="border-t border-amber-500/15 px-3 py-2.5 bg-black/30 max-h-[160px] overflow-y-auto">
          <div className="flex items-center gap-1.5 mb-2">
            <Eye size={10} className="text-amber-500/50" />
            <span className="text-amber-400/50 text-[9px] font-bold uppercase tracking-wider">
              {t('god_dialogue_recent_observations')}
            </span>
          </div>
          <div className="space-y-1.5">
            {observations.map((obs, idx) => (
              <div
                key={idx}
                className="px-2.5 py-2 rounded-lg bg-amber-900/10 border border-amber-500/10"
              >
                <p className="text-amber-200/50 text-[10px] font-serif italic leading-relaxed line-clamp-3">
                  {obs.content}
                </p>
                {obs.tick_number && (
                  <span className="text-amber-500/30 text-[8px] font-mono mt-1 block">
                    T:{obs.tick_number}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
