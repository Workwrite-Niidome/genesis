'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { api, StructCodeConsultResponse } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import { Send, Compass, ArrowLeft } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function ConsultationPage() {
  const router = useRouter()
  const { resident } = useAuthStore()

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [remaining, setRemaining] = useState<number | null>(null)
  const [error, setError] = useState('')

  // Redirect if not diagnosed
  if (resident && !resident.struct_type) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <Compass size={48} className="text-text-muted mx-auto mb-4" />
        <h2 className="text-xl font-bold text-text-primary mb-2">Diagnosis Required</h2>
        <p className="text-text-secondary mb-6">
          Please complete your STRUCT CODE diagnosis first.
        </p>
        <button
          onClick={() => router.push('/struct-code')}
          className="px-6 py-2 bg-accent-gold text-bg-primary font-semibold rounded-lg hover:bg-accent-gold-dim transition-colors"
        >
          Take Diagnosis
        </button>
      </div>
    )
  }

  if (!resident) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <p className="text-text-secondary">Please log in to use the consultation.</p>
      </div>
    )
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const question = input.trim()
    setInput('')
    setError('')
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setLoading(true)

    try {
      const res: StructCodeConsultResponse = await api.structCodeConsult(question)
      setMessages(prev => [...prev, { role: 'assistant', content: res.answer }])
      setRemaining(res.remaining_today)
    } catch (e: any) {
      const msg = e.message || 'Consultation failed'
      setError(msg)
      // Remove the user message if failed
      setMessages(prev => prev.slice(0, -1))
      setInput(question)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6 flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/struct-code')}
            className="text-text-muted hover:text-text-primary transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-lg font-bold text-text-primary">AI Counselor</h1>
            <p className="text-text-muted text-xs">
              STRUCT CODE: <span className="text-accent-gold font-mono">{resident.struct_type}</span>
            </p>
          </div>
        </div>
        {remaining !== null && (
          <span className="text-text-muted text-xs bg-bg-tertiary px-3 py-1 rounded-full">
            {remaining} left today
          </span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <Compass size={40} className="text-text-muted mx-auto mb-3" />
            <p className="text-text-secondary text-sm">
              Ask about your personality type, decision-making patterns, relationships, or personal growth.
            </p>
            <p className="text-text-muted text-xs mt-2">
              3 consultations per day
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] px-4 py-3 rounded-xl text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-accent-gold/20 text-text-primary rounded-br-sm'
                  : 'bg-bg-tertiary text-text-primary border border-border-default rounded-bl-sm'
              }`}
            >
              {msg.content.split('\n').map((line, j) => (
                <p key={j} className={j > 0 ? 'mt-2' : ''}>
                  {line}
                </p>
              ))}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-bg-tertiary border border-border-default px-4 py-3 rounded-xl rounded-bl-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <p className="text-karma-down text-sm mb-2 shrink-0">{error}</p>
      )}

      {/* Input */}
      <div className="flex gap-2 shrink-0">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Ask about your type..."
          disabled={loading || remaining === 0}
          className="flex-1 px-4 py-3 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-gold disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || loading || remaining === 0}
          className="px-4 py-3 bg-accent-gold text-bg-primary rounded-lg hover:bg-accent-gold-dim transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
