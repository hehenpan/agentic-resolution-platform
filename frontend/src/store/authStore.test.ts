import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuthStore } from './authStore';
import { setCookie, removeCookie, getCookie } from '../utils/cookie';
import { authService } from '../services/authService';

describe('authStore', () => {
  beforeEach(() => {
    removeCookie('sessionid');
    useAuthStore.setState({
      isAuthenticated: false,
      userEmail: null,
      tenantId: null,
      isLoading: false,
      error: null,
    });
    vi.restoreAllMocks();
  });

  it('checkAuth returns false when cookie is missing', () => {
    const isAuth = useAuthStore.getState().checkAuth();
    expect(isAuth).toBe(false);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().tenantId).toBeNull();
  });

  it('checkAuth returns true when sessionid cookie exists and sets tenantId to 1', () => {
    setCookie('sessionid', 'test_session');
    const isAuth = useAuthStore.getState().checkAuth();
    expect(isAuth).toBe(true);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().tenantId).toBe(1);
  });

  it('login succeeds and sets session cookie, email and tenantId to 1', async () => {
    vi.spyOn(authService, 'login').mockResolvedValueOnce({
      code: 0,
      message: 'User logged in successfully',
      data: { tenant_id: 1 },
    });

    const success = await useAuthStore.getState().login({
      email: 'user@example.com',
      password: 'any_password',
    });

    expect(success).toBe(true);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().userEmail).toBe('user@example.com');
    expect(useAuthStore.getState().tenantId).toBe(1);
    expect(getCookie('sessionid')).not.toBeNull();
  });

  it('logout clears session cookie and resets state', async () => {
    setCookie('sessionid', 'test_session');
    useAuthStore.setState({ isAuthenticated: true, userEmail: 'user@example.com', tenantId: 1 });

    await useAuthStore.getState().logout();

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().userEmail).toBeNull();
    expect(useAuthStore.getState().tenantId).toBeNull();
    expect(getCookie('sessionid')).toBeNull();
  });
});
