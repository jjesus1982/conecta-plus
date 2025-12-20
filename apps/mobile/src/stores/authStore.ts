/**
 * Conecta Plus Mobile - Auth Store
 * Gerenciamento de estado de autenticação com Zustand
 */

import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { api } from '../services/api';

interface User {
  id: string;
  email: string;
  nome: string;
  role: 'admin' | 'sindico' | 'gerente' | 'porteiro' | 'morador' | 'visitante';
  avatar_url?: string;
  condominio_id?: string;
}

interface Condominio {
  id: string;
  nome: string;
  endereco: string;
  logo_url?: string;
}

interface AuthState {
  user: User | null;
  condominio: Condominio | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  loginWithMicrosoft: () => Promise<void>;
  loginWithLDAP: (username: string, password: string, domain?: string) => Promise<void>;
  logout: () => Promise<void>;
  loadStoredAuth: () => Promise<void>;
  refreshAccessToken: () => Promise<void>;
  updateUser: (user: Partial<User>) => void;
}

const TOKEN_KEY = 'conecta_plus_token';
const REFRESH_TOKEN_KEY = 'conecta_plus_refresh_token';
const USER_KEY = 'conecta_plus_user';

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  condominio: null,
  token: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,

  login: async (email: string, password: string) => {
    set({ isLoading: true });

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post('/auth/login', formData.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      const { access_token, refresh_token, user_id } = response.data;

      // Buscar dados do usuário
      const userResponse = await api.get('/auth/me', {
        headers: { Authorization: `Bearer ${access_token}` },
      });

      const user = userResponse.data;

      // Salvar tokens de forma segura
      await SecureStore.setItemAsync(TOKEN_KEY, access_token);
      if (refresh_token) {
        await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refresh_token);
      }
      await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user));

      // Configurar token no axios
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      set({
        user,
        token: access_token,
        refreshToken: refresh_token,
        isAuthenticated: true,
        isLoading: false,
      });

      // Buscar condomínio se o usuário tiver um
      if (user.condominio_id) {
        try {
          const condoResponse = await api.get('/auth/me/condominio');
          set({ condominio: condoResponse.data });
        } catch (e) {
          console.warn('Erro ao buscar condomínio:', e);
        }
      }
    } catch (error: any) {
      set({ isLoading: false });
      throw new Error(error.response?.data?.detail || 'Erro ao fazer login');
    }
  },

  loginWithGoogle: async () => {
    set({ isLoading: true });
    try {
      // Obter URL de autenticação
      const response = await api.get('/auth/google/login');
      const { auth_url } = response.data;

      // Abrir URL no navegador (o app deve tratar o callback)
      // Linking.openURL(auth_url);

      // O fluxo OAuth será completado via deep link
      set({ isLoading: false });

      return auth_url;
    } catch (error: any) {
      set({ isLoading: false });
      throw new Error('Erro ao iniciar login com Google');
    }
  },

  loginWithMicrosoft: async () => {
    set({ isLoading: true });
    try {
      const response = await api.get('/auth/microsoft/login');
      const { auth_url } = response.data;
      set({ isLoading: false });
      return auth_url;
    } catch (error: any) {
      set({ isLoading: false });
      throw new Error('Erro ao iniciar login com Microsoft');
    }
  },

  loginWithLDAP: async (username: string, password: string, domain?: string) => {
    set({ isLoading: true });

    try {
      const response = await api.post('/auth/ldap/login', {
        username,
        password,
        domain,
      });

      const { access_token, refresh_token } = response.data;

      // Buscar dados do usuário
      const userResponse = await api.get('/auth/me', {
        headers: { Authorization: `Bearer ${access_token}` },
      });

      const user = userResponse.data;

      // Salvar tokens
      await SecureStore.setItemAsync(TOKEN_KEY, access_token);
      if (refresh_token) {
        await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refresh_token);
      }
      await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user));

      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      set({
        user,
        token: access_token,
        refreshToken: refresh_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error: any) {
      set({ isLoading: false });
      throw new Error(error.response?.data?.detail || 'Credenciais inválidas');
    }
  },

  logout: async () => {
    try {
      await api.post('/auth/logout');
    } catch (e) {
      // Ignorar erros de logout
    }

    // Limpar armazenamento
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
    await SecureStore.deleteItemAsync(USER_KEY);

    // Limpar header de autenticação
    delete api.defaults.headers.common['Authorization'];

    set({
      user: null,
      condominio: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
    });
  },

  loadStoredAuth: async () => {
    try {
      const [token, refreshToken, userJson] = await Promise.all([
        SecureStore.getItemAsync(TOKEN_KEY),
        SecureStore.getItemAsync(REFRESH_TOKEN_KEY),
        SecureStore.getItemAsync(USER_KEY),
      ]);

      if (token && userJson) {
        const user = JSON.parse(userJson);

        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;

        set({
          user,
          token,
          refreshToken,
          isAuthenticated: true,
        });

        // Verificar se token ainda é válido
        try {
          const response = await api.get('/auth/me');
          set({ user: response.data });

          // Buscar condomínio
          if (response.data.condominio_id) {
            const condoResponse = await api.get('/auth/me/condominio');
            set({ condominio: condoResponse.data });
          }
        } catch (e) {
          // Token expirado, tentar refresh
          if (refreshToken) {
            await get().refreshAccessToken();
          } else {
            await get().logout();
          }
        }
      }
    } catch (error) {
      console.error('Erro ao carregar autenticação:', error);
    }
  },

  refreshAccessToken: async () => {
    const { refreshToken } = get();

    if (!refreshToken) {
      await get().logout();
      return;
    }

    try {
      const response = await api.post('/auth/refresh', {
        refresh_token: refreshToken,
      });

      const { access_token } = response.data;

      await SecureStore.setItemAsync(TOKEN_KEY, access_token);
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      set({ token: access_token });
    } catch (error) {
      // Refresh falhou, fazer logout
      await get().logout();
    }
  },

  updateUser: (updates: Partial<User>) => {
    const { user } = get();
    if (user) {
      const updatedUser = { ...user, ...updates };
      set({ user: updatedUser });
      SecureStore.setItemAsync(USER_KEY, JSON.stringify(updatedUser));
    }
  },
}));
