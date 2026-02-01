import { create } from 'zustand';
import { api } from '../services/api';

export interface BoardThread {
  id: string;
  title: string;
  body: string | null;
  author_type: string;
  author_id: string | null;
  author_name: string | null;
  event_id: string | null;
  category: string | null;
  reply_count: number;
  last_reply_at: string | null;
  is_pinned: boolean;
  created_at: string;
}

export interface BoardReply {
  id: string;
  thread_id: string;
  author_type: string;
  author_id: string | null;
  author_name: string | null;
  content: string;
  created_at: string;
}

export interface BoardThreadDetail extends BoardThread {
  replies: BoardReply[];
}

type BoardView = 'list' | 'detail' | 'create';

interface BoardStore {
  threads: BoardThread[];
  currentThread: BoardThreadDetail | null;
  view: BoardView;
  categoryFilter: string | null;
  loading: boolean;

  setView: (view: BoardView) => void;
  setCategoryFilter: (category: string | null) => void;

  fetchThreads: (page?: number, limit?: number) => Promise<void>;
  fetchThread: (id: string) => Promise<void>;
  createThread: (token: string, title: string, body?: string, category?: string) => Promise<boolean>;
  createReply: (token: string, threadId: string, content: string) => Promise<boolean>;

  addThread: (thread: BoardThread) => void;
  addReply: (reply: BoardReply & { thread_title?: string }) => void;
}

export const useBoardStore = create<BoardStore>((set, get) => ({
  threads: [],
  currentThread: null,
  view: 'list',
  categoryFilter: null,
  loading: false,

  setView: (view) => set({ view }),
  setCategoryFilter: (category) => set({ categoryFilter: category }),

  fetchThreads: async (page = 1, limit = 30) => {
    set({ loading: true });
    try {
      const { categoryFilter } = get();
      const threads = await api.board.getThreads(page, limit, categoryFilter || undefined);
      set({ threads, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchThread: async (id: string) => {
    set({ loading: true });
    try {
      const thread = await api.board.getThread(id);
      set({ currentThread: thread, view: 'detail', loading: false });
    } catch {
      set({ loading: false });
    }
  },

  createThread: async (token, title, body, category) => {
    set({ loading: true });
    try {
      await api.board.createThread(token, title, body, category);
      set({ loading: false, view: 'list' });
      // Refresh list
      get().fetchThreads();
      return true;
    } catch {
      set({ loading: false });
      return false;
    }
  },

  createReply: async (token, threadId, content) => {
    set({ loading: true });
    try {
      await api.board.createReply(token, threadId, content);
      set({ loading: false });
      // Refresh current thread
      get().fetchThread(threadId);
      return true;
    } catch {
      set({ loading: false });
      return false;
    }
  },

  addThread: (thread) => {
    set((s) => {
      // Deduplicate
      if (s.threads.some((t) => t.id === thread.id)) return s;
      return { threads: [thread, ...s.threads] };
    });
  },

  addReply: (reply) => {
    set((s) => {
      // Update thread reply_count in the list
      const threads = s.threads.map((t) =>
        t.id === reply.thread_id
          ? { ...t, reply_count: t.reply_count + 1, last_reply_at: reply.created_at }
          : t
      );

      // If currently viewing that thread, append the reply
      let currentThread = s.currentThread;
      if (currentThread && currentThread.id === reply.thread_id) {
        if (!currentThread.replies.some((r) => r.id === reply.id)) {
          currentThread = {
            ...currentThread,
            reply_count: currentThread.reply_count + 1,
            last_reply_at: reply.created_at,
            replies: [...currentThread.replies, reply],
          };
        }
      }

      return { threads, currentThread };
    });
  },
}));
