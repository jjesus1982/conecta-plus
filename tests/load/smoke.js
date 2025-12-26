/**
 * Conecta Plus - Smoke Test
 * Teste rapido para verificar se o sistema esta respondendo
 * Duracao: ~1 minuto
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Metricas customizadas
const errorRate = new Rate('errors');
const healthLatency = new Trend('health_latency');

// Configuracao do teste
export const options = {
  vus: 5,           // 5 usuarios virtuais
  duration: '1m',   // 1 minuto
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% das requests < 500ms
    errors: ['rate<0.01'],              // Error rate < 1%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // Health check
  const healthRes = http.get(`${BASE_URL}/health`);
  healthLatency.add(healthRes.timings.duration);

  const healthOk = check(healthRes, {
    'health status 200': (r) => r.status === 200,
    'health has status field': (r) => JSON.parse(r.body).status !== undefined,
  });
  errorRate.add(!healthOk);

  sleep(1);

  // API info
  const apiRes = http.get(`${BASE_URL}/api/v1`);

  const apiOk = check(apiRes, {
    'api info status 200': (r) => r.status === 200,
    'api has version': (r) => JSON.parse(r.body).version !== undefined,
  });
  errorRate.add(!apiOk);

  sleep(1);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'tests/load/results/smoke-summary.json': JSON.stringify(data, null, 2),
  };
}

function textSummary(data, options) {
  const lines = [];
  lines.push('='.repeat(60));
  lines.push('SMOKE TEST - Conecta Plus');
  lines.push('='.repeat(60));
  lines.push(`Total Requests: ${data.metrics.http_reqs.values.count}`);
  lines.push(`Failed Requests: ${data.metrics.http_req_failed?.values.passes || 0}`);
  lines.push(`Avg Duration: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
  lines.push(`P95 Duration: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
  lines.push('='.repeat(60));
  return lines.join('\n');
}
