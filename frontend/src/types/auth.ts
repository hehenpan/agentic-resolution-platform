/** Auth Data Schemas aligned with api_server/app/schemas/auth.py and common.py */

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  code: number;
  message: string;
  data?: {
    tenant_id?: number;
    email?: string;
    [key: string]: unknown;
  };
}

export interface User {
  email: string;
  tenant_id: number;
}

export interface AuthState {
  isAuthenticated: boolean;
  userEmail: string | null;
  tenantId: number | null;
  isLoading: boolean;
  error: string | null;
  checkAuth: () => boolean;
  login: (credentials: LoginRequest) => Promise<boolean>;
  logout: () => Promise<void>;
  clearError: () => void;
}
