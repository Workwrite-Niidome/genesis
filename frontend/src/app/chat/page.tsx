'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAuthStore } from '@/stores/authStore'
import {
  Send, Plus, MessageSquare, Menu, X, Trash2, Loader2, Compass,
} from 'lucide-react'
import Link from 'next/link'

const DIFY_API_URL = 'https://api.dify.ai/v1/chat-messages'
const DIFY_API_KEY = 'BfeKg4QYX511bD3a'
const STORAGE_KEY = 'struct-code-conversations'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

interface Conversation {
  id: string
  title: string
  conversation_id: string | null // Dify conversation_id
  messages: ChatMessage[]
  created_at: number
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

function loadConversations(): Conversation[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveConversations(convos: Conversation[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(convos))
}

function formatTimestamp(ts: number): string {
  const d = new Date(ts)
  const m = d.getMonth() + 1
  const day = d.getDate()
  const h = d.getHours().toString().padStart(2, '0')
  const min = d.getMinutes().toString().padStart(2, '0')
  return `${m}/${day} ${h}:${min}`
}

// Simple markdown-like rendering (bold, italic, code, newlines)
function renderMarkdown(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/```([\s\S]*?)```/g, '<pre class="bg-bg-primary rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono"><code>$1</code></pre>')
    .replace(/`([^`]+)`/g, '<code class="bg-bg-primary px-1.5 py-0.5 rounded text-xs font-mono text-accent-gold">$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>')
}

export default function ChatPage() {
  const searchParams = useSearchParams()
  const { resident } = useAuthStore()
  const structCode = searchParams.get('struct_code') || ''

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [initialized, setInitialized] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const streamingContentRef = useRef('')

  // Load conversations from localStorage
  useEffect(() => {
    const loaded = loadConversations()
    setConversations(loaded)

    // If struct_code param, start new conversation with context
    if (structCode) {
      const newConvo: Conversation = {
        id: generateId(),
        title: `STRUCT CODE: ${structCode}`,
        conversation_id: null,
        messages: [],
        created_at: Date.now(),
      }
      const updated = [newConvo, ...loaded]
      setConversations(updated)
      setActiveId(newConvo.id)
      saveConversations(updated)
      // Pre-fill input with struct code context
      setInput(buildStructCodePrompt(structCode, resident))
    } else if (loaded.length > 0) {
      setActiveId(loaded[0].id)
    }
    setInitialized(true)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversations, activeId, streaming])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  }, [input])

  const activeConvo = conversations.find(c => c.id === activeId) || null

  const updateConversation = useCallback((id: string, updater: (c: Conversation) => Conversation) => {
    setConversations(prev => {
      const updated = prev.map(c => c.id === id ? updater(c) : c)
      saveConversations(updated)
      return updated
    })
  }, [])

  const startNewConversation = useCallback(() => {
    const newConvo: Conversation = {
      id: generateId(),
      title: 'New conversation',
      conversation_id: null,
      messages: [],
      created_at: Date.now(),
    }
    setConversations(prev => {
      const updated = [newConvo, ...prev]
      saveConversations(updated)
      return updated
    })
    setActiveId(newConvo.id)
    setInput('')
    setSidebarOpen(false)
  }, [])

  const deleteConversation = useCallback((id: string) => {
    setConversations(prev => {
      const updated = prev.filter(c => c.id !== id)
      saveConversations(updated)
      if (activeId === id) {
        setActiveId(updated.length > 0 ? updated[0].id : null)
      }
      return updated
    })
  }, [activeId])

  const selectConversation = useCallback((id: string) => {
    setActiveId(id)
    setSidebarOpen(false)
  }, [])

  const handleSend = async () => {
    if (!input.trim() || streaming || !activeId) return

    const question = input.trim()
    setInput('')

    // Add user message
    const userMsg: ChatMessage = { role: 'user', content: question, timestamp: Date.now() }
    updateConversation(activeId, c => ({
      ...c,
      messages: [...c.messages, userMsg],
      title: c.messages.length === 0 ? question.slice(0, 40) : c.title,
    }))

    setStreaming(true)
    streamingContentRef.current = ''

    try {
      const body: any = {
        inputs: structCode ? { struct_code: structCode } : {},
        query: question,
        response_mode: 'streaming',
        user: resident?.name || 'anonymous',
      }

      if (activeConvo?.conversation_id) {
        body.conversation_id = activeConvo.conversation_id
      }

      const response = await fetch(DIFY_API_URL, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer app-${DIFY_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        const errText = await response.text()
        throw new Error(`API error: ${response.status} ${errText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let difyConversationId: string | null = activeConvo?.conversation_id || null
      let buffer = ''

      // Add placeholder assistant message
      const assistantMsg: ChatMessage = { role: 'assistant', content: '', timestamp: Date.now() }
      updateConversation(activeId, c => ({
        ...c,
        messages: [...c.messages, assistantMsg],
      }))

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const jsonStr = line.slice(6).trim()
          if (!jsonStr) continue

          try {
            const event = JSON.parse(jsonStr)

            if (event.event === 'message' || event.event === 'agent_message') {
              streamingContentRef.current += event.answer || ''
              const currentContent = streamingContentRef.current
              updateConversation(activeId, c => {
                const msgs = [...c.messages]
                msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content: currentContent }
                return { ...c, messages: msgs }
              })
            }

            if (event.conversation_id && !difyConversationId) {
              difyConversationId = event.conversation_id
              updateConversation(activeId, c => ({ ...c, conversation_id: difyConversationId }))
            }

            if (event.event === 'message_end') {
              // Final update
              if (event.metadata?.usage) {
                // Could track token usage here
              }
            }

            if (event.event === 'error') {
              throw new Error(event.message || 'Stream error')
            }
          } catch (parseErr) {
            // Skip non-JSON lines
          }
        }
      }
    } catch (err: any) {
      const errorMsg = err.message || 'Failed to send message'
      updateConversation(activeId, c => {
        const msgs = [...c.messages]
        // Update or add error message
        if (msgs.length > 0 && msgs[msgs.length - 1].role === 'assistant' && !msgs[msgs.length - 1].content) {
          msgs[msgs.length - 1] = { role: 'assistant', content: `Error: ${errorMsg}`, timestamp: Date.now() }
        } else {
          msgs.push({ role: 'assistant', content: `Error: ${errorMsg}`, timestamp: Date.now() })
        }
        return { ...c, messages: msgs }
      })
    } finally {
      setStreaming(false)
      streamingContentRef.current = ''
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!initialized) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="animate-spin text-accent-gold" size={32} />
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-5rem)] sm:h-[calc(100vh-8rem)] -mx-2 sm:-mx-4">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0 fixed md:relative z-40 md:z-auto top-0 md:top-auto left-0 md:left-auto h-full w-64 md:w-60 shrink-0 bg-bg-secondary border-r border-border-default flex flex-col transition-transform duration-300 md:transition-none`}
      >
        {/* Sidebar header */}
        <div className="flex items-center justify-between p-3 border-b border-border-default shrink-0">
          <h2 className="text-sm font-semibold text-text-primary">AI Chat</h2>
          <div className="flex items-center gap-1">
            <button
              onClick={startNewConversation}
              className="p-1.5 text-text-muted hover:text-accent-gold transition-colors rounded-md hover:bg-bg-tertiary"
              title="New conversation"
            >
              <Plus size={16} />
            </button>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-1.5 text-text-muted hover:text-text-primary md:hidden rounded-md hover:bg-bg-tertiary"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <p className="text-text-muted text-xs p-4">No conversations yet</p>
          ) : (
            conversations.map(c => (
              <div
                key={c.id}
                className={`group flex items-center gap-2 px-3 py-2.5 cursor-pointer border-b border-border-default/50 transition-colors ${
                  activeId === c.id ? 'bg-bg-tertiary' : 'hover:bg-bg-tertiary/50'
                }`}
                onClick={() => selectConversation(c.id)}
              >
                <MessageSquare size={14} className="text-text-muted shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary truncate">{c.title}</p>
                  <p className="text-[10px] text-text-muted">
                    {c.messages.length} msgs · {formatTimestamp(c.created_at)}
                  </p>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteConversation(c.id) }}
                  className="opacity-0 group-hover:opacity-100 p-1 text-text-muted hover:text-karma-down transition-all shrink-0"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))
          )}
        </div>

        {/* Sidebar footer */}
        <div className="p-3 border-t border-border-default shrink-0">
          <Link
            href="/struct-code"
            className="flex items-center gap-2 text-xs text-text-muted hover:text-accent-gold transition-colors"
          >
            <Compass size={14} />
            STRUCT CODE
          </Link>
        </div>
      </aside>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat header */}
        <div className="flex items-center gap-2 px-3 sm:px-4 py-2 border-b border-border-default shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-1.5 text-text-muted hover:text-text-primary md:hidden rounded-md hover:bg-bg-tertiary"
          >
            <Menu size={18} />
          </button>
          <h1 className="text-sm font-semibold text-text-primary truncate">
            {activeConvo?.title || 'AI Chat'}
          </h1>
          {structCode && (
            <span className="text-[10px] text-accent-gold font-mono bg-accent-gold/10 px-2 py-0.5 rounded shrink-0">
              {structCode}
            </span>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-3 sm:px-4 py-4 space-y-4">
          {!activeConvo || activeConvo.messages.length === 0 ? (
            <div className="text-center py-12">
              <Compass size={48} className="text-text-muted mx-auto mb-4" />
              <p className="text-text-secondary text-sm mb-2">
                STRUCT CODE AI Chat
              </p>
              <p className="text-text-muted text-xs">
                Ask anything about your personality type, growth path, and more.
              </p>
              {structCode && (
                <p className="text-accent-gold text-xs mt-2 font-mono">
                  Code: {structCode}
                </p>
              )}
            </div>
          ) : (
            activeConvo.messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[88%] sm:max-w-[80%] px-3.5 py-2.5 rounded-xl text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-accent-gold/20 text-text-primary rounded-br-sm'
                      : 'bg-bg-tertiary text-text-primary border border-border-default rounded-bl-sm'
                  }`}
                >
                  {msg.role === 'assistant' ? (
                    <div
                      className="prose-sm [&_pre]:my-2 [&_code]:text-accent-gold"
                      dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                    />
                  ) : (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  )}
                </div>
              </div>
            ))
          )}
          {streaming && streamingContentRef.current === '' && (
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
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="px-3 sm:px-4 py-2 sm:py-3 border-t border-border-default shrink-0">
          {!activeConvo ? (
            <button
              onClick={startNewConversation}
              className="w-full py-3 bg-accent-gold text-bg-primary font-semibold rounded-lg hover:bg-accent-gold-dim transition-colors text-sm"
            >
              Start a new conversation
            </button>
          ) : (
            <div className="flex gap-2 items-end">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a message... (Enter to send)"
                disabled={streaming}
                rows={1}
                className="flex-1 px-3 py-2.5 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-gold disabled:opacity-50 resize-none text-sm leading-relaxed"
                style={{ maxHeight: '160px' }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || streaming}
                className="px-3 py-2.5 bg-accent-gold text-bg-primary rounded-lg hover:bg-accent-gold-dim transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
              >
                <Send size={18} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function buildStructCodePrompt(structCode: string, resident: any): string {
  if (!resident?.struct_result) {
    return `My STRUCT CODE is ${structCode}. Please tell me about my personality type and characteristics.`
  }

  const sr = resident.struct_result
  const top3 = sr.top_candidates || []
  const top3Lines = top3.slice(0, 3).map((c: any, i: number) => {
    const score = c.score <= 1.0 ? (c.score * 100).toFixed(1) : c.score.toFixed(1)
    return `#${i + 1}: ${c.code} (${c.name}) Match: ${score}%`
  })

  const lines = [
    `[STRUCT CODE Diagnosis Result]`,
    `Code: ${sr.struct_code || structCode}`,
    sr.birth_date ? `Birth Date: ${sr.birth_date}` : '',
    '',
    ...(top3Lines.length > 0 ? [`[Type Candidates TOP3]`, ...top3Lines] : []),
    '',
    `Based on these results, please tell me about my personality traits and thinking patterns.`,
  ]
  return lines.filter(l => l !== undefined).join('\n')
}
