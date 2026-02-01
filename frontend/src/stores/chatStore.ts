import { create } from 'zustand';
import { api } from '../services/api';

interface ChatMessage {
  id: string;
  username: string;
  content: string;
  channel: string;
  timestamp: string;
}

interface ChatStore {
  messages: ChatMessage[];
  activeChannel: string;
  addMessage: (msg: ChatMessage) => void;
  setChannel: (channel: string) => void;
  fetchMessages: (channel?: string) => Promise<void>;
  postMessage: (token: string, content: string) => Promise<void>;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  activeChannel: 'global',

  addMessage: (msg) =>
    set((s) => {
      // Deduplicate by id
      if (s.messages.some((m) => m.id === msg.id)) return s;
      return { messages: [...s.messages.slice(-200), msg] };
    }),

  setChannel: (channel) => set({ activeChannel: channel }),

  fetchMessages: async (channel?: string) => {
    const ch = channel || get().activeChannel;
    try {
      const data = await api.observers.getChat(ch, 50);
      set({ messages: data });
    } catch {
      // Silently fail — messages stay as-is
    }
  },

  postMessage: async (token: string, content: string) => {
    const channel = get().activeChannel;
    try {
      await api.observers.postChat(token, channel, content);
      // The message will arrive via Socket.IO broadcast — no need to add locally
    } catch {
      // Silently fail
    }
  },
}));
