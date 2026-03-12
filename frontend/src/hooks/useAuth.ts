import { useState } from 'react';
import { login as apiLogin, logout as apiLogout, LoginPayload } from '../services/api';

interface ApiError {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

export function useAuth() {
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(
    () => !!localStorage.getItem('access_token')
  );
  const [error, setError] = useState<string | null>(null);

  const login = async (payload: LoginPayload) => {
    setError(null);
    try {
      await apiLogin(payload);
      setIsLoggedIn(true);
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setError(apiErr?.response?.data?.detail || apiErr?.message || 'Login failed');
    }
  };

  const logout = () => {
    apiLogout();
    setIsLoggedIn(false);
  };

  return { isLoggedIn, login, logout, error };
}
