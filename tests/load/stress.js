/**
 * Conecta Plus - Stress Test
 * Teste de stress para encontrar o ponto de ruptura
 * Duracao: ~15 minutos
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';

// Metricas customizadas
const errorRate = new Rate('errors');
const reqDuration = new Trend('request_duration');
const activeUsers = new Gauge('active_users');
const breakingPoint = new Counter('breaking_point_errors');

// Configuracao - aumento progressivo ate quebrar
export const options = {
  stages: [
    { duration: '2m', target: 50 },    // Aquecimento
    { duration: '2m', target: 100 },   // Carga normal-alta
    { duration: '2m', target: 200 },   // Stress
    { duration: '2m', target: 300 },   // Heavy stress
    { duration: '2m', target: 400 },   // Breaking point test
    { duration: '2m', target: 500 },   // Max stress
    { duration: '3m', target: 0 },     // Recovery
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],  // Aceitar ate 5s em stress
    http_req_failed: ['rate<0.30'],     // Ate 30% de falhas em stress
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  activeUsers.add(__VU);

  const endpoints = [
    '/health',
    '/api/v1',
    '/',
  ];

  const endpoint = endpoints[Math.floor(Math.random() * endpoints.length)];

  const start = Date.now();
  const res = http.get(`${BASE_URL}${endpoint}`, {
    timeout: '10s',
  });
  const duration = Date.now() - start;

  reqDuration.add(duration);

  const success = check(res, {
    'status is 2xx or 429': (r) => r.status >= 200 && r.status < 300 || r.status === 429,
    'response time < 5s': (r) => r.timings.duration < 5000,
  });

  if (!success) {
    errorRate.add(1);
    if (res.status >= 500) {
      breakingPoint.add(1);
    }
  }

  // Menos sleep em stress test para maximizar carga
  sleep(Math.random() * 0.5);
}

export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    test: 'stress',
    metrics: {
      total_requests: data.metrics.http_reqs?.values.count || 0,
      failed_requests: data.metrics.http_req_failed?.values.passes || 0,
      avg_duration_ms: data.metrics.http_req_duration?.values.avg || 0,
      p95_duration_ms: data.metrics.http_req_duration?.values['p(95)'] || 0,
      p99_duration_ms: data.metrics.http_req_duration?.values['p(99)'] || 0,
      max_duration_ms: data.metrics.http_req_duration?.values.max || 0,
      rps: data.metrics.http_reqs?.values.rate || 0,
    },
    thresholds: {
      passed: Object.values(data.root_group?.checks || {}).every(c => c.passes > c.fails),
    },
  };

  return {
    'tests/load/results/stress-summary.json': JSON.stringify(summary, null, 2),
    stdout: generateTextReport(summary),
  };
}

function generateTextReport(summary) {
  return `
================================================================================
                    STRESS TEST REPORT - Conecta Plus
================================================================================
Timestamp: ${summary.timestamp}

METRICAS DE PERFORMANCE
-----------------------
Total Requests:    ${summary.metrics.total_requests}
Failed Requests:   ${summary.metrics.failed_requests}
Requests/sec:      ${summary.metrics.rps.toFixed(2)}

LATENCIA
--------
Average:           ${summary.metrics.avg_duration_ms.toFixed(2)}ms
P95:               ${summary.metrics.p95_duration_ms.toFixed(2)}ms
P99:               ${summary.metrics.p99_duration_ms.toFixed(2)}ms
Max:               ${summary.metrics.max_duration_ms.toFixed(2)}ms

RESULTADO: ${summary.thresholds.passed ? 'PASSED' : 'FAILED'}
================================================================================
`;
}
