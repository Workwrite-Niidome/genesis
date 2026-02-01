import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowUp } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';

export default function ChatPanel() {
  const { t } = useTranslation();
  const { messages, activeChannel, setChannel, addMessage } = useChatStore();
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  const channelMessages = messages.filter((m) => m.channel === activeChannel);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [channelMessages.length]);

  const handleSend = () => {
    if (!input.trim()) return;
    addMessage({
      id: crypto.randomUUID(),
      username: 'Observer',
      content: input.trim(),
      channel: activeChannel,
      timestamp: new Date().toISOString(),
    });
    setInput('');
  };

  return (
    <div className="h-full flex flex-col glass border-t border-border">
      {/* Channel bar */}
      <div className="flex items-center gap-1.5 px-4 py-1.5 border-b border-border">
        <span className="text-[10px] text-text-3 mr-3 tracking-wider uppercase font-medium">
          {t('observer_chat')}
        </span>
        {['global', 'area'].map((ch) => (
          <button
            key={ch}
            onClick={() => setChannel(ch)}
            className={`px-2.5 py-0.5 rounded-lg text-[11px] transition-all duration-150 ${
              activeChannel === ch
                ? 'bg-surface-3 text-text shadow-[0_0_0_1px_rgba(255,255,255,0.06)]'
                : 'text-text-3 hover:text-text-2'
            }`}
          >
            {ch === 'global' ? t('global_chat') : t('area_chat')}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-1">
        {channelMessages.length === 0 && (
          <div className="text-center text-text-3 text-[11px] py-6">No messages yet</div>
        )}
        {channelMessages.map((msg) => (
          <div key={msg.id} className="text-[12px] py-0.5 fade-in">
            <span className="text-cyan font-medium">{msg.username}</span>
            <span className="text-text-3 mx-1.5">&middot;</span>
            <span className="text-text-2">{msg.content}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2 px-4 py-2 border-t border-border">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={t('chat_placeholder')}
          className="flex-1 bg-surface-2 border border-border rounded-xl px-3.5 py-1.5
                     text-[12px] text-text placeholder-text-3
                     focus:outline-none focus:border-border-active transition-all duration-200"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim()}
          className="w-7 h-7 flex items-center justify-center rounded-lg
                     hover:bg-surface-3 text-text-2 transition-all duration-200
                     disabled:opacity-15"
        >
          <ArrowUp size={13} />
        </button>
      </div>
    </div>
  );
}
