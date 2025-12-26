/**
 * Conecta Plus - Spike Test
 * Teste de pico para verificar comportamento sob carga repentina
 * Duracao: ~5 minutos
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6';

const errorRate = new Rate('errors');
const responseTime = new Trend('response_time');

// Simula um pico repentino de trafego
export const options = {
  stages: [
    { duration: '30s', target: 10 },    // Baseline
    { duration: '10s', target: 200 },   // Spike instantaneo!
    { duration: '1m', target: 200 },    // Manter pico
    { duration: '10s', target: 10 },    // Voltar ao normal
    { duration: '1m', target: 10 },     // Recuperacao
    { duration: '30s', target: 0 },     // Cooldown
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'],
    errors: ['rate<0.20'],  // Ate 20% de erros em spike
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const res = http.get(`${BASE_URL}/health`, {
    timeout: '5s',
  });

  responseTime.add(res.timings.duration);

  const success = check(res, {
    'status ok': (r) => r.status === 200 || r.status === 429,
    'response < 3s': (r) => r.timings.duration < 3000,
  });

  if (!success) {
    errorRate.add(1);
  }

  sleep(0.1);  // Muito rapido para maximizar carga
}
