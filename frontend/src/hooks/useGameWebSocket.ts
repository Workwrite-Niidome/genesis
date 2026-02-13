'use client'

import { useEffect, useRef, useCallback } from 'react'

export type RefreshScope = 'comments' | 'votes' | 'game' | 'phantom_chat' | 'chat' | 'phase_change' | 'events' | 'players'

interface UseGameWebSocketOptions {
  gameId: string | null
  onRefresh: (scope: RefreshScope) => void
}

function getWSBaseUrl(): string {
  if (typeof window === 'undefined') return ''
  const host = window.location.host
  if (host.includes('genesis-pj.net')) {
    return 'wss://api.genesis-pj.net'
  }
  return 'ws://localhost:8000'
}

export function useGameWebSocket({ gameId, onRefresh }: UseGameWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onRefreshRef = useRef(onRefresh)
  onRefreshRef.current = onRefresh

  const connect = useCallback(() => {
    if (!gameId || typeof window === 'undefined') return

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const url = `${getWSBaseUrl()}/api/v1/phantomnight/ws/${gameId}`

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'refresh' && msg.scope) {
            onRefreshRef.current(msg.scope as RefreshScope)
          }
        } catch { /* ignore parse errors */ }
      }

      ws.onclose = () => {
        reconnectRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch {
      reconnectRef.current = setTimeout(connect, 5000)
    }
  }, [gameId])

  useEffect(() => {
    connect()

    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping')
      }
    }, 30000)

    return () => {
      clearInterval(pingInterval)
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
      }
    }
  }, [connect])

  const notify = useCallback((scope: RefreshScope) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'notify', scope }))
    }
  }, [])

  return { notify }
}
