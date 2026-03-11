import { useState } from 'react';
import { login as apiLogin, logout as apiLogout, LoginPayload } from '../services/api';

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
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Login failed');
    }
  };

  const logout = () => {
    apiLogout();
    setIsLoggedIn(false);
  };

  return { isLoggedIn, login, logout, error };
}
