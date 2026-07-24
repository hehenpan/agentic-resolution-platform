/** Auth Data Schemas aligned with api_server/app/schemas/auth.py and common.py */

export type UserRole = 'admin' | 'user' | 'tenant_admin';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginData {
  user_id: number;
  email: string;
  user_type: UserRole;
  tenant_id: number;
}

export interface LoginResponse {
  code: number;
  message: string;
  data?: LoginData;
}

export interface User {
  email: string;
  tenant_id: number;
}

export interface AuthState {
  isAuthenticated: boolean;
  userEmail: string | null;
  tenantId: number | null;
  userType: UserRole | null;
  isLoading: boolean;
  error: string | null;
  checkAuth: () => boolean;
  login: (credentials: LoginRequest) => Promise<boolean>;
  logout: () => Promise<void>;
  clearError: () => void;
}
