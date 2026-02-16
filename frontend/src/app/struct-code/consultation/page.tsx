'use client'

import { useState, useMemo, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { api, StructCodeConsultResponse, ConsultationSessionSummary, ConsultationSessionDetail } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import { Send, Compass, ArrowLeft, Plus, History, X, MessageSquare } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

function buildInitialPrompt(resident: any, lang: string): string {
  const sr = resident.struct_result
  if (!sr) return ''

  const structCode = sr.struct_code || resident.struct_type || ''
  const birthDate = sr.birth_date || ''

  // Calculate age
  let ageStr = ''
  if (birthDate) {
    try {
      const bd = new Date(birthDate)
      const today = new Date()
      let age = today.getFullYear() - bd.getFullYear()
      if (
        today.getMonth() < bd.getMonth() ||
        (today.getMonth() === bd.getMonth() && today.getDate() < bd.getDate())
      ) {
        age--
      }
      ageStr = `${age}歳`
    } catch {}
  }

  // TOP3 candidates
  const top3 = sr.top_candidates || []
  const top3Lines = top3.slice(0, 3).map((c: any, i: number) => {
    const score = c.score <= 1.0 ? (c.score * 100).toFixed(1) : c.score.toFixed(1)
    return `${i + 1}位: ${c.code}（${c.name}）適合度 ${score}%`
  })

  if (lang === 'en') {
    const lines = [
      `[STRUCT CODE Diagnosis Result]`,
      `Code: ${structCode}`,
      birthDate ? `Birth Date: ${birthDate}${ageStr ? ` (${ageStr})` : ''}` : '',
      '',
      ...(top3Lines.length > 0
        ? [
            `[Type Candidates TOP3]`,
            ...top3.slice(0, 3).map((c: any, i: number) => {
              const score = c.score <= 1.0 ? (c.score * 100).toFixed(1) : c.score.toFixed(1)
              return `#${i + 1}: ${c.code} (${c.name}) Match: ${score}%`
            }),
          ]
        : []),
      '',
      `Based on these results, please tell me about my personality traits and thinking patterns.`,
      `Considering my age, please advise on how to leverage this type's strengths and tips for growth.`,
    ]
    return lines.filter((l) => l !== undefined).join('\n')
  }

  const lines = [
    `【STRUCT CODE診断結果】`,
    `コード: ${structCode}`,
    birthDate ? `生年月日: ${birthDate}${ageStr ? `（${ageStr}）` : ''}` : '',
    '',
    ...(top3Lines.length > 0 ? [`【タイプ候補TOP3】`, ...top3Lines] : []),
    '',
    `上記の診断結果に基づいて、私の性格特性や思考パターンについて教えてください。`,
    `年齢も考慮した上で、このタイプの強みを活かす方法や、成長のためのアドバイスがあればお願いします。`,
  ]
  return lines.filter((l) => l !== undefined).join('\n')
}

function formatDate(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const m = d.getMonth() + 1
  const day = d.getDate()
  const h = d.getHours().toString().padStart(2, '0')
  const min = d.getMinutes().toString().padStart(2, '0')
  return `${m}/${day} ${h}:${min}`
}

export default function ConsultationPage() {
  const router = useRouter()
  const { resident } = useAuthStore()

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [remaining, setRemaining] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [initialized, setInitialized] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessions, setSessions] = useState<ConsultationSessionSummary[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [loadingSessions, setLoadingSessions] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const lang = useMemo(() => {
    if (resident?.struct_result?.lang) return resident.struct_result.lang
    return 'en'
  }, [resident?.struct_result?.lang])

  // Pre-fill input with diagnosis results on first load
  useEffect(() => {
    if (!initialized && resident?.struct_result) {
      const prompt = buildInitialPrompt(resident, lang)
      if (prompt) {
        setInput(prompt)
      }
      setInitialized(true)
    }
  }, [resident, lang, initialized])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
    }
  }, [input])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const loadSessions = useCallback(async () => {
    setLoadingSessions(true)
    try {
      const data = await api.getConsultationSessions()
      setSessions(data)
    } catch {
      // silently fail
    } finally {
      setLoadingSessions(false)
    }
  }, [])

  const loadSession = useCallback(async (id: string) => {
    try {
      const detail: ConsultationSessionDetail = await api.getConsultationSession(id)
      setSessionId(id)
      setMessages(detail.messages.map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content })))
      setShowHistory(false)
      setInput('')
      setError('')
    } catch {
      setError(lang === 'en' ? 'Failed to load session' : 'セッションの読み込みに失敗しました')
    }
  }, [lang])

  const startNewConversation = useCallback(() => {
    setSessionId(null)
    setMessages([])
    setError('')
    setInitialized(false)
    // Re-trigger initial prompt
    if (resident?.struct_result) {
      const prompt = buildInitialPrompt(resident, lang)
      if (prompt) setInput(prompt)
    }
  }, [resident, lang])

  // Redirect if not diagnosed
  if (resident && !resident.struct_type) {
    return (
      <div className="w-full px-4 text-center py-12">
        <Compass size={48} className="text-text-muted mx-auto mb-4" />
        <h2 className="text-xl font-bold text-text-primary mb-2">
          {lang === 'en' ? 'Diagnosis Required' : '診断が必要です'}
        </h2>
        <p className="text-text-secondary mb-6">
          {lang === 'en'
            ? 'Please complete your STRUCT CODE diagnosis first.'
            : 'まずSTRUCT CODE診断を完了してください。'}
        </p>
        <button
          onClick={() => router.push('/struct-code')}
          className="px-6 py-2 bg-accent-gold text-bg-primary font-semibold rounded-lg hover:bg-accent-gold-dim transition-colors"
        >
          {lang === 'en' ? 'Take Diagnosis' : '診断を受ける'}
        </button>
      </div>
    )
  }

  if (!resident) {
    return (
      <div className="w-full px-4 text-center py-12">
        <p className="text-text-secondary">
          {lang === 'en' ? 'Please log in to use the consultation.' : 'ログインしてください。'}
        </p>
      </div>
    )
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const question = input.trim()
    setInput('')
    setError('')
    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setLoading(true)

    try {
      const res: StructCodeConsultResponse = await api.structCodeConsult(
        question,
        lang,
        sessionId || undefined,
      )
      setMessages((prev) => [...prev, { role: 'assistant', content: res.answer }])
      setRemaining(res.remaining_today)
      // Track session for conversation continuation
      if (res.session_id) {
        setSessionId(res.session_id)
      }
    } catch (e: any) {
      const msg = e.message || 'Consultation failed'
      setError(msg)
      // Remove the user message if failed
      setMessages((prev) => prev.slice(0, -1))
      setInput(question)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Ctrl+Enter or Cmd+Enter to send
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSend()
    }
  }

  const natalType = resident.struct_result?.natal?.type_name || ''
  const currentType = resident.struct_result?.current?.type_name || ''
  const displayType = currentType && natalType && currentType !== natalType
    ? `${currentType}（${natalType}）`
    : currentType || natalType || resident.struct_type || ''

  return (
    <div className="w-full px-0 sm:px-4 flex flex-col h-[calc(100vh-5rem)] sm:h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 sm:mb-4 shrink-0">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <button
            onClick={() => router.back()}
            className="text-text-muted hover:text-text-primary transition-colors shrink-0"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="min-w-0">
            <h1 className="text-base sm:text-lg font-bold text-text-primary">AI Counselor</h1>
            <p className="text-text-muted text-xs truncate">
              <span className="text-accent-gold font-mono">{displayType}</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          {remaining !== null && (
            <span className="hidden sm:inline text-text-muted text-xs bg-bg-tertiary px-3 py-1 rounded-full">
              {lang === 'en' ? `${remaining} left today` : `残り${remaining}回/日`}
            </span>
          )}
          <button
            onClick={() => { setShowHistory(!showHistory); if (!showHistory) loadSessions() }}
            className="p-2 text-text-muted hover:text-text-primary transition-colors rounded-lg hover:bg-bg-tertiary"
            title={lang === 'en' ? 'History' : '履歴'}
          >
            <History size={18} />
          </button>
          <button
            onClick={startNewConversation}
            className="p-2 text-text-muted hover:text-accent-gold transition-colors rounded-lg hover:bg-bg-tertiary"
            title={lang === 'en' ? 'New conversation' : '新しい会話'}
          >
            <Plus size={18} />
          </button>
        </div>
      </div>

      {/* History Panel */}
      {showHistory && (
        <div className="mb-4 shrink-0 border border-border-default rounded-lg bg-bg-secondary overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border-default">
            <span className="text-sm font-semibold text-text-primary">
              {lang === 'en' ? 'Past Sessions' : '過去のセッション'}
            </span>
            <button
              onClick={() => setShowHistory(false)}
              className="text-text-muted hover:text-text-primary"
            >
              <X size={16} />
            </button>
          </div>
          <div className="max-h-48 overflow-y-auto">
            {loadingSessions ? (
              <p className="text-text-muted text-xs px-4 py-3">
                {lang === 'en' ? 'Loading...' : '読み込み中...'}
              </p>
            ) : sessions.length === 0 ? (
              <p className="text-text-muted text-xs px-4 py-3">
                {lang === 'en' ? 'No past sessions' : '過去のセッションはありません'}
              </p>
            ) : (
              sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => loadSession(s.id)}
                  className={`w-full text-left px-4 py-2 hover:bg-bg-tertiary transition-colors border-b border-border-default last:border-b-0 ${
                    sessionId === s.id ? 'bg-bg-tertiary' : ''
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <MessageSquare size={14} className="text-text-muted shrink-0" />
                    <span className="text-sm text-text-primary truncate">{s.title}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5 ml-[22px]">
                    <span className="text-xs text-text-muted">
                      {s.message_count} {lang === 'en' ? 'messages' : '件'}
                    </span>
                    <span className="text-xs text-text-muted">{formatDate(s.updated_at)}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <Compass size={40} className="text-text-muted mx-auto mb-3" />
            <p className="text-text-secondary text-sm mb-2">
              {lang === 'en'
                ? 'Your diagnosis results are pre-loaded below.'
                : '診断結果が下の入力欄にセットされています。'}
            </p>
            <p className="text-text-muted text-xs">
              {lang === 'en'
                ? 'Press Ctrl+Enter to send. Edit freely before sending.'
                : 'Ctrl+Enterで送信。自由に編集できます。'}
            </p>
            <p className="text-text-muted text-xs mt-1">
              {lang === 'en' ? '3 consultations per day' : '1日3回まで'}
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] px-4 py-3 rounded-xl text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-accent-gold/20 text-text-primary rounded-br-sm'
                  : 'bg-bg-tertiary text-text-primary border border-border-default rounded-bl-sm'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-bg-tertiary border border-border-default px-4 py-3 rounded-xl rounded-bl-sm">
              <p className="text-text-muted text-xs mb-2">
                {lang === 'en' ? 'Analyzing your structure...' : '構造解析中...'}
              </p>
              <div className="flex gap-1">
                <span
                  className="w-2 h-2 bg-text-muted rounded-full animate-bounce"
                  style={{ animationDelay: '0ms' }}
                />
                <span
                  className="w-2 h-2 bg-text-muted rounded-full animate-bounce"
                  style={{ animationDelay: '150ms' }}
                />
                <span
                  className="w-2 h-2 bg-text-muted rounded-full animate-bounce"
                  style={{ animationDelay: '300ms' }}
                />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error */}
      {error && <p className="text-karma-down text-sm mb-2 shrink-0">{error}</p>}

      {/* Input */}
      <div className="flex gap-2 shrink-0 items-end pb-2 sm:pb-0">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            lang === 'en'
              ? 'Ask about your type...'
              : 'タイプについて質問...'
          }
          disabled={loading || remaining === 0}
          rows={1}
          className="flex-1 px-3 sm:px-4 py-3 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-gold disabled:opacity-50 resize-none text-sm leading-relaxed"
          style={{ maxHeight: '200px' }}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || loading || remaining === 0}
          className="px-3 sm:px-4 py-3 bg-accent-gold text-bg-primary rounded-lg hover:bg-accent-gold-dim transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
