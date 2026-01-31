const API_BASE = '/api';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API Error: ${res.status}`);
  return res.json();
}

export const api = {
  world: {
    getState: () => fetchJSON<any>('/world/state'),
    getStats: () => fetchJSON<any>('/world/stats'),
    genesis: () =>
      fetchJSON<any>('/world/genesis', {
        method: 'POST',
        body: JSON.stringify({ confirm: true }),
      }),
  },
  god: {
    getState: () => fetchJSON<any>('/god/state'),
    sendMessage: (message: string) =>
      fetchJSON<any>('/god/message', {
        method: 'POST',
        body: JSON.stringify({ message }),
      }),
    getHistory: () => fetchJSON<{ history: any[] }>('/god/history'),
  },
  ais: {
    list: (aliveOnly = true) => fetchJSON<any[]>(`/ais?alive_only=${aliveOnly}`),
    get: (id: string) => fetchJSON<any>(`/ais/${id}`),
    getMemories: (id: string) => fetchJSON<any[]>(`/ais/${id}/memories`),
  },
  concepts: {
    list: () => fetchJSON<any[]>('/concepts'),
    get: (id: string) => fetchJSON<any>(`/concepts/${id}`),
  },
  history: {
    getEvents: (limit = 50) => fetchJSON<any[]>(`/history/events?limit=${limit}`),
    getTimeline: (limit = 100) => fetchJSON<any[]>(`/history/timeline?limit=${limit}`),
  },
};
