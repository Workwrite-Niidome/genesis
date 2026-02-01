import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowUp, ChevronDown, ChevronUp } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useUIStore } from '../../stores/uiStore';

export default function ObserverChat() {
  const { t } = useTranslation();
  const { messages, activeChannel, setChannel, addMessage } = useChatStore();
  const { observerChatExpanded, toggleObserverChat } = useUIStore();
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  const channelMessages = messages.filter((m) => m.channel === activeChannel);

  useEffect(() => {
    if (observerChatExpanded) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [channelMessages.length, observerChatExpanded]);

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
    <div className="absolute bottom-0 left-0 right-0 z-40 pointer-events-none">
      <div className="max-w-2xl mx-auto px-4 pb-4 pointer-events-auto">
        <div className="glass rounded-xl border border-border shadow-[0_-4px_24px_rgba(0,0,0,0.3)]">
          {/* Toggle bar */}
          <button
            onClick={toggleObserverChat}
            className="w-full flex items-center justify-between px-4 py-2 border-b border-border hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-medium text-text-3 tracking-[0.15em] uppercase">
                {t('observer_chat')}
              </span>
              {channelMessages.length > 0 && (
                <span className="badge bg-accent-dim text-accent text-[8px]">{channelMessages.length}</span>
              )}
            </div>
            {observerChatExpanded ? <ChevronDown size={12} className="text-text-3" /> : <ChevronUp size={12} className="text-text-3" />}
          </button>

          {/* Expandable messages area */}
          {observerChatExpanded && (
            <div className="fade-in">
              {/* Channel tabs */}
              <div className="flex items-center gap-1.5 px-4 py-1.5 border-b border-border">
                {['global', 'area'].map((ch) => (
                  <button
                    key={ch}
                    onClick={() => setChannel(ch)}
                    className={`px-2.5 py-0.5 rounded-lg text-[10px] transition-all duration-150 ${
                      activeChannel === ch
                        ? 'bg-white/[0.06] text-text shadow-[0_0_0_1px_rgba(255,255,255,0.06)]'
                        : 'text-text-3 hover:text-text-2'
                    }`}
                  >
                    {ch === 'global' ? t('global_chat') : t('area_chat')}
                  </button>
                ))}
              </div>

              {/* Messages */}
              <div className="h-36 overflow-y-auto px-4 py-2 space-y-1">
                {channelMessages.length === 0 && (
                  <div className="text-center text-text-3 text-[10px] py-4">No messages yet</div>
                )}
                {channelMessages.map((msg) => (
                  <div key={msg.id} className="text-[11px] py-0.5">
                    <span className="text-cyan font-medium">{msg.username}</span>
                    <span className="text-text-3 mx-1">&middot;</span>
                    <span className="text-text-2">{msg.content}</span>
                  </div>
                ))}
                <div ref={bottomRef} />
              </div>
            </div>
          )}

          {/* Input — always visible */}
          <div className="flex gap-2 px-3 py-2 border-t border-border">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder={t('chat_placeholder')}
              className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-1.5
                         text-[11px] text-text placeholder-text-3
                         focus:outline-none focus:border-white/[0.12] transition-all duration-200"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="w-7 h-7 flex items-center justify-center rounded-lg
                         hover:bg-white/[0.06] text-text-2 transition-all duration-200
                         disabled:opacity-15"
            >
              <ArrowUp size={12} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
