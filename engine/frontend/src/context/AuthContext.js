/**
 * Authentication context for Agent Rook.
 * Single user type — simplified from Daisy's multi-role system.
 */
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { getMe, getToken, setToken, clearToken } from '../services/chatApi';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const cached = localStorage.getItem('rook_user');
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });
  const [token, setTokenState] = useState(() => getToken());

  const isLoggedIn = !!token;
  const credits = user?.credits ?? 0;
  const isAdmin = user?.role === 'admin';

  // Refresh user profile on mount if token exists
  useEffect(() => {
    if (token) {
      getMe()
        .then((res) => {
          const userData = res.user || res;
          setUser(userData);
          localStorage.setItem('rook_user', JSON.stringify(userData));
        })
        .catch(() => {
          // Token expired — clear auth state
          clearToken();
          localStorage.removeItem('rook_user');
          setTokenState(null);
          setUser(null);
        });
    }
  }, []); // eslint-disable-line

  const handleLogin = useCallback((accessToken, userData) => {
    setToken(accessToken);
    setTokenState(accessToken);
    setUser(userData);
    localStorage.setItem('rook_user', JSON.stringify(userData));
  }, []);

  const logout = useCallback(() => {
    clearToken();
    localStorage.removeItem('rook_user');
    setTokenState(null);
    setUser(null);
  }, []);

  const updateCredits = useCallback((newCredits) => {
    setUser((prev) => {
      if (!prev) return prev;
      const updated = { ...prev, credits: newCredits };
      localStorage.setItem('rook_user', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const refreshProfile = useCallback(async () => {
    if (!token) return;
    try {
      const res = await getMe();
      const userData = res.user || res;
      setUser(userData);
      localStorage.setItem('rook_user', JSON.stringify(userData));
    } catch {
      // Silently fail
    }
  }, [token]);

  const value = {
    user,
    token,
    isLoggedIn,
    credits,
    isAdmin,
    login: handleLogin,
    logout,
    updateCredits,
    refreshProfile,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
