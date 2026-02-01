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
          className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] text-accent
                     border border-accent/20 hover:bg-accent-dim transition-colors"
          title="Spawn AIs (Fallback)"
        >
          <Plus size={10} />
          Spawn AI
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-2.5 mb-3 min-h-0">
        {history.length === 0 && (
          <div className="text-center py-10 text-text-3 text-[11px]">
            {t('genesis_waiting')}
          </div>
        )}

        {history.map((entry, i) => (
          <div
            key={i}
            className={`p-3 rounded-lg text-[12px] leading-[1.7] fade-in ${
              entry.role === 'god'
                ? 'bg-accent-dim/40 border border-accent/10'
                : 'bg-surface-2 border border-border ml-6'
            }`}
          >
            <div
              className="text-[9px] font-medium mb-1.5 uppercase tracking-[0.15em]"
              style={{ color: entry.role === 'god' ? '#7c5bf5' : '#58d5f0' }}
            >
              {entry.role === 'god' ? 'GOD AI' : 'ADMIN'}
            </div>
            <div className="text-text whitespace-pre-wrap font-light">{entry.content}</div>
          </div>
        ))}

        {sending && (
          <div className="p-3 rounded-lg bg-accent-dim/20 border border-accent/10 fade-in">
            <div className="text-[9px] text-accent font-medium mb-1 uppercase tracking-[0.15em]">GOD AI</div>
            <div className="flex items-center gap-1.5 text-text-3 text-[11px]">
              <div className="flex gap-0.5">
                <div className="w-1 h-1 rounded-full bg-accent/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-1 h-1 rounded-full bg-accent/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-1 h-1 rounded-full bg-accent/60 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              {t('god_speaking')}
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
          className="flex-1 bg-surface-2 border border-border rounded-lg px-3 py-2
                     text-[12px] text-text placeholder-text-3
                     focus:outline-none focus:border-accent/30
                     disabled:opacity-40 transition-colors"
        />
        <button
          onClick={handleSend}
          disabled={sending || !input.trim()}
          className="w-8 h-8 flex items-center justify-center rounded-lg
                     bg-accent/80 hover:bg-accent text-bg
                     transition-colors duration-150
                     disabled:opacity-20 disabled:cursor-not-allowed"
        >
          <ArrowUp size={14} />
        </button>
      </div>
    </div>
  );
}
