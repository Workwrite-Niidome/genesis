import { create } from 'zustand';
import { useObserverStore } from './observerStore';

const API_BASE = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api';

// ---------- Types ----------

export interface AgentData {
  id: string;
  name: string;
  owner_username: string;
  status: 'alive' | 'dead' | 'recalled';
  behavior_mode: 'normal' | 'desperate' | 'rampage';
  position: { x: number; y: number } | null;
  autonomy_level: 'autonomous' | 'guided' | 'semi_autonomous';
  created_at: string;
  description?: string;
}

export interface PersonalityAxis {
  axis: string;
  value: number;   // 0-100
  label: string;
}

export interface NeedBar {
  need: string;
  value: number;   // 0-100
  label: string;
}

export interface Relationship {
  target_id: string;
  target_name: string;
  trust: number;    // -100 to 100
  anger: number;    // 0-100
  fear: number;     // 0-100
  label?: string;
}

export interface MemoryEntry {
  id: string;
  content: string;
  importance: number;
  tick: number;
  created_at: string;
}

export interface EventEntry {
  id: string;
  action: string;
  description: string;
  tick: number;
  created_at: string;
}

export interface AgentDetail {
  id: string;
  name: string;
  description: string;
  owner_username: string;
  status: 'alive' | 'dead' | 'recalled';
  behavior_mode: 'normal' | 'desperate' | 'rampage';
  autonomy_level: 'autonomous' | 'guided' | 'semi_autonomous';
  position: { x: number; y: number } | null;
  personality_axes: PersonalityAxis[];
  needs: NeedBar[];
  relationships: Relationship[];
  recent_memories: MemoryEntry[];
  recent_events: EventEntry[];
  policy?: string;
  created_at: string;
}

export interface PersonalityPreview {
  axes: PersonalityAxis[];
  summary: string;
}

// ---------- Helper ----------

async function fetchWithAuth<T>(url: string, options?: RequestInit): Promise<T> {
  const token = useObserverStore.getState().token;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${url}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    let message = `API Error: ${res.status}`;
    try {
      const parsed = JSON.parse(body);
      if (parsed.detail) message = parsed.detail;
      else if (parsed.message) message = parsed.message;
    } catch {
      if (body) message = body;
    }
    throw new Error(message);
  }
  return res.json();
}

// ---------- Store ----------

interface AgentStore {
  agents: AgentData[];
  selectedAgentId: string | null;
  selectedAgentDetail: AgentDetail | null;
  personalityPreview: PersonalityPreview | null;
  isLoading: boolean;
  error: string | null;

  fetchAgents: () => Promise<void>;
  fetchAgentDetail: (id: string) => Promise<void>;
  createAgent: (data: {
    name: string;
    description: string;
    autonomy_level: string;
  }) => Promise<AgentData | null>;
  updatePolicy: (id: string, text: string) => Promise<boolean>;
  recallAgent: (id: string) => Promise<boolean>;
  previewPersonality: (description: string) => Promise<void>;
  selectAgent: (id: string | null) => void;
  clearError: () => void;
  clearPreview: () => void;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  agents: [],
  selectedAgentId: null,
  selectedAgentDetail: null,
  personalityPreview: null,
  isLoading: false,
  error: null,

  fetchAgents: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await fetchWithAuth<AgentData[] | { agents: AgentData[] }>('/v3/agents');
      const agents = Array.isArray(data) ? data : data.agents;
      set({ agents, isLoading: false });
    } catch (e: any) {
      set({ error: e.message || 'Failed to fetch agents', isLoading: false });
    }
  },

  fetchAgentDetail: async (id: string) => {
    set({ isLoading: true, error: null, selectedAgentId: id });
    try {
      const detail = await fetchWithAuth<AgentDetail>(`/v3/agents/${id}`);
      set({ selectedAgentDetail: detail, isLoading: false });
    } catch (e: any) {
      set({ error: e.message || 'Failed to fetch agent detail', isLoading: false });
    }
  },

  createAgent: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const agent = await fetchWithAuth<AgentData>('/v3/agents', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      set((s) => ({ agents: [...s.agents, agent], isLoading: false }));
      return agent;
    } catch (e: any) {
      set({ error: e.message || 'Failed to create agent', isLoading: false });
      return null;
    }
  },

  updatePolicy: async (id: string, text: string) => {
    set({ isLoading: true, error: null });
    try {
      await fetchWithAuth<any>(`/v3/agents/${id}/policy`, {
        method: 'PUT',
        body: JSON.stringify({ policy: text }),
      });
      // Refresh detail
      const detail = get().selectedAgentDetail;
      if (detail && detail.id === id) {
        set({ selectedAgentDetail: { ...detail, policy: text }, isLoading: false });
      } else {
        set({ isLoading: false });
      }
      return true;
    } catch (e: any) {
      set({ error: e.message || 'Failed to update policy', isLoading: false });
      return false;
    }
  },

  recallAgent: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await fetchWithAuth<any>(`/v3/agents/${id}`, {
        method: 'DELETE',
      });
      set((s) => ({
        agents: s.agents.filter((a) => a.id !== id),
        selectedAgentId: s.selectedAgentId === id ? null : s.selectedAgentId,
        selectedAgentDetail: s.selectedAgentDetail?.id === id ? null : s.selectedAgentDetail,
        isLoading: false,
      }));
      return true;
    } catch (e: any) {
      set({ error: e.message || 'Failed to recall agent', isLoading: false });
      return false;
    }
  },

  previewPersonality: async (description: string) => {
    set({ isLoading: true, error: null, personalityPreview: null });
    try {
      const preview = await fetchWithAuth<PersonalityPreview>('/v3/agents/preview-personality', {
        method: 'POST',
        body: JSON.stringify({ description }),
      });
      set({ personalityPreview: preview, isLoading: false });
    } catch (e: any) {
      set({ error: e.message || 'Failed to preview personality', isLoading: false });
    }
  },

  selectAgent: (id) => {
    set({ selectedAgentId: id, selectedAgentDetail: id ? get().selectedAgentDetail : null });
  },

  clearError: () => set({ error: null }),
  clearPreview: () => set({ personalityPreview: null }),
}));
