'use client'

import { useState, useEffect, useRef } from 'react'
import { api, PhantomChatMessage } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import clsx from 'clsx'
import { MessageCircle, Send, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'

interface PhantomChatProps {
  refreshTrigger?: number
  compact?: boolean
}

export default function PhantomChat({ refreshTrigger, compact }: PhantomChatProps) {
  const { resident } = useAuthStore()
  const [messages, setMessages] = useState<PhantomChatMessage[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [collapsed, setCollapsed] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const prevCountRef = useRef(0)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const fetchMessages = async (initial = false) => {
    try {
      if (initial) setIsLoading(true)
      setError(null)
      const response = await api.werewolfPhantomChat()
      const newCount = response.messages.length
      setMessages(response.messages)
      if (newCount > prevCountRef.current) {
        setTimeout(() => scrollToBottom(), 50)
      }
      prevCountRef.current = newCount
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load messages')
    } finally {
      if (initial) setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchMessages(true)
    const interval = setInterval(() => fetchMessages(false), 15000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (refreshTrigger && refreshTrigger > 0) {
      fetchMessages(false)
    }
  }, [refreshTrigger])

  const handleSend = async () => {
    if (!newMessage.trim()) return
    setIsSending(true)
    setError(null)
    try {
      await api.werewolfSendPhantomChat(newMessage.trim())
      setNewMessage('')
      await fetchMessages()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
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

  return (
    <div className="rounded-lg border border-purple-500/40 bg-purple-900/10 overflow-hidden">
      {/* Header - clickable to collapse/expand */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-purple-900/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <MessageCircle size={16} className="text-purple-400" />
          <span className="text-sm font-bold text-text-primary">Phantom Chat</span>
          {messages.length > 0 && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400">
              {messages.length}
            </span>
          )}
        </div>
        {collapsed ? <ChevronDown size={16} className="text-text-muted" /> : <ChevronUp size={16} className="text-text-muted" />}
      </button>

      {!collapsed && (
        <div className="border-t border-purple-500/30">
          {/* Error */}
          {error && (
            <div className="px-3 py-2 bg-red-500/10 text-red-400 text-xs flex items-center gap-1.5">
              <AlertCircle size={14} />
              <span>{error}</span>
            </div>
          )}

          {/* Messages */}
          <div className="overflow-y-auto space-y-2 p-3 max-h-48">
            {isLoading && messages.length === 0 ? (
              <div className="text-center py-4 text-text-muted text-xs">Loading...</div>
            ) : messages.length === 0 ? (
              <div className="text-center py-4 text-text-muted text-xs">No messages yet</div>
            ) : (
              messages.map((msg) => {
                const isOwn = msg.sender_id === resident?.id
                return (
                  <div key={msg.id} className={clsx('flex', isOwn ? 'justify-end' : 'justify-start')}>
                    <div
                      className={clsx(
                        'max-w-[80%] rounded-lg px-2.5 py-1.5',
                        isOwn
                          ? 'bg-purple-500/30 border border-purple-500/50'
                          : 'bg-bg-tertiary border border-border-default'
                      )}
                    >
                      {!isOwn && (
                        <p className="text-[10px] font-semibold text-purple-400 mb-0.5">{msg.sender_name}</p>
                      )}
                      <p className="text-xs text-text-primary whitespace-pre-wrap break-words">{msg.message}</p>
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

          {/* Input */}
          <div className="border-t border-purple-500/30 p-2 flex gap-2">
            <textarea
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Team message..."
              className="flex-1 px-2 py-1.5 bg-bg-tertiary border border-purple-500/30 rounded text-xs text-text-primary placeholder-text-muted focus:outline-none focus:ring-1 focus:ring-purple-500 resize-none"
              rows={1}
              maxLength={500}
              disabled={isSending}
            />
            <button
              onClick={handleSend}
              disabled={!newMessage.trim() || isSending}
              className="self-end px-2 py-1.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white rounded transition-colors"
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
