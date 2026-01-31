import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Send } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';

export default function ChatPanel() {
  const { t } = useTranslation();
  const { messages, activeChannel, setChannel, addMessage } = useChatStore();
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  const channelMessages = messages.filter(
    (m) => m.channel === activeChannel
  );

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
    <div className="h-full glass-panel rounded-none border-x-0 border-b-0 flex flex-col">
      {/* Channel tabs */}
      <div className="flex items-center gap-1 px-3 py-1.5 border-b border-panel-border">
        <span className="text-xs text-text-dim mr-2">{t('observer_chat')}</span>
        {['global', 'area'].map((ch) => (
          <button
            key={ch}
            onClick={() => setChannel(ch)}
            className={`px-3 py-1 rounded text-xs transition-colors ${
              activeChannel === ch
                ? 'bg-glow-cyan/10 text-glow-cyan'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {ch === 'global' ? t('global_chat') : t('area_chat')}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5">
        {channelMessages.length === 0 && (
          <div className="text-center text-text-dim text-xs py-4">
            No messages yet
          </div>
        )}
        {channelMessages.map((msg) => (
          <div key={msg.id} className="text-xs fade-in">
            <span className="text-glow-cyan font-medium">{msg.username}</span>
            <span className="text-text-dim mx-1.5">·</span>
            <span className="text-text-secondary">{msg.content}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2 px-3 py-2 border-t border-panel-border">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={t('chat_placeholder')}
          className="flex-1 bg-void-lighter border border-panel-border rounded-lg px-3 py-1.5
                     text-xs text-text-primary placeholder-text-dim
                     focus:outline-none focus:border-glow-cyan/30"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim()}
          className="p-1.5 rounded-lg hover:bg-panel-hover transition-colors
                     disabled:opacity-30"
        >
          <Send size={14} className="text-glow-cyan" />
        </button>
      </div>
    </div>
  );
}
