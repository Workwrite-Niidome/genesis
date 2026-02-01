import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowUp, Plus } from 'lucide-react';
import { api } from '../../services/api';
import { useAIStore } from '../../stores/aiStore';
import type { GodConversationEntry } from '../../types/world';

export default function GodAIConsole() {
  const { t } = useTranslation();
  const [history, setHistory] = useState<GodConversationEntry[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fetchAIs = useAIStore((s) => s.fetchAIs);

  useEffect(() => {
    api.god.getHistory().then((data) => setHistory(data.history)).catch(console.error);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history]);

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const msg = input.trim();
    setInput('');
    setSending(true);

    setHistory((h) => [...h, { role: 'admin', content: msg, timestamp: new Date().toISOString() }]);

    try {
      const result = await api.god.sendMessage(msg);
      setHistory((h) => [
        ...h,
        { role: 'god', content: result.god_response, timestamp: result.timestamp },
      ]);
    } catch (e) {
      console.error('Failed to send:', e);
    } finally {
      setSending(false);
    }
  };

  const handleSpawn = async () => {
    try {
      const res = await fetch('/api/god/spawn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: 3 }),
      });
      const data = await res.json();
      if (data.success) {
        fetchAIs();
      }
    } catch (e) {
      console.error('Spawn failed:', e);
    }
  };

  return (
    <div className="flex flex-col h-full fade-in">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-medium text-text flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-accent pulse-glow" />
          {t('god_console')}
        </h3>
        <button
          onClick={handleSpawn}
          className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] text-accent
                     border border-accent/20 hover:bg-accent-dim hover:border-accent/30
                     transition-all duration-200"
          title="Spawn AIs"
        >
          <Plus size={10} />
          Spawn AI
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 mb-3 min-h-0">
        {history.length === 0 && (
          <div className="text-center py-12 fade-in">
            <div className="relative w-10 h-10 mx-auto mb-4">
              <div className="absolute inset-0 rounded-full border border-accent/15 pulse-ring" />
              <div className="absolute inset-2 rounded-full border border-accent/10" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-1 h-1 rounded-full bg-accent/50" />
              </div>
            </div>
            <p className="text-text-3 text-[11px]">{t('genesis_waiting')}</p>
          </div>
        )}

        {history.map((entry, i) => (
          <div
            key={i}
            className={`p-3.5 rounded-xl text-[12px] leading-[1.8] fade-in ${
              entry.role === 'god'
                ? 'bg-accent-dim/30 border border-accent/8'
                : 'bg-surface-2 border border-border ml-4'
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              {entry.role === 'god' && (
                <div className="w-1 h-1 rounded-full bg-accent pulse-glow" />
              )}
              <span
                className="text-[9px] font-medium uppercase tracking-[0.15em]"
                style={{ color: entry.role === 'god' ? '#7c5bf5' : '#58d5f0' }}
              >
                {entry.role === 'god' ? 'GOD AI' : 'ADMIN'}
              </span>
            </div>
            <div className="text-text whitespace-pre-wrap font-light">{entry.content}</div>
          </div>
        ))}

        {sending && (
          <div className="p-3.5 rounded-xl bg-accent-dim/15 border border-accent/8 fade-in">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-1 h-1 rounded-full bg-accent pulse-glow" />
              <span className="text-[9px] text-accent font-medium uppercase tracking-[0.15em]">GOD AI</span>
            </div>
            <div className="flex items-center gap-2 text-text-3 text-[11px]">
              <div className="flex gap-1">
                <div className="w-1 h-1 rounded-full bg-accent/50 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-1 h-1 rounded-full bg-accent/50 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-1 h-1 rounded-full bg-accent/50 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-text-3">{t('god_speaking')}</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2 mt-auto">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={t('god_placeholder')}
          disabled={sending}
          className="flex-1 bg-surface-2 border border-border rounded-xl px-3.5 py-2.5
                     text-[12px] text-text placeholder-text-3
                     focus:outline-none focus:border-accent/25 focus:shadow-[0_0_0_1px_rgba(124,91,245,0.1)]
                     disabled:opacity-30 transition-all duration-200"
        />
        <button
          onClick={handleSend}
          disabled={sending || !input.trim()}
          className="w-9 h-9 flex items-center justify-center rounded-xl
                     bg-accent/80 hover:bg-accent text-bg
                     transition-all duration-200
                     disabled:opacity-15 disabled:cursor-not-allowed
                     hover:shadow-[0_0_15px_rgba(124,91,245,0.3)]"
        >
          <ArrowUp size={14} />
        </button>
      </div>
    </div>
  );
}
