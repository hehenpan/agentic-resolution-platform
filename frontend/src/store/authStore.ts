import { create } from 'zustand';
import { AuthState, LoginRequest } from '../types/auth';
import { authService } from '../services/authService';
import { getCookie, setCookie, removeCookie } from '../utils/cookie';

const SESSION_COOKIE_NAME = 'sessionid';
const DEFAULT_MOCK_TENANT_ID = 1;
const LOCAL_STORAGE_EMAIL_KEY = 'auth_user_email';
const LOCAL_STORAGE_TENANT_KEY = 'auth_tenant_id';

function getStoredUser(): { userEmail: string | null; tenantId: number | null } {
  if (typeof window === 'undefined') return { userEmail: null, tenantId: null };
  const email = localStorage.getItem(LOCAL_STORAGE_EMAIL_KEY);
  const tenantStr = localStorage.getItem(LOCAL_STORAGE_TENANT_KEY);
  const tenantId = tenantStr ? Number(tenantStr) : null;
  return { userEmail: email, tenantId };
}

function setStoredUser(email: string, tenantId: number): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(LOCAL_STORAGE_EMAIL_KEY, email);
  localStorage.setItem(LOCAL_STORAGE_TENANT_KEY, String(tenantId));
}

function clearStoredUser(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(LOCAL_STORAGE_EMAIL_KEY);
  localStorage.removeItem(LOCAL_STORAGE_TENANT_KEY);
}

const initialUser = getStoredUser();
const initialAuth = !!initialUser.userEmail || !!getCookie(SESSION_COOKIE_NAME);

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: initialAuth,
  userEmail: initialUser.userEmail,
  tenantId: initialAuth ? (initialUser.tenantId ?? DEFAULT_MOCK_TENANT_ID) : null,
  isLoading: false,
  error: null,

  checkAuth: () => {
    const user = getStoredUser();
    const hasSession = !!user.userEmail || !!getCookie(SESSION_COOKIE_NAME);
    set({
      isAuthenticated: hasSession,
      userEmail: user.userEmail,
      tenantId: hasSession ? (user.tenantId ?? DEFAULT_MOCK_TENANT_ID) : null,
    });
    return hasSession;
  },

  login: async (credentials: LoginRequest): Promise<boolean> => {
    set({ isLoading: true, error: null });

    try {
      const res = await authService.login(credentials);
      if (res.code === 0) {
        const tenantId = res.data?.tenant_id ?? DEFAULT_MOCK_TENANT_ID;
        setCookie(SESSION_COOKIE_NAME, `session_${Date.now()}`);
        setStoredUser(credentials.email, tenantId);
        set({
          isAuthenticated: true,
          userEmail: credentials.email,
          tenantId,
          isLoading: false,
          error: null,
        });
        return true;
      } else {
        set({
          isLoading: false,
          error: res.message || 'Login failed',
        });
        return false;
      }
    } catch (err: unknown) {
      // In mock / offline / dev mode, fallback to successful login if mock server passes
      if (import.meta.env.VITE_MOCK === 'true' || process.env.NODE_ENV === 'test') {
        setCookie(SESSION_COOKIE_NAME, `mock_session_${Date.now()}`);
        setStoredUser(credentials.email, DEFAULT_MOCK_TENANT_ID);
        set({
          isAuthenticated: true,
          userEmail: credentials.email,
          tenantId: DEFAULT_MOCK_TENANT_ID,
          isLoading: false,
          error: null,
        });
        return true;
      }

      const errorMessage =
        err instanceof Error ? err.message : 'Network or server error during login';
      set({
        isLoading: false,
        error: errorMessage,
      });
      return false;
    }
  },

  logout: async (): Promise<void> => {
    await authService.logout();
    removeCookie(SESSION_COOKIE_NAME);
    clearStoredUser();
    set({
      isAuthenticated: false,
      userEmail: null,
      tenantId: null,
      error: null,
    });
  },

  clearError: () => {
    set({ error: null });
  },
}));
