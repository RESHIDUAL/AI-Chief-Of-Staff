import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api/client';

export interface UserProfile {
  user_id: string;
  email: string;
  name: string;
  role: 'employee' | 'manager' | 'leadership' | 'admin';
  allowed_groups: string[];
  avatar_url?: string;
}

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  loginDemo: (email?: string, role?: string) => Promise<void>;
  loginGoogle: () => void;
  logout: () => void;
  switchRole: (role: 'employee' | 'manager' | 'leadership' | 'admin') => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const DEMO_USER_DEFAULT: UserProfile = {
  user_id: 'demo-user',
  email: 'hackathon@demo.com',
  name: 'Demo User',
  role: 'leadership',
  allowed_groups: ['all', 'engineering', 'leadership'],
  avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150',
};

function parseJwtPayload(token: string): UserProfile | null {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const p = JSON.parse(jsonPayload);
    if (!p || (!p.email && !p.sub)) return null;
    return {
      user_id: p.sub || p.email || 'user',
      email: p.email || p.sub || 'user@gmail.com',
      name: p.name || p.email || 'Google User',
      role: p.role || 'leadership',
      allowed_groups: p.allowed_groups || ['all', 'engineering', 'leadership'],
      avatar_url: p.avatar_url,
    };
  } catch (e) {
    return null;
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Read #token=... from URL fragment (set by OAuth callback redirect)
  const extractTokenFromFragment = useCallback(() => {
    const hash = window.location.hash;
    if (hash.startsWith('#token=')) {
      const jwt = hash.slice('#token='.length);
      localStorage.setItem('cos_jwt_token', jwt);
      setToken(jwt);
      // Clear the URL fragment without triggering a reload
      window.history.replaceState(null, '', window.location.pathname);
      return jwt;
    }
    return null;
  }, []);

  // Fetch user profile from /auth/me or decode JWT payload
  const fetchMe = useCallback(async (jwt: string) => {
    if (jwt === 'demo-token') {
      setUser(DEMO_USER_DEFAULT);
      setToken('demo-token');
      return true;
    }

    const jwtUser = parseJwtPayload(jwt);
    if (jwtUser) {
      setUser(jwtUser);
      setToken(jwt);
    }

    try {
      const res = await apiClient.get('/auth/me', {
        headers: { Authorization: `Bearer ${jwt}` },
      });
      setUser(res.data);
      setToken(jwt);
      return true;
    } catch (e: any) {
      if (e.response?.status === 401) {
        localStorage.removeItem('cos_jwt_token');
        setToken(null);
        setUser(null);
      } else if (jwtUser) {
        setUser(jwtUser);
        setToken(jwt);
      } else {
        setUser(DEMO_USER_DEFAULT);
        setToken(jwt);
      }
      return false;
    }
  }, []);

  // Initialize auth state on mount
  useEffect(() => {
    const init = async () => {
      setLoading(true);

      // 1. Check for token in URL fragment (from OAuth redirect)
      const fragmentToken = extractTokenFromFragment();
      if (fragmentToken) {
        await fetchMe(fragmentToken);
        setLoading(false);
        return;
      }

      // 2. Check for existing token in localStorage
      const storedToken = localStorage.getItem('cos_jwt_token');
      if (storedToken) {
        await fetchMe(storedToken);
        setLoading(false);
        return;
      }

      // 3. No token found — unauthenticated
      setLoading(false);
    };

    init();
  }, [extractTokenFromFragment, fetchMe]);

  const isAuthenticated = !!user && !!token;

  const loginDemo = async (email = 'hackathon@demo.com', role = 'leadership') => {
    try {
      const res = await apiClient.post('/auth/login/demo', { email, role });
      const { access_token, user: u } = res.data;
      setToken(access_token);
      setUser(u);
      localStorage.setItem('cos_jwt_token', access_token);
    } catch (e) {
      console.warn('Demo API login call failed, logging in locally:', e);
      const fallbackUser: UserProfile = {
        ...DEMO_USER_DEFAULT,
        email,
        role: role as any,
      };
      setToken('demo-token');
      setUser(fallbackUser);
      localStorage.setItem('cos_jwt_token', 'demo-token');
    }
  };

  const loginGoogle = () => {
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
    window.location.href = `${apiBase}/auth/login/google`;
  };

  const switchRole = async (newRole: 'employee' | 'manager' | 'leadership' | 'admin') => {
    if (user) {
      await loginDemo(user.email, newRole);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('cos_jwt_token');
    window.location.replace('/');
  };

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated, loading, loginDemo, loginGoogle, logout, switchRole }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
