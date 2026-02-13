'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { api, ChatMessage } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import clsx from 'clsx'
import { Send, MessageCircle, Info } from 'lucide-react'

interface ChatWindowProps {
  refreshTrigger?: number
  onMessageSent?: () => void
  isDay: boolean
  isAlive: boolean
}

export default function ChatWindow({ refreshTrigger, onMessageSent, isDay, isAlive }: ChatWindowProps) {
  const { resident } = useAuthStore()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const prevCountRef = useRef(0)
  const isAtBottomRef = useRef(true)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const checkAtBottom = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 60
  }, [])

  const fetchMessages = useCallback(async (initial = false) => {
    try {
      if (initial) setLoading(true)
      const data = await api.werewolfChatHistory(200)
      const newCount = data.length
      setMessages(data)
      if (newCount > prevCountRef.current && isAtBottomRef.current) {
        setTimeout(scrollToBottom, 50)
      }
      prevCountRef.current = newCount
    } catch {
      // silent
    } finally {
      if (initial) setLoading(false)
    }
  }, [scrollToBottom])

  useEffect(() => {
    fetchMessages(true)
    const interval = setInterval(() => fetchMessages(false), 15000)
    return () => clearInterval(interval)
  }, [fetchMessages])

  // WebSocket-triggered refresh
  useEffect(() => {
    if (refreshTrigger && refreshTrigger > 0) {
      fetchMessages(false)
    }
  }, [refreshTrigger, fetchMessages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isSending) return

    setIsSending(true)
    setError(null)

    try {
      await api.werewolfSendChat(text)
      setInput('')
      await fetchMessages(false)
      onMessageSent?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send')
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const canSend = isDay && isAlive && !!resident

  return (
    <div className="flex flex-col h-full bg-bg-secondary border border-border-default rounded-lg overflow-hidden">
      {/* Messages */}
      <div
        ref={containerRef}
        onScroll={checkAtBottom}
        className="flex-1 overflow-y-auto p-4 space-y-2 min-h-0"
      >
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-text-muted">
            <MessageCircle size={32} className="opacity-50 mb-2" />
            <p className="text-sm">No messages yet</p>
          </div>
        ) : (
          messages.map((msg) => {
            if (msg.message_type === 'system') {
              return (
                <div key={msg.id} className="flex justify-center py-1">
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-bg-tertiary text-text-muted text-xs max-w-[85%]">
                    <Info size={12} className="flex-shrink-0" />
                    <span>{msg.content}</span>
                  </div>
                </div>
              )
            }

            const isOwn = msg.sender_id === resident?.id

            return (
              <div key={msg.id} className={clsx('flex', isOwn ? 'justify-end' : 'justify-start')}>
                <div
                  className={clsx(
                    'max-w-[75%] rounded-lg px-3 py-2',
                    isOwn
                      ? 'bg-purple-600/30 border border-purple-500/40'
                      : 'bg-bg-tertiary border border-border-default'
                  )}
                >
                  {!isOwn && (
                    <p className="text-xs font-semibold text-purple-400 mb-0.5">{msg.sender_name}</p>
                  )}
                  <p className="text-sm text-text-primary whitespace-pre-wrap break-words">{msg.content}</p>
                  <p className="text-[10px] text-text-muted mt-0.5 text-right">
                    {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            )
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="px-4 py-2 bg-red-500/10 border-t border-red-500/30 text-red-400 text-xs">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="border-t border-border-default p-3">
        {!canSend ? (
          <div className="text-center text-xs text-text-muted py-1">
            {!resident
              ? 'Log in to chat'
              : !isAlive
                ? 'You have been eliminated'
                : 'Chat is available during the day phase'}
          </div>
        ) : (
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Send a message..."
              className="flex-1 px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-sm text-text-primary placeholder-text-muted focus:outline-none focus:ring-1 focus:ring-purple-500 resize-none"
              rows={1}
              maxLength={500}
              disabled={isSending}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isSending}
              className="self-end px-3 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-40 disabled:hover:bg-purple-600 text-white rounded-lg transition-colors"
            >
              <Send size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
