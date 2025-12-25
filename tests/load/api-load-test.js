import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 10 },  // Ramp up to 10 users
    { duration: '1m', target: 50 },   // Stay at 50 users
    { duration: '30s', target: 100 }, // Spike to 100 users
    { duration: '1m', target: 50 },   // Back to 50 users
    { duration: '30s', target: 0 },   // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500'], // 95% of requests should complete within 500ms
    'errors': ['rate<0.1'],              // Error rate should be less than 10%
  },
};

const BASE_URL = 'http://localhost:3001';

// Test login to get token (run once per VU)
let token = null;

export function setup() {
  // Login once to get a valid token
  const loginRes = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({
    email: 'admin@conectaplus.com.br',
    senha: 'admin123',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  if (loginRes.status === 200) {
    const body = JSON.parse(loginRes.body);
    return { token: body.access_token || body.token };
  }

  return { token: null };
}

export default function (data) {
  const headers = data.token ? {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  } : {
    'Content-Type': 'application/json',
  };

  // Test 1: Dashboard Statistics
  {
    const res = http.get(`${BASE_URL}/api/dashboard/estatisticas`, { headers });
    const success = check(res, {
      'dashboard status is 200 or 401': (r) => r.status === 200 || r.status === 401,
      'dashboard response time < 500ms': (r) => r.timings.duration < 500,
    });
    errorRate.add(!success);
  }

  sleep(1);

  // Test 2: List Condominios
  {
    const res = http.get(`${BASE_URL}/api/condominios`, { headers });
    const success = check(res, {
      'condominios status is 200 or 401': (r) => r.status === 200 || r.status === 401,
      'condominios response time < 500ms': (r) => r.timings.duration < 500,
    });
    errorRate.add(!success);
  }

  sleep(1);

  // Test 3: Financial IA Score (if authenticated)
  if (data.token) {
    const res = http.get(`${BASE_URL}/api/financeiro/ia/score/unit_001`, { headers });
    const success = check(res, {
      'score status is 200 or 404': (r) => r.status === 200 || r.status === 404,
      'score response time < 1000ms': (r) => r.timings.duration < 1000,
    });
    errorRate.add(!success);
  }

  sleep(2);
}

export function teardown(data) {
  // Cleanup if needed
  console.log('Load test completed');
}
