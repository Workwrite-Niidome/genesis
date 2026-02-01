import { create } from 'zustand';
import { api } from '../services/api';

interface LLMProvider {
  id: string;
  name: string;
  default_model: string;
  key_prefix: string;
}

interface DeployStore {
  availableTraits: string[];
  providers: LLMProvider[];
  deployPanelOpen: boolean;
  loading: boolean;
  error: string | null;
  successMessage: string | null;
  agentToken: string | null;
  togglePanel: () => void;
  fetchTraits: () => Promise<void>;
  fetchProviders: () => Promise<void>;
  registerAgent: (
    name: string,
    traits: string[],
    philosophy: string,
    llmProvider: string,
    llmApiKey: string,
    llmModel: string,
  ) => Promise<boolean>;
  clearMessages: () => void;
}

export const useDeployStore = create<DeployStore>((set) => ({
  availableTraits: [],
  providers: [],
  deployPanelOpen: false,
  loading: false,
  error: null,
  successMessage: null,
  agentToken: null,

  togglePanel: () => set((s) => ({ deployPanelOpen: !s.deployPanelOpen })),

  fetchTraits: async () => {
    try {
      const data = await api.deploy.getTraits();
      set({ availableTraits: data.traits });
    } catch {
      // silent
    }
  },

  fetchProviders: async () => {
    try {
      const data = await api.deploy.getProviders();
      set({ providers: data.providers });
    } catch {
      // silent
    }
  },

  registerAgent: async (
    name: string,
    traits: string[],
    philosophy: string,
    llmProvider: string,
    llmApiKey: string,
    llmModel: string,
  ) => {
    set({ loading: true, error: null, successMessage: null, agentToken: null });
    try {
      const data = await api.deploy.registerAgent({
        name,
        traits,
        philosophy,
        llm_provider: llmProvider,
        llm_api_key: llmApiKey,
        llm_model: llmModel,
      });
      set({
        loading: false,
        successMessage: data.message,
        agentToken: data.agent_token,
      });
      return true;
    } catch (e: any) {
      let msg = 'Registration failed';
      try {
        if (e?.message?.includes('401')) msg = 'API key validation failed. Check your key.';
        else if (e?.message?.includes('422')) msg = 'Invalid input. Check name, traits, and provider.';
        else if (e?.message) msg = e.message;
      } catch {}
      set({ loading: false, error: msg });
      return false;
    }
  },

  clearMessages: () => set({ error: null, successMessage: null, agentToken: null }),
}));
