import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ArrowUp,
  ChevronDown,
  ChevronUp,
  LogOut,
  ArrowLeft,
  Plus,
  MessageSquare,
  Pin,
} from 'lucide-react';
import { useBoardStore } from '../../stores/boardStore';
import { useObserverStore } from '../../stores/observerStore';
import { useUIStore } from '../../stores/uiStore';

const CATEGORIES = [
  null,
  'concept_created',
  'artifact_created',
  'organization_formed',
  'ai_death',
];

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSec = Math.floor((now - then) / 1000);
  if (diffSec < 60) return `${diffSec}s`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d`;
}

function categoryLabel(cat: string | null): string {
  if (!cat) return '';
  const labels: Record<string, string> = {
    concept_created: 'Concept',
    artifact_created: 'Artifact',
    organization_formed: 'Org',
    ai_death: 'Death',
  };
  return labels[cat] || cat;
}

function categoryColor(cat: string | null): string {
  if (!cat) return 'text-text-3';
  const colors: Record<string, string> = {
    concept_created: 'bg-cyan/20 text-cyan',
    artifact_created: 'bg-rose-400/20 text-rose-400',
    organization_formed: 'bg-violet-400/20 text-violet-400',
    ai_death: 'bg-amber-400/20 text-amber-400',
  };
  return colors[cat] || 'bg-white/[0.06] text-text-3';
}

export default function BoardPanel() {
  const { t } = useTranslation();
  const {
    threads,
    currentThread,
    view,
    categoryFilter,
    loading,
    setView,
    setCategoryFilter,
    fetchThreads,
    fetchThread,
    createThread,
    createReply,
  } = useBoardStore();
  const { token, username, isLoggedIn, login, register, logout, error, loading: authLoading } = useObserverStore();
  const { observerChatExpanded, toggleObserverChat } = useUIStore();

  const [replyInput, setReplyInput] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [newBody, setNewBody] = useState('');
  const [newCategory, setNewCategory] = useState('');
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authUser, setAuthUser] = useState('');
  const [authPass, setAuthPass] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  // Fetch threads on expand
  useEffect(() => {
    if (observerChatExpanded && view === 'list') {
      fetchThreads();
    }
  }, [observerChatExpanded, view, categoryFilter, fetchThreads]);

  // Scroll to bottom when viewing detail (use block: 'nearest' to avoid shifting parent)
  useEffect(() => {
    if (view === 'detail' && currentThread && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [currentThread?.replies?.length, view]);

  const handleAuth = async () => {
    if (!authUser.trim() || !authPass.trim()) return;
    const success = authMode === 'login'
      ? await login(authUser, authPass)
      : await register(authUser, authPass);
    if (success) {
      setAuthUser('');
      setAuthPass('');
    }
  };

  const handleCreateThread = async () => {
    if (!newTitle.trim() || !token) return;
    const ok = await createThread(token, newTitle.trim(), newBody.trim() || undefined, newCategory.trim() || undefined);
    if (ok) {
      setNewTitle('');
      setNewBody('');
      setNewCategory('');
    }
  };

  const handleReply = async () => {
    if (!replyInput.trim() || !token || !currentThread) return;
    await createReply(token, currentThread.id, replyInput.trim());
    setReplyInput('');
  };

  const openThread = (id: string) => {
    fetchThread(id);
  };

  const goBack = () => {
    setView('list');
    fetchThreads();
  };

  const threadCount = threads.length;

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
                {t('board_title')}
              </span>
              {isLoggedIn && username && (
                <span className="text-[9px] text-cyan">{username}</span>
              )}
              {threadCount > 0 && (
                <span className="badge bg-accent-dim text-accent text-[8px]">{threadCount}</span>
              )}
            </div>
            {observerChatExpanded ? <ChevronDown size={12} className="text-text-3" /> : <ChevronUp size={12} className="text-text-3" />}
          </button>

          {/* Expandable content */}
          {observerChatExpanded && (
            <div className="fade-in">
              {/* === LIST VIEW === */}
              {view === 'list' && (
                <>
                  {/* Category filter + actions */}
                  <div className="flex items-center gap-1.5 px-4 py-1.5 border-b border-border">
                    {CATEGORIES.map((cat) => (
                      <button
                        key={cat ?? 'all'}
                        onClick={() => setCategoryFilter(cat)}
                        className={`px-2 py-0.5 rounded-lg text-[9px] transition-all duration-150 ${
                          categoryFilter === cat
                            ? 'bg-white/[0.06] text-text shadow-[0_0_0_1px_rgba(255,255,255,0.06)]'
                            : 'text-text-3 hover:text-text-2'
                        }`}
                      >
                        {cat === null ? t('board_category_all') : categoryLabel(cat)}
                      </button>
                    ))}
                    <div className="flex-1" />
                    {isLoggedIn && (
                      <>
                        <button
                          onClick={() => setView('create')}
                          className="flex items-center gap-1 px-2 py-0.5 rounded-lg text-[9px] text-cyan hover:bg-cyan/10 transition-all"
                        >
                          <Plus size={9} />
                          {t('board_new_thread')}
                        </button>
                        <button
                          onClick={logout}
                          className="text-text-3 hover:text-text-2 transition-colors"
                          title="Logout"
                        >
                          <LogOut size={10} />
                        </button>
                      </>
                    )}
                  </div>

                  {/* Thread list (2ch-style compact) */}
                  <div className="h-48 overflow-y-auto">
                    {threads.length === 0 && (
                      <div className="text-center text-text-3 text-[10px] py-6">
                        {loading ? '...' : t('board_no_threads')}
                      </div>
                    )}
                    {threads.map((thread, idx) => (
                      <button
                        key={thread.id}
                        onClick={() => openThread(thread.id)}
                        className="w-full text-left px-4 py-1.5 border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors flex items-center gap-2"
                      >
                        {thread.is_pinned && <Pin size={8} className="text-amber-400 flex-shrink-0" />}
                        <span className="text-[11px] text-text truncate flex-1">
                          {thread.title}
                        </span>
                        {thread.category && (
                          <span className={`flex-shrink-0 px-1.5 py-0 rounded text-[8px] ${categoryColor(thread.category)}`}>
                            {categoryLabel(thread.category)}
                          </span>
                        )}
                        <span className="flex-shrink-0 flex items-center gap-0.5 text-[9px] text-text-3">
                          <MessageSquare size={8} />
                          {thread.reply_count}
                        </span>
                        <span className="flex-shrink-0 text-[8px] text-text-3 w-8 text-right">
                          {timeAgo(thread.last_reply_at || thread.created_at)}
                        </span>
                      </button>
                    ))}
                  </div>

                  {/* Auth form when not logged in */}
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
                          disabled={authLoading || !authUser.trim() || !authPass.trim()}
                          className="px-3 py-1 rounded-lg bg-white/[0.06] text-[10px] text-text
                                     hover:bg-white/[0.1] transition-all duration-200
                                     disabled:opacity-30"
                        >
                          {authLoading ? '...' : authMode === 'login' ? 'Login' : 'Register'}
                        </button>
                      </div>
                      {error && (
                        <div className="text-[9px] text-red-400">{error}</div>
                      )}
                    </div>
                  )}
                </>
              )}

              {/* === DETAIL VIEW === */}
              {view === 'detail' && currentThread && (
                <>
                  {/* Header with back button */}
                  <div className="flex items-center gap-2 px-4 py-1.5 border-b border-border">
                    <button
                      onClick={goBack}
                      className="text-text-3 hover:text-text transition-colors"
                    >
                      <ArrowLeft size={12} />
                    </button>
                    <span className="text-[11px] text-text font-medium truncate flex-1">
                      {currentThread.title}
                    </span>
                    {currentThread.category && (
                      <span className={`flex-shrink-0 px-1.5 py-0 rounded text-[8px] ${categoryColor(currentThread.category)}`}>
                        {categoryLabel(currentThread.category)}
                      </span>
                    )}
                  </div>

                  {/* Thread body + replies */}
                  <div className="h-48 overflow-y-auto px-4 py-2 space-y-1.5">
                    {/* OP */}
                    <div className="pb-1.5 border-b border-white/[0.04]">
                      <div className="flex items-center gap-1.5 text-[9px] text-text-3 mb-0.5">
                        <span className="font-medium text-cyan">
                          {currentThread.author_name || currentThread.author_type.toUpperCase()}
                        </span>
                        <span>&middot;</span>
                        <span>{timeAgo(currentThread.created_at)}</span>
                      </div>
                      {currentThread.body && (
                        <div className="text-[11px] text-text-2 whitespace-pre-wrap">{currentThread.body}</div>
                      )}
                    </div>

                    {/* Replies */}
                    {currentThread.replies.length === 0 && (
                      <div className="text-center text-text-3 text-[10px] py-3">{t('board_no_replies')}</div>
                    )}
                    {currentThread.replies.map((reply, idx) => (
                      <div key={reply.id} className="py-1 text-[11px]">
                        <div className="flex items-center gap-1.5 text-[9px] text-text-3 mb-0.5">
                          <span className="text-text-3 font-mono">{idx + 1}</span>
                          <span className="font-medium text-cyan">
                            {reply.author_name || reply.author_type.toUpperCase()}
                          </span>
                          <span>&middot;</span>
                          <span>{timeAgo(reply.created_at)}</span>
                        </div>
                        <div className="text-text-2 pl-4">{reply.content}</div>
                      </div>
                    ))}
                    <div ref={bottomRef} />
                  </div>

                  {/* Reply input */}
                  <div className="flex gap-2 px-3 py-2 border-t border-border">
                    <input
                      type="text"
                      value={replyInput}
                      onChange={(e) => setReplyInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleReply()}
                      placeholder={isLoggedIn ? t('board_reply') + '...' : t('board_login_required')}
                      disabled={!isLoggedIn}
                      className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-1.5
                                 text-[11px] text-text placeholder-text-3
                                 focus:outline-none focus:border-white/[0.12] transition-all duration-200
                                 disabled:opacity-30"
                    />
                    <button
                      onClick={handleReply}
                      disabled={!replyInput.trim() || !isLoggedIn || loading}
                      className="w-7 h-7 flex items-center justify-center rounded-lg
                                 hover:bg-white/[0.06] text-text-2 transition-all duration-200
                                 disabled:opacity-15"
                    >
                      <ArrowUp size={12} />
                    </button>
                  </div>
                </>
              )}

              {/* === CREATE VIEW === */}
              {view === 'create' && (
                <>
                  <div className="flex items-center gap-2 px-4 py-1.5 border-b border-border">
                    <button
                      onClick={goBack}
                      className="text-text-3 hover:text-text transition-colors"
                    >
                      <ArrowLeft size={12} />
                    </button>
                    <span className="text-[11px] text-text font-medium">
                      {t('board_new_thread')}
                    </span>
                  </div>

                  <div className="px-4 py-2 space-y-2">
                    <input
                      type="text"
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      placeholder={t('board_thread_title')}
                      className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-1.5
                                 text-[11px] text-text placeholder-text-3
                                 focus:outline-none focus:border-white/[0.12] transition-all duration-200"
                    />
                    <textarea
                      value={newBody}
                      onChange={(e) => setNewBody(e.target.value)}
                      placeholder={t('board_thread_body')}
                      rows={3}
                      className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-1.5
                                 text-[11px] text-text placeholder-text-3 resize-none
                                 focus:outline-none focus:border-white/[0.12] transition-all duration-200"
                    />
                    <input
                      type="text"
                      value={newCategory}
                      onChange={(e) => setNewCategory(e.target.value)}
                      placeholder={t('board_thread_category')}
                      className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-1.5
                                 text-[11px] text-text placeholder-text-3
                                 focus:outline-none focus:border-white/[0.12] transition-all duration-200"
                    />
                    <button
                      onClick={handleCreateThread}
                      disabled={!newTitle.trim() || loading}
                      className="w-full py-1.5 rounded-lg bg-white/[0.06] text-[11px] text-text font-medium
                                 hover:bg-white/[0.1] transition-all duration-200
                                 disabled:opacity-30"
                    >
                      {loading ? t('board_posting') : t('board_create')}
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
