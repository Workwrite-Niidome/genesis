'use client'

import { useState, useMemo, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { api, StructCodeConsultResponse } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import { Send, Compass, ArrowLeft } from 'lucide-react'

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

export default function ConsultationPage() {
  const router = useRouter()
  const { resident } = useAuthStore()

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [remaining, setRemaining] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [initialized, setInitialized] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const lang = useMemo(() => {
    if (typeof navigator === 'undefined') return 'ja'
    return navigator.language.startsWith('ja') ? 'ja' : 'en'
  }, [])

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

  // Redirect if not diagnosed
  if (resident && !resident.struct_type) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
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
      <div className="max-w-2xl mx-auto p-6 text-center">
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
      const res: StructCodeConsultResponse = await api.structCodeConsult(question, lang)
      setMessages((prev) => [...prev, { role: 'assistant', content: res.answer }])
      setRemaining(res.remaining_today)
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
    <div className="max-w-2xl mx-auto p-6 flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="text-text-muted hover:text-text-primary transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-lg font-bold text-text-primary">AI Counselor</h1>
            <p className="text-text-muted text-xs">
              STRUCT CODE:{' '}
              <span className="text-accent-gold font-mono">{displayType}</span>
            </p>
          </div>
        </div>
        {remaining !== null && (
          <span className="text-text-muted text-xs bg-bg-tertiary px-3 py-1 rounded-full">
            {lang === 'en' ? `${remaining} left today` : `残り${remaining}回/日`}
          </span>
        )}
      </div>

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
      <div className="flex gap-2 shrink-0 items-end">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            lang === 'en'
              ? 'Ask about your type... (Ctrl+Enter to send)'
              : 'タイプについて質問... (Ctrl+Enterで送信)'
          }
          disabled={loading || remaining === 0}
          rows={1}
          className="flex-1 px-4 py-3 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-gold disabled:opacity-50 resize-none text-sm leading-relaxed"
          style={{ maxHeight: '200px' }}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || loading || remaining === 0}
          className="px-4 py-3 bg-accent-gold text-bg-primary rounded-lg hover:bg-accent-gold-dim transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
