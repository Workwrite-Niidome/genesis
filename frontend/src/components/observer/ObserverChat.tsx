import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowUp, ChevronDown, ChevronUp, LogOut } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useObserverStore } from '../../stores/observerStore';
import { useUIStore } from '../../stores/uiStore';

export default function ObserverChat() {
  const { t } = useTranslation();
  const { messages, activeChannel, setChannel, fetchMessages, postMessage } = useChatStore();
  const { token, username, isLoggedIn, login, register, logout, error, loading } = useObserverStore();
  const { observerChatExpanded, toggleObserverChat } = useUIStore();
  const [input, setInput] = useState('');
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authUser, setAuthUser] = useState('');
  const [authPass, setAuthPass] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  const channelMessages = messages.filter((m) => m.channel === activeChannel);

  // Fetch messages when channel changes or chat is expanded
  useEffect(() => {
    if (observerChatExpanded) {
      fetchMessages(activeChannel);
    }
  }, [activeChannel, observerChatExpanded, fetchMessages]);

  useEffect(() => {
    if (observerChatExpanded) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [channelMessages.length, observerChatExpanded]);

  const handleSend = async () => {
    if (!input.trim() || !token) return;
    await postMessage(token, input.trim());
    setInput('');
  };

  const handleAuth = async () => {
    if (!authUser.trim() || !authPass.trim()) return;
    const success = authMode === 'login'
      ? await login(authUser, authPass)
      : await register(authUser, authPass);
    if (success) {
      setAuthUser('');
      setAuthPass('');
      fetchMessages(activeChannel);
    }
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
              {isLoggedIn && username && (
                <span className="text-[9px] text-cyan">{username}</span>
              )}
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
                {isLoggedIn && (
                  <button
                    onClick={logout}
                    className="ml-auto text-text-3 hover:text-text-2 transition-colors"
                    title="Logout"
                  >
                    <LogOut size={10} />
                  </button>
                )}
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

              {/* Login/Register form when not authenticated */}
              {!isLoggedIn && (
                <div className="px-3 py-2 border-t border-border space-y-1.5">
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => setAuthMode('login')}
                      className={`px-2 py-0.5 rounded text-[9px] transition-all ${
                        authMode === 'login'
                          ? 'bg-white/[0.08] text-text'
                          : 'text-text-3 hover:text-text-2'
                      }`}
                    >
                      Login
                    </button>
                    <button
                      onClick={() => setAuthMode('register')}
                      className={`px-2 py-0.5 rounded text-[9px] transition-all ${
                        authMode === 'register'
                          ? 'bg-white/[0.08] text-text'
                          : 'text-text-3 hover:text-text-2'
                      }`}
                    >
                      Register
                    </button>
                  </div>
                  <div className="flex gap-1.5">
                    <input
                      type="text"
                      value={authUser}
                      onChange={(e) => setAuthUser(e.target.value)}
                      placeholder="Username"
                      className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-lg px-2 py-1
                                 text-[10px] text-text placeholder-text-3
                                 focus:outline-none focus:border-white/[0.12] transition-all duration-200"
                    />
                    <input
                      type="password"
                      value={authPass}
                      onChange={(e) => setAuthPass(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleAuth()}
                      placeholder="Password"
                      className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-lg px-2 py-1
                                 text-[10px] text-text placeholder-text-3
                                 focus:outline-none focus:border-white/[0.12] transition-all duration-200"
                    />
                    <button
                      onClick={handleAuth}
                      disabled={loading || !authUser.trim() || !authPass.trim()}
                      className="px-3 py-1 rounded-lg bg-white/[0.06] text-[10px] text-text
                                 hover:bg-white/[0.1] transition-all duration-200
                                 disabled:opacity-30"
                    >
                      {loading ? '...' : authMode === 'login' ? 'Login' : 'Register'}
                    </button>
                  </div>
                  {error && (
                    <div className="text-[9px] text-red-400">{error}</div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Input — always visible, but disabled if not logged in */}
          <div className="flex gap-2 px-3 py-2 border-t border-border">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder={isLoggedIn ? t('chat_placeholder') : 'Login to chat...'}
              disabled={!isLoggedIn}
              className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-1.5
                         text-[11px] text-text placeholder-text-3
                         focus:outline-none focus:border-white/[0.12] transition-all duration-200
                         disabled:opacity-30"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || !isLoggedIn}
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
