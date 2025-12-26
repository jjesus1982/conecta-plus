/**
 * Conecta Plus - Load Test
 * Teste de carga para simular uso normal do sistema
 * Duracao: ~10 minutos
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Metricas customizadas
const errorRate = new Rate('errors');
const loginDuration = new Trend('login_duration');
const dashboardDuration = new Trend('dashboard_duration');
const apiCalls = new Counter('api_calls');

// Configuracao do teste - ramp up, sustain, ramp down
export const options = {
  stages: [
    { duration: '2m', target: 20 },   // Ramp up para 20 usuarios
    { duration: '5m', target: 20 },   // Manter 20 usuarios
    { duration: '2m', target: 50 },   // Aumentar para 50
    { duration: '2m', target: 50 },   // Manter 50
    { duration: '1m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000', 'p(99)<2000'],
    errors: ['rate<0.05'],  // Max 5% de erros
    'login_duration': ['p(95)<500'],
    'dashboard_duration': ['p(95)<800'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_URL = `${BASE_URL}/api/v1`;

// Dados de teste
const testUsers = [
  { email: 'admin@conectaplus.com.br', password: 'admin123' },
];

export function setup() {
  // Login para obter token
  const loginRes = http.post(`${API_URL}/auth/login`, {
    username: testUsers[0].email,
    password: testUsers[0].password,
  }, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  if (loginRes.status !== 200) {
    console.warn('Login falhou no setup - alguns testes serao limitados');
    return { token: null };
  }

  const body = JSON.parse(loginRes.body);
  return { token: body.access_token };
}

export default function (data) {
  const authHeaders = data.token
    ? { Authorization: `Bearer ${data.token}` }
    : {};

  group('Health Checks', function () {
    const healthRes = http.get(`${BASE_URL}/health`);
    apiCalls.add(1);
    check(healthRes, { 'health ok': (r) => r.status === 200 }) || errorRate.add(1);
  });

  group('Public Endpoints', function () {
    const rootRes = http.get(`${BASE_URL}/`);
    apiCalls.add(1);
    check(rootRes, { 'root ok': (r) => r.status === 200 }) || errorRate.add(1);

    const apiInfoRes = http.get(`${API_URL}`);
    apiCalls.add(1);
    check(apiInfoRes, { 'api info ok': (r) => r.status === 200 }) || errorRate.add(1);
  });

  if (data.token) {
    group('Authenticated Endpoints', function () {
      // Dashboard
      const dashStart = Date.now();
      const dashRes = http.get(`${API_URL}/dashboard/resumo`, {
        headers: authHeaders,
      });
      dashboardDuration.add(Date.now() - dashStart);
      apiCalls.add(1);
      check(dashRes, { 'dashboard ok': (r) => r.status === 200 }) || errorRate.add(1);

      // Condominios
      const condosRes = http.get(`${API_URL}/condominios`, {
        headers: authHeaders,
      });
      apiCalls.add(1);
      check(condosRes, { 'condominios ok': (r) => r.status === 200 }) || errorRate.add(1);

      // Unidades
      const unidadesRes = http.get(`${API_URL}/unidades/`, {
        headers: authHeaders,
      });
      apiCalls.add(1);
      check(unidadesRes, { 'unidades ok': (r) => r.status === 200 || r.status === 404 }) || errorRate.add(1);

      // Moradores
      const moradoresRes = http.get(`${API_URL}/moradores`, {
        headers: authHeaders,
      });
      apiCalls.add(1);
      check(moradoresRes, { 'moradores ok': (r) => r.status === 200 }) || errorRate.add(1);
    });

    group('Financial Endpoints', function () {
      const finRes = http.get(`${API_URL}/financeiro/resumo`, {
        headers: authHeaders,
      });
      apiCalls.add(1);
      check(finRes, { 'financeiro ok': (r) => r.status === 200 }) || errorRate.add(1);
    });
  }

  sleep(Math.random() * 2 + 1); // 1-3 segundos entre requests
}

export function teardown(data) {
  console.log('Load test finalizado');
}
