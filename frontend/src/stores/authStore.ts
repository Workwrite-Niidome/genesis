import { create } from 'zustand';

interface AuthStore {
  isAuthenticated: boolean;
  error: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
}

function getStoredCredentials(): string | null {
  return sessionStorage.getItem('genesis_admin_auth');
}

function storeCredentials(username: string, password: string): void {
  const encoded = btoa(`${username}:${password}`);
  sessionStorage.setItem('genesis_admin_auth', encoded);
}

function clearCredentials(): void {
  sessionStorage.removeItem('genesis_admin_auth');
}

export function getAdminAuthHeader(): string | null {
  const cred = getStoredCredentials();
  return cred ? `Basic ${cred}` : null;
}

export const useAuthStore = create<AuthStore>((set) => ({
  isAuthenticated: !!getStoredCredentials(),
  error: null,
  loading: false,

  login: async (username: string, password: string) => {
    set({ loading: true, error: null });
    const encoded = btoa(`${username}:${password}`);
    try {
      const res = await fetch('/api/god/state', {
        headers: { Authorization: `Basic ${encoded}` },
      });
      if (res.ok) {
        storeCredentials(username, password);
        set({ isAuthenticated: true, loading: false });
        return true;
      }
      set({ error: 'Invalid credentials', loading: false });
      return false;
    } catch {
      set({ error: 'Connection error', loading: false });
      return false;
    }
  },

  logout: () => {
    clearCredentials();
    set({ isAuthenticated: false, error: null });
  },
}));
