import { request } from './httpClient';
import { LoginRequest, LoginResponse } from '../types/auth';
import { setCookie, removeCookie } from '../utils/cookie';

export const authService = {
  /**
   * Post login credentials to backend FastAPI service.
   * Endpoint: /api/v1/auth/login
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const res = await request<LoginResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    if (res.code === 0) {
      // Set client session cookie if not set via Set-Cookie header (e.g., client mock environment)
      setCookie('sessionid', `session_${Date.now()}`);
    }

    return res;
  },

  /**
   * Log out current user and remove session cookie.
   */
  async logout(): Promise<void> {
    removeCookie('sessionid');
  },
};
