import { create } from 'zustand';

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
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  activeChannel: 'global',

  addMessage: (msg) =>
    set((s) => ({ messages: [...s.messages.slice(-200), msg] })),

  setChannel: (channel) => set({ activeChannel: channel }),
}));
