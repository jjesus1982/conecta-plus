/**
 * Conecta Plus Mobile - API Service
 * Cliente HTTP configurado com axios
 */

import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import Constants from 'expo-constants';

// URL base da API
const API_URL = Constants.expoConfig?.extra?.apiUrl || 'http://localhost:8000/api/v1';

// Criar instância do axios
export const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para adicionar token
api.interceptors.request.use(
  async (config) => {
    try {
      const token = await SecureStore.getItemAsync('conecta_plus_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Erro ao obter token:', error);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor para tratar erros e refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Se erro 401 e não é retry
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = await SecureStore.getItemAsync('conecta_plus_refresh_token');

        if (refreshToken) {
          const response = await axios.post(`${API_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token } = response.data;
          await SecureStore.setItemAsync('conecta_plus_token', access_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Limpar tokens e redirecionar para login
        await SecureStore.deleteItemAsync('conecta_plus_token');
        await SecureStore.deleteItemAsync('conecta_plus_refresh_token');
        // O app vai detectar a falta de autenticação
      }
    }

    return Promise.reject(error);
  }
);

// === API Endpoints ===

// Auth
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', new URLSearchParams({ username: email, password }).toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  meCondominio: () => api.get('/auth/me/condominio'),
  ssoConfig: () => api.get('/auth/sso/config'),
  googleLogin: () => api.get('/auth/google/login'),
  microsoftLogin: () => api.get('/auth/microsoft/login'),
  ldapLogin: (username: string, password: string, domain?: string) =>
    api.post('/auth/ldap/login', { username, password, domain }),
};

// Dashboard
export const dashboardApi = {
  getStats: () => api.get('/dashboard'),
  getRecentEvents: () => api.get('/dashboard/eventos'),
};

// CFTV
export const cftvApi = {
  listCameras: () => api.get('/cftv/cameras'),
  getCamera: (id: string) => api.get(`/cftv/cameras/${id}`),
  getSnapshot: (id: string) => api.get(`/cftv/cameras/${id}/snapshot`),
  getStream: (id: string, type?: string) => api.get(`/cftv/cameras/${id}/stream`, { params: { type } }),
};

// Frigate NVR
export const frigateApi = {
  listInstances: () => api.get('/frigate/instances'),
  getStats: (instanceId: string) => api.get(`/frigate/instances/${instanceId}/stats`),
  listCameras: (instanceId: string) => api.get(`/frigate/instances/${instanceId}/cameras`),
  getSnapshot: (instanceId: string, camera: string) =>
    api.get(`/frigate/instances/${instanceId}/cameras/${camera}/snapshot`),
  getStream: (instanceId: string, camera: string, type?: string) =>
    api.get(`/frigate/instances/${instanceId}/cameras/${camera}/stream`, { params: { stream_type: type } }),
  getEvents: (instanceId: string, params?: object) =>
    api.get(`/frigate/instances/${instanceId}/events`, { params }),
  getRecordings: (instanceId: string, camera: string, params?: object) =>
    api.get(`/frigate/instances/${instanceId}/cameras/${camera}/recordings`, { params }),
};

// Acesso
export const acessoApi = {
  getRecent: (limit?: number) => api.get('/acesso', { params: { limit } }),
  register: (data: object) => api.post('/acesso', data),
  getById: (id: string) => api.get(`/acesso/${id}`),
  authorizeVisitor: (id: string) => api.post(`/acesso/${id}/autorizar`),
};

// Ocorrências
export const ocorrenciasApi = {
  list: (params?: object) => api.get('/ocorrencias', { params }),
  create: (data: FormData) => api.post('/ocorrencias', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  getById: (id: string) => api.get(`/ocorrencias/${id}`),
  update: (id: string, data: object) => api.patch(`/ocorrencias/${id}`, data),
  addComment: (id: string, comment: string) => api.post(`/ocorrencias/${id}/comentarios`, { comentario: comment }),
};

// Reservas
export const reservasApi = {
  list: (params?: object) => api.get('/reservas', { params }),
  create: (data: object) => api.post('/reservas', data),
  getById: (id: string) => api.get(`/reservas/${id}`),
  cancel: (id: string) => api.post(`/reservas/${id}/cancelar`),
  getAreas: () => api.get('/reservas/areas'),
  getAvailability: (areaId: string, date: string) => api.get(`/reservas/areas/${areaId}/disponibilidade`, { params: { data: date } }),
};

// Comunicados
export const comunicadosApi = {
  list: (params?: object) => api.get('/comunicados', { params }),
  getById: (id: string) => api.get(`/comunicados/${id}`),
  markAsRead: (id: string) => api.post(`/comunicados/${id}/lido`),
};

// Financeiro
export const financeiroApi = {
  getBoletos: (params?: object) => api.get('/financeiro/boletos', { params }),
  getBoleto: (id: string) => api.get(`/financeiro/boletos/${id}`),
  getExtrato: (params?: object) => api.get('/financeiro/extrato', { params }),
  getPixCode: (boletoId: string) => api.get(`/financeiro/boletos/${boletoId}/pix`),
};

// Encomendas
export const encomendasApi = {
  list: (params?: object) => api.get('/encomendas', { params }),
  getById: (id: string) => api.get(`/encomendas/${id}`),
  confirm: (id: string) => api.post(`/encomendas/${id}/confirmar`),
};

// Portaria
export const portariaApi = {
  getStatus: () => api.get('/portaria/status'),
  openGate: (gateId: string) => api.post(`/portaria/portoes/${gateId}/abrir`),
  callIntercom: (unitId: string) => api.post(`/portaria/interfone/${unitId}/chamar`),
  registerVisitor: (data: object) => api.post('/portaria/visitantes', data),
};

// Alarmes
export const alarmesApi = {
  list: (params?: object) => api.get('/alarmes', { params }),
  getZones: () => api.get('/alarmes/zonas'),
  arm: (zoneId: string) => api.post(`/alarmes/zonas/${zoneId}/armar`),
  disarm: (zoneId: string) => api.post(`/alarmes/zonas/${zoneId}/desarmar`),
  acknowledge: (alertId: string) => api.post(`/alarmes/${alertId}/reconhecer`),
};
