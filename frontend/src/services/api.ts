import { getAdminAuthHeader } from '../stores/authStore';
import type { AIRanking } from '../types/world';

const API_BASE = '/api';

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
  history: {
    getEvents: (limit = 50) => fetchJSON<any[]>(`/history/events?limit=${limit}`),
    getTimeline: (limit = 100) => fetchJSON<any[]>(`/history/timeline?limit=${limit}`),
    getGodFeed: (limit = 20) => fetchJSON<{ feed: any[] }>(`/history/god-feed?limit=${limit}`),
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
