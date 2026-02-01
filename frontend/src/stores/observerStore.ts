import { create } from 'zustand';
import { api } from '../services/api';

interface ObserverStore {
  token: string | null;
  username: string | null;
  isLoggedIn: boolean;
  error: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  register: (username: string, password: string, language?: string) => Promise<boolean>;
  logout: () => void;
}

function getStoredToken(): string | null {
  return localStorage.getItem('genesis_observer_token');
}

function getStoredUsername(): string | null {
  return localStorage.getItem('genesis_observer_username');
}

function storeObserver(token: string, username: string): void {
  localStorage.setItem('genesis_observer_token', token);
  localStorage.setItem('genesis_observer_username', username);
}

function clearObserver(): void {
  localStorage.removeItem('genesis_observer_token');
  localStorage.removeItem('genesis_observer_username');
}

export const useObserverStore = create<ObserverStore>((set) => ({
  token: getStoredToken(),
  username: getStoredUsername(),
  isLoggedIn: !!getStoredToken(),
  error: null,
  loading: false,

  login: async (username: string, password: string) => {
    set({ loading: true, error: null });
    try {
      const data = await api.observers.login(username, password);
      storeObserver(data.token, data.username);
      set({ token: data.token, username: data.username, isLoggedIn: true, loading: false });
      return true;
    } catch (e: any) {
      set({ error: e.message || 'Login failed', loading: false });
      return false;
    }
  },

  register: async (username: string, password: string, language?: string) => {
    set({ loading: true, error: null });
    try {
      const data = await api.observers.register(username, password, language);
      storeObserver(data.token, data.username);
      set({ token: data.token, username: data.username, isLoggedIn: true, loading: false });
      return true;
    } catch (e: any) {
      set({ error: e.message || 'Registration failed', loading: false });
      return false;
    }
  },

  logout: () => {
    clearObserver();
    set({ token: null, username: null, isLoggedIn: false, error: null });
  },
}));
