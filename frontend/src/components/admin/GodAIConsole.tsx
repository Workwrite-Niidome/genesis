import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Send } from 'lucide-react';
import { api } from '../../services/api';
import type { GodConversationEntry } from '../../types/world';

export default function GodAIConsole() {
  const { t } = useTranslation();
  const [history, setHistory] = useState<GodConversationEntry[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

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

    // Optimistic: add admin message
    setHistory((h) => [...h, { role: 'admin', content: msg, timestamp: new Date().toISOString() }]);

    try {
      const result = await api.god.sendMessage(msg);
      setHistory((h) => [
        ...h,
        { role: 'god', content: result.god_response, timestamp: result.timestamp },
      ]);
    } catch (e) {
      console.error('Failed to send to God AI:', e);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full fade-in">
      <h3 className="text-sm font-medium text-glow-purple mb-3 flex items-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-glow-purple pulse-slow" />
        {t('god_console')}
      </h3>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 mb-3 min-h-0">
        {history.length === 0 && (
          <div className="text-center py-6 text-text-dim text-xs">
            {t('genesis_waiting')}
          </div>
        )}

        {history.map((entry, i) => (
          <div
            key={i}
            className={`p-3 rounded-lg text-xs leading-relaxed ${
              entry.role === 'god'
                ? 'bg-nebula/30 border border-nebula-light/20 text-star'
                : 'bg-void-lighter text-text-secondary ml-4'
            }`}
          >
            <div className="text-[10px] mb-1.5 uppercase tracking-wider"
              style={{ color: entry.role === 'god' ? '#ce93d8' : '#4fc3f7' }}
            >
              {entry.role === 'god' ? '神 AI' : 'Admin'}
            </div>
            <div className="whitespace-pre-wrap">{entry.content}</div>
          </div>
        ))}

        {sending && (
          <div className="p-3 rounded-lg bg-nebula/20 border border-nebula-light/10 text-xs">
            <div className="text-[10px] text-glow-purple mb-1 uppercase tracking-wider">神 AI</div>
            <div className="text-text-dim pulse-slow">{t('god_speaking')}</div>
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
          className="flex-1 bg-void-lighter border border-panel-border rounded-lg px-3 py-2
                     text-xs text-text-primary placeholder-text-dim
                     focus:outline-none focus:border-glow-purple/40
                     disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={sending || !input.trim()}
          className="p-2 rounded-lg bg-nebula/40 border border-nebula-light/30
                     hover:bg-nebula/60 transition-colors
                     disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <Send size={14} className="text-glow-purple" />
        </button>
      </div>
    </div>
  );
}
