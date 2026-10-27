import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api/client';

const AuthContext = createContext(null);

export const DEMO_USERS = [
  {
    role: 'worker',
    name: 'Carlos Mendez (Construction)',
    email: 'worker.carlos@fairshift.demo',
    password: 'WorkerPass123!',
    tag: 'Worker: Construction'
  },
  {
    role: 'worker',
    name: 'Amina Patel (Gig Delivery)',
    email: 'worker.amina@fairshift.demo',
    password: 'WorkerPass123!',
    tag: 'Worker: Courier'
  },
  {
    role: 'employer_admin',
    name: 'Priya Shah (Platform Operations)',
    email: 'admin.priya@fairshift.demo',
    password: 'AdminPass123!',
    tag: 'Employer Admin: Platform'
  },
  {
    role: 'employer_admin',
    name: 'Sarah Jenkins (Operations Mgr)',
    email: 'admin.sarah@fairshift.demo',
    password: 'AdminPass123!',
    tag: 'Employer Admin'
  },
  {
    role: 'safety_officer',
    name: 'Marcus Vance (Safety Officer)',
    email: 'safety.marcus@fairshift.demo',
    password: 'SafetyPass123!',
    tag: 'Safety Officer'
  }
];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('fairshift_token');
    if (token) {
      api.get('/auth/me')
        .then(profile => setUser(profile))
        .catch(() => {
          localStorage.removeItem('fairshift_token');
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const data = await api.post('/auth/login', { email, password });
    localStorage.setItem('fairshift_token', data.access_token);
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem('fairshift_token');
    setUser(null);
  };

  const switchDemoUser = async (demoUser) => {
    return await login(demoUser.email, demoUser.password);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, switchDemoUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
