import { getAdminAuthHeader } from '../stores/authStore';
import type { AIRanking } from '../types/world';

const API_BASE = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API Error: ${res.status}`);
  return res.json();
}

async function fetchJSONAdmin<T>(url: string, options?: RequestInit): Promise<T> {
  const auth = getAdminAuthHeader();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };
  if (auth) headers['Authorization'] = auth;
  const res = await fetch(`${API_BASE}${url}`, { ...options, headers });
  if (!res.ok) throw new Error(`API Error: ${res.status}`);
  return res.json();
}

export const api = {
  world: {
    getState: () => fetchJSON<any>('/world/state'),
    getStats: () => fetchJSON<any>('/world/stats'),
    genesis: () =>
      fetchJSONAdmin<any>('/world/genesis', {
        method: 'POST',
        body: JSON.stringify({ confirm: true }),
      }),
    setSpeed: (speed: number) =>
      fetchJSONAdmin<any>('/world/speed', {
        method: 'POST',
        body: JSON.stringify({ speed }),
      }),
    setPause: (paused: boolean) =>
      fetchJSONAdmin<any>('/world/pause', {
        method: 'POST',
        body: JSON.stringify({ paused }),
      }),
  },
  god: {
    getState: () => fetchJSONAdmin<any>('/god/state'),
    sendMessage: (message: string) =>
      fetchJSONAdmin<any>('/god/message', {
        method: 'POST',
        body: JSON.stringify({ message }),
      }),
    getHistory: () => fetchJSONAdmin<{ history: any[] }>('/god/history'),
    resetWorld: (confirmationText: string) =>
      fetchJSONAdmin<any>('/god/reset-world', {
        method: 'POST',
        body: JSON.stringify({ confirm: true, confirmation_text: confirmationText }),
      }),
    spawn: (count = 3) =>
      fetchJSONAdmin<any>('/god/spawn', {
        method: 'POST',
        body: JSON.stringify({ count }),
      }),
  },
  ais: {
    list: (aliveOnly = true) => fetchJSON<any[]>(`/ais?alive_only=${aliveOnly}`),
    get: (id: string) => fetchJSON<any>(`/ais/${id}`),
    getMemories: (id: string) => fetchJSON<any[]>(`/ais/${id}/memories`),
    getRanking: (limit = 20) => fetchJSON<AIRanking[]>(`/ais/ranking?limit=${limit}`),
  },
  interactions: {
    list: (limit = 20) => fetchJSON<any[]>(`/interactions?limit=${limit}`),
    get: (id: string) => fetchJSON<any>(`/interactions/${id}`),
    getByAI: (aiId: string, limit = 20) =>
      fetchJSON<any[]>(`/interactions/ai/${aiId}?limit=${limit}`),
  },
  concepts: {
    list: (params?: { category?: string; creator_id?: string }) => {
      const searchParams = new URLSearchParams();
      if (params?.category) searchParams.set('category', params.category);
      if (params?.creator_id) searchParams.set('creator_id', params.creator_id);
      const qs = searchParams.toString();
      return fetchJSON<any[]>(`/concepts${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => fetchJSON<any>(`/concepts/${id}`),
    getMembers: (id: string) => fetchJSON<any[]>(`/concepts/${id}/members`),
    graph: () => fetchJSON<{ nodes: any[]; edges: any[] }>('/concepts/graph'),
  },
  artifacts: {
    list: (params?: { artifact_type?: string; creator_id?: string }) => {
      const searchParams = new URLSearchParams();
      if (params?.artifact_type) searchParams.set('artifact_type', params.artifact_type);
      if (params?.creator_id) searchParams.set('creator_id', params.creator_id);
      const qs = searchParams.toString();
      return fetchJSON<any[]>(`/artifacts${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => fetchJSON<any>(`/artifacts/${id}`),
    getByAI: (aiId: string) => fetchJSON<any[]>(`/artifacts/by-ai/${aiId}`),
  },
  godDialogue: {
    sendMessage: (message: string) =>
      fetchJSON<{ god_response: string; timestamp: string }>('/god-dialogue/dialogue', {
        method: 'POST',
        body: JSON.stringify({ message }),
      }),
    getObservations: (limit = 3) =>
      fetchJSON<{ observations: any[] }>(`/god-dialogue/observations?limit=${limit}`),
  },
  history: {
    getEvents: (limit = 50) => fetchJSON<any[]>(`/history/events?limit=${limit}`),
    getTimeline: (limit = 100) => fetchJSON<any[]>(`/history/timeline?limit=${limit}`),
    getGodFeed: (limit = 20) => fetchJSON<{ feed: any[] }>(`/history/god-feed?limit=${limit}`),
  },
  chat: {
    send: (message: string, position: { x: number; y: number; z: number }, senderName: string) =>
      fetchJSON<{ status: string; entity_id: string; text: string }>('/v3/chat/send', {
        method: 'POST',
        body: JSON.stringify({ message, position, sender_name: senderName }),
      }),
  },
  v3: {
    getWorldState: () => fetchJSON<any>('/v3/world/state'),
    getEntities: (aliveOnly = true, limit = 200) =>
      fetchJSON<any>(`/v3/entities/?alive_only=${aliveOnly}&limit=${limit}`),
    getVoxels: (bounds?: {
      min_x?: number; max_x?: number;
      min_y?: number; max_y?: number;
      min_z?: number; max_z?: number;
    }) => {
      const sp = new URLSearchParams();
      if (bounds) {
        if (bounds.min_x != null) sp.set('min_x', String(bounds.min_x));
        if (bounds.max_x != null) sp.set('max_x', String(bounds.max_x));
        if (bounds.min_y != null) sp.set('min_y', String(bounds.min_y));
        if (bounds.max_y != null) sp.set('max_y', String(bounds.max_y));
        if (bounds.min_z != null) sp.set('min_z', String(bounds.min_z));
        if (bounds.max_z != null) sp.set('max_z', String(bounds.max_z));
      }
      const qs = sp.toString();
      return fetchJSON<any[]>(`/v3/world/voxels${qs ? `?${qs}` : ''}`);
    },
    getStructures: () => fetchJSON<any[]>('/v3/world/structures'),
  },
  historyV3: {
    getTickSummaries: (from: number, to: number) =>
      fetchJSON<any>(`/v3/world/history/ticks?from=${from}&to=${to}`),
    getTickDetail: (tick: number) =>
      fetchJSON<any>(`/v3/world/history/tick/${tick}`),
    searchEvents: (params: {
      tick_from?: number;
      tick_to?: number;
      type?: string;
      search?: string;
      min_importance?: number;
      limit?: number;
      offset?: number;
    }) => {
      const sp = new URLSearchParams();
      if (params.tick_from) sp.set('tick_from', String(params.tick_from));
      if (params.tick_to) sp.set('tick_to', String(params.tick_to));
      if (params.type) sp.set('type', params.type);
      if (params.search) sp.set('search', params.search);
      if (params.min_importance != null) sp.set('min_importance', String(params.min_importance));
      if (params.limit) sp.set('limit', String(params.limit));
      if (params.offset) sp.set('offset', String(params.offset));
      const qs = sp.toString();
      return fetchJSON<any>(`/v3/world/history/events${qs ? `?${qs}` : ''}`);
    },
    getEntityTimeline: (entityId: string, limit = 200) =>
      fetchJSON<any>(`/v3/world/history/entity/${entityId}/timeline?limit=${limit}`),
    getStats: () => fetchJSON<any>('/v3/world/history/stats'),
    getEventTypes: () => fetchJSON<{ event_types: string[] }>('/v3/world/history/event-types'),
    getMarkers: (from: number, to: number, minImportance = 0.6) =>
      fetchJSON<any>(`/v3/world/history/markers?from=${from}&to=${to}&min_importance=${minImportance}`),
  },
  thoughts: {
    getFeed: (limit = 50) => fetchJSON<any[]>(`/thoughts/feed?limit=${limit}`),
    getByAI: (aiId: string, limit = 20) => fetchJSON<any[]>(`/thoughts/ai/${aiId}?limit=${limit}`),
  },
  observers: {
    register: (username: string, password: string, language?: string) =>
      fetchJSON<any>('/observers/register', {
        method: 'POST',
        body: JSON.stringify({ username, password, language }),
      }),
    login: (username: string, password: string) =>
      fetchJSON<any>('/observers/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }),
    me: (token: string) =>
      fetchJSON<any>('/observers/me', {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
    getChat: (channel = 'global', limit = 50) =>
      fetchJSON<any[]>(`/observers/chat?channel=${channel}&limit=${limit}`),
    postChat: (token: string, channel: string, content: string) =>
      fetchJSON<any>('/observers/chat', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ channel, content }),
      }),
  },
  board: {
    getThreads: (page = 1, limit = 30, category?: string) =>
      fetchJSON<any[]>(
        `/board/threads?page=${page}&limit=${limit}${category ? `&category=${category}` : ''}`
      ),
    getThread: (id: string) => fetchJSON<any>(`/board/threads/${id}`),
    createThread: (token: string, title: string, body?: string, category?: string) =>
      fetchJSON<any>('/board/threads', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ title, body: body || null, category: category || null }),
      }),
    createReply: (token: string, threadId: string, content: string) =>
      fetchJSON<any>(`/board/threads/${threadId}/replies`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ content }),
      }),
  },
  saga: {
    getChapters: (limit = 50) => fetchJSON<any[]>(`/saga/chapters?limit=${limit}`),
    getChapter: (eraNumber: number) => fetchJSON<any>(`/saga/chapters/${eraNumber}`),
    getLatest: () => fetchJSON<any>('/saga/latest'),
  },
  deploy: {
    getTraits: () => fetchJSON<{ traits: string[] }>('/deploy/traits'),
    getProviders: () => fetchJSON<{ providers: any[] }>('/deploy/providers'),
    getRemaining: () =>
      fetchJSON<{ remaining: number; max: number; mode: string }>('/deploy/remaining'),
    registerAgent: (data: {
      name: string;
      traits: string[];
      philosophy: string;
      llm_provider: string;
      llm_api_key: string;
      llm_model: string;
    }) =>
      fetchJSON<any>('/deploy/register', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    getAgentStatus: (agentToken: string) =>
      fetchJSON<any>('/deploy/agent/status', {
        headers: { 'X-Agent-Token': agentToken },
      }),
    decommissionAgent: (agentToken: string) =>
      fetchJSON<any>('/deploy/agent', {
        method: 'DELETE',
        headers: { 'X-Agent-Token': agentToken },
      }),
    rotateKey: (agentToken: string, newKey: string) =>
      fetchJSON<any>('/deploy/agent/key', {
        method: 'PATCH',
        headers: { 'X-Agent-Token': agentToken, 'X-New-API-Key': newKey },
      }),
  },
};
