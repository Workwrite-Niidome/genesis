'use client'

import { useState, useEffect, useRef } from 'react'
import { api, PhantomChatMessage } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import clsx from 'clsx'
import { MessageCircle, Send, AlertCircle } from 'lucide-react'

export default function PhantomChat() {
  const { resident } = useAuthStore()
  const [messages, setMessages] = useState<PhantomChatMessage[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const prevCountRef = useRef(0)

  const fetchMessages = async (initial = false) => {
    try {
      if (initial) setIsLoading(true)
      setError(null)
      const response = await api.werewolfPhantomChat()
      const newCount = response.messages.length
      setMessages(response.messages)
      // Only auto-scroll when new messages arrive (not on every poll)
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
    const interval = setInterval(() => fetchMessages(false), 10000)
    return () => clearInterval(interval)
  }, [])

  const handleSend = async () => {
    if (!newMessage.trim()) return

    setIsSending(true)
    setError(null)

    try {
      await api.werewolfSendPhantomChat(newMessage.trim())
      setNewMessage('')
      // Immediately fetch updated messages
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
    <Card className="p-4 border-purple-500/50 bg-gradient-to-br from-purple-900/10 to-violet-900/10 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4 pb-4 border-b border-purple-500/30">
        <div className="p-2 rounded-lg bg-purple-500/20 text-purple-400">
          <MessageCircle size={20} />
        </div>
        <div>
          <h3 className="text-lg font-bold text-text-primary">Phantom Team Chat</h3>
          <p className="text-xs text-text-secondary">Secret channel for phantoms only</p>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/20 text-red-400 border border-red-500/30 flex items-center gap-2">
          <AlertCircle size={18} />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 mb-4 min-h-0">
        {isLoading && messages.length === 0 ? (
          <div className="text-center py-8 text-text-muted">
            <div className="animate-spin w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full mx-auto mb-2" />
            <p className="text-sm">Loading messages...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-8 text-text-muted">
            <MessageCircle size={32} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">No messages yet. Start the conversation!</p>
          </div>
        ) : (
          messages.map((msg) => {
            const isOwnMessage = msg.sender_id === resident?.id

            return (
              <div
                key={msg.id}
                className={clsx('flex', isOwnMessage ? 'justify-end' : 'justify-start')}
              >
                <div
                  className={clsx(
                    'max-w-[75%] rounded-lg p-3',
                    isOwnMessage
                      ? 'bg-purple-500/30 border border-purple-500/50'
                      : 'bg-bg-tertiary border border-border-default'
                  )}
                >
                  {!isOwnMessage && (
                    <p className="text-xs font-semibold text-purple-400 mb-1">
                      {msg.sender_name}
                    </p>
                  )}
                  <p className="text-sm text-text-primary whitespace-pre-wrap break-words">
                    {msg.message}
                  </p>
                  <p className="text-xs text-text-muted mt-1">
                    {new Date(msg.created_at).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              </div>
            )
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <textarea
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Send a message to your team..."
          className="flex-1 px-3 py-2 bg-bg-tertiary border border-purple-500/30 rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
          rows={2}
          maxLength={500}
          disabled={isSending}
        />
        <Button
          onClick={handleSend}
          disabled={!newMessage.trim() || isSending}
          isLoading={isSending}
          variant="primary"
          className="self-end bg-purple-500 hover:bg-purple-600"
        >
          <Send size={18} />
        </Button>
      </div>
      <p className="text-xs text-text-muted mt-1">{newMessage.length} / 500</p>
    </Card>
  )
}
