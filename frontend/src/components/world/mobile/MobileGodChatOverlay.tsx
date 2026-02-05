/**
 * MobileGodChatOverlay — God dialogue as full-screen overlay for mobile.
 *
 * Message bubbles: 14px text, max-width 85%
 * Input: 16px text (prevents iOS zoom), 48px min-height
 * Send button: 48x48
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Crown, Send, Eye } from 'lucide-react';
import { api } from '../../../services/api';
import { useMobileStoreV3 } from '../../../stores/mobileStoreV3';
import { MobileOverlay } from './MobileOverlay';

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

function GodThinkingIndicator() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className="flex items-center gap-1.5">
        <div className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" style={{ animationDelay: '0ms' }} />
        <div className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" style={{ animationDelay: '300ms' }} />
        <div className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" style={{ animationDelay: '600ms' }} />
      </div>
      <span className="text-amber-400/60 text-[13px] font-serif italic">
        {t('god_dialogue_thinking')}
      </span>
    </div>
  );
}

export function MobileGodChatOverlay() {
  const { t } = useTranslation();
  const godChatOpen = useMobileStoreV3(s => s.godChatOpen);
  const setGodChatOpen = useMobileStoreV3(s => s.setGodChatOpen);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [observations, setObservations] = useState<GodObservation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // Load observations when visible
  useEffect(() => {
    if (!godChatOpen) return;

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
  }, [godChatOpen]);

  // Focus input
  useEffect(() => {
    if (godChatOpen) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [godChatOpen]);

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

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  const formatTime = (iso: string) => {
    try {
      const date = new Date(iso);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <MobileOverlay
      visible={godChatOpen}
      onClose={() => setGodChatOpen(false)}
      title={t('god_dialogue_title')}
      icon={<Crown size={16} className="text-amber-400" />}
      headerClassName="border-b border-amber-500/20 bg-gradient-to-r from-amber-900/20 to-transparent"
    >
      <div className="flex flex-col flex-1 min-h-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {messages.length === 0 && !isLoading && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Crown size={36} className="text-amber-500/30 mb-3" />
              <p className="text-amber-400/40 text-[14px] font-serif italic leading-relaxed max-w-[280px]">
                {t('god_dialogue_empty')}
              </p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`flex flex-col ${msg.role === 'god' ? 'items-start' : 'items-end'}`}>
              <div className={`flex items-center gap-2 mb-1 ${msg.role === 'god' ? '' : 'flex-row-reverse'}`}>
                <span className={`text-[12px] font-bold uppercase tracking-wider ${
                  msg.role === 'god' ? 'text-amber-400' : 'text-white/50'
                }`}>
                  {msg.role === 'god' ? t('god_dialogue_god') : t('god_dialogue_you')}
                </span>
                <span className="text-[11px] text-white/30 font-mono">
                  {formatTime(msg.timestamp)}
                </span>
              </div>
              <div
                className={`px-4 py-3 rounded-xl text-[14px] leading-relaxed ${
                  msg.role === 'god'
                    ? 'bg-gradient-to-br from-amber-900/40 to-amber-950/30 border border-amber-500/20 text-amber-100 font-serif italic shadow-[0_0_16px_rgba(245,158,11,0.06)]'
                    : 'bg-white/5 border border-white/10 text-white/80'
                }`}
                style={{ maxWidth: '85%' }}
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
              <p className="text-red-400/70 text-[13px]">{error}</p>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Observations */}
        {observations.length > 0 && (
          <div className="flex-shrink-0 border-t border-amber-500/15 px-4 py-2.5 bg-black/30 max-h-[140px] overflow-y-auto">
            <div className="flex items-center gap-1.5 mb-2">
              <Eye size={12} className="text-amber-500/50" />
              <span className="text-amber-400/50 text-[11px] font-bold uppercase tracking-wider">
                {t('god_dialogue_recent_observations')}
              </span>
            </div>
            <div className="space-y-1.5">
              {observations.map((obs, idx) => (
                <div
                  key={idx}
                  className="px-3 py-2 rounded-lg bg-amber-900/10 border border-amber-500/10"
                >
                  <p className="text-amber-200/50 text-[12px] font-serif italic leading-relaxed line-clamp-3">
                    {obs.content}
                  </p>
                  {obs.tick_number && (
                    <span className="text-amber-500/30 text-[11px] font-mono mt-1 block">
                      T:{obs.tick_number}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="flex-shrink-0 border-t border-amber-500/20 p-3 bg-black/40 safe-bottom">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('god_dialogue_placeholder')}
              disabled={isLoading}
              rows={1}
              className="flex-1 bg-white/5 border border-amber-500/20 rounded-lg px-4 py-3
                         text-white/90 placeholder-amber-400/30
                         focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20
                         resize-none max-h-24
                         disabled:opacity-50 disabled:cursor-not-allowed
                         transition-colors"
              style={{ fontSize: 16, minHeight: 48, fieldSizing: 'content' } as React.CSSProperties}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="flex items-center justify-center rounded-lg
                         bg-amber-500/20 border border-amber-500/30 text-amber-400
                         disabled:opacity-30 disabled:cursor-not-allowed
                         transition-all duration-200"
              style={{ width: 48, height: 48 }}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </MobileOverlay>
  );
}
