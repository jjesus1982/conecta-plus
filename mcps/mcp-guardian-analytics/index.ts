/**
 * MCP Guardian Analytics - Analises e Relatorios de Seguranca
 * Conecta Plus - Plataforma de Gestao Condominial
 *
 * Funcionalidades:
 * - Geracao de relatorios de seguranca
 * - Analises de tendencias
 * - Metricas e KPIs
 * - Exportacao de dados
 * - Dashboards customizados
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  {
    name: 'mcp-guardian-analytics',
    version: '2.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// === Tipos ===

type ReportType = 'daily' | 'weekly' | 'monthly' | 'custom';
type ReportFormat = 'json' | 'pdf' | 'excel' | 'csv';
type MetricPeriod = 'hour' | 'day' | 'week' | 'month';

interface ReportConfig {
  id: string;
  name: string;
  type: ReportType;
  sections: string[];
  schedule?: string;
  recipients?: string[];
  format: ReportFormat;
}

interface MetricData {
  name: string;
  value: number;
  unit: string;
  trend: 'up' | 'down' | 'stable';
  changePercent: number;
  period: MetricPeriod;
}

interface TimeSeriesPoint {
  timestamp: string;
  value: number;
}

interface HeatmapData {
  location: string;
  hour: number;
  dayOfWeek: number;
  value: number;
}

interface AnomalyData {
  id: string;
  type: string;
  description: string;
  severity: number;
  detectedAt: string;
  affectedMetric: string;
  expectedValue: number;
  actualValue: number;
}

// === Estado ===

const reportConfigs: Map<string, ReportConfig> = new Map();
const scheduledReports: Map<string, { config: ReportConfig; lastRun?: string; nextRun: string }> = new Map();

// Dados simulados para analytics
const mockMetrics = {
  accessGranted24h: { value: 487, change: 5 },
  accessDenied24h: { value: 12, change: -15 },
  alertsGenerated24h: { value: 8, change: 20 },
  incidentsResolved24h: { value: 3, change: 0 },
  avgResponseTime: { value: 45, change: -10 },
  camerasOnline: { value: 23, change: 0 },
  riskScore: { value: 35, change: -5 },
};

// === Helpers ===

function generateId(prefix: string): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 8);
  return `${prefix}_${timestamp}_${random}`;
}

function generateTimeSeriesData(hours: number, baseValue: number, variance: number): TimeSeriesPoint[] {
  const data: TimeSeriesPoint[] = [];
  const now = Date.now();
  for (let i = hours; i >= 0; i--) {
    const timestamp = new Date(now - i * 60 * 60 * 1000).toISOString();
    const value = baseValue + (Math.random() - 0.5) * variance * 2;
    data.push({ timestamp, value: Math.round(value) });
  }
  return data;
}

function generateHeatmapData(): HeatmapData[] {
  const locations = ['Entrada Principal', 'Portaria Social', 'Garagem A', 'Garagem B', 'Bloco A', 'Bloco B'];
  const data: HeatmapData[] = [];

  for (const location of locations) {
    for (let hour = 0; hour < 24; hour++) {
      for (let day = 0; day < 7; day++) {
        // Simular padroes reais (mais movimento em horarios comerciais)
        let baseValue = 5;
        if (hour >= 7 && hour <= 9) baseValue = 30; // Pico manha
        if (hour >= 17 && hour <= 19) baseValue = 35; // Pico tarde
        if (hour >= 22 || hour <= 5) baseValue = 2; // Madrugada
        if (day >= 5) baseValue *= 0.6; // Fim de semana

        const value = Math.round(baseValue * (0.8 + Math.random() * 0.4));
        data.push({ location, hour, dayOfWeek: day, value });
      }
    }
  }
  return data;
}

// === Tools Definition ===

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    // === Metrics ===
    {
      name: 'analytics_get_metrics',
      description: 'Obtem metricas principais de seguranca',
      inputSchema: {
        type: 'object',
        properties: {
          period: { type: 'string', enum: ['hour', 'day', 'week', 'month'] },
          metrics: { type: 'array', items: { type: 'string' }, description: 'Metricas especificas (opcional)' },
        },
      },
    },
    {
      name: 'analytics_get_kpis',
      description: 'Obtem KPIs de seguranca',
      inputSchema: {
        type: 'object',
        properties: {
          category: { type: 'string', enum: ['access', 'incidents', 'cameras', 'response', 'risk'] },
        },
      },
    },
    {
      name: 'analytics_compare_periods',
      description: 'Compara metricas entre dois periodos',
      inputSchema: {
        type: 'object',
        properties: {
          metric: { type: 'string' },
          period1_start: { type: 'string' },
          period1_end: { type: 'string' },
          period2_start: { type: 'string' },
          period2_end: { type: 'string' },
        },
        required: ['metric', 'period1_start', 'period1_end', 'period2_start', 'period2_end'],
      },
    },

    // === Time Series ===
    {
      name: 'analytics_get_timeseries',
      description: 'Obtem dados de serie temporal',
      inputSchema: {
        type: 'object',
        properties: {
          metric: { type: 'string', description: 'Nome da metrica' },
          hours: { type: 'number', description: 'Ultimas N horas' },
          granularity: { type: 'string', enum: ['minute', 'hour', 'day'] },
        },
        required: ['metric'],
      },
    },
    {
      name: 'analytics_get_heatmap',
      description: 'Obtem dados para heatmap de atividade',
      inputSchema: {
        type: 'object',
        properties: {
          type: { type: 'string', enum: ['access', 'alerts', 'incidents'] },
          location: { type: 'string', description: 'Filtrar por local' },
        },
      },
    },

    // === Trends & Predictions ===
    {
      name: 'analytics_get_trends',
      description: 'Analisa tendencias de metricas',
      inputSchema: {
        type: 'object',
        properties: {
          metrics: { type: 'array', items: { type: 'string' } },
          period_days: { type: 'number' },
        },
      },
    },
    {
      name: 'analytics_get_predictions',
      description: 'Obtem predicoes baseadas em dados historicos',
      inputSchema: {
        type: 'object',
        properties: {
          metric: { type: 'string' },
          hours_ahead: { type: 'number' },
        },
        required: ['metric'],
      },
    },
    {
      name: 'analytics_get_anomalies',
      description: 'Lista anomalias detectadas',
      inputSchema: {
        type: 'object',
        properties: {
          hours: { type: 'number' },
          min_severity: { type: 'number' },
          type: { type: 'string' },
        },
      },
    },

    // === Reports ===
    {
      name: 'analytics_generate_report',
      description: 'Gera um relatorio de seguranca',
      inputSchema: {
        type: 'object',
        properties: {
          type: { type: 'string', enum: ['daily', 'weekly', 'monthly', 'custom'] },
          sections: {
            type: 'array',
            items: { type: 'string' },
            description: 'Secoes: access_summary, incidents, alerts, risk_analysis, recommendations',
          },
          period_start: { type: 'string' },
          period_end: { type: 'string' },
          format: { type: 'string', enum: ['json', 'pdf', 'excel', 'csv'] },
        },
        required: ['type'],
      },
    },
    {
      name: 'analytics_get_daily_summary',
      description: 'Obtem resumo diario de seguranca',
      inputSchema: {
        type: 'object',
        properties: {
          date: { type: 'string', description: 'Data (YYYY-MM-DD), padrao: hoje' },
        },
      },
    },
    {
      name: 'analytics_create_report_config',
      description: 'Cria configuracao de relatorio recorrente',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          name: { type: 'string' },
          type: { type: 'string', enum: ['daily', 'weekly', 'monthly'] },
          sections: { type: 'array', items: { type: 'string' } },
          schedule: { type: 'string', description: 'Cron expression' },
          recipients: { type: 'array', items: { type: 'string' } },
          format: { type: 'string', enum: ['json', 'pdf', 'excel', 'csv'] },
        },
        required: ['id', 'name', 'type', 'sections'],
      },
    },
    {
      name: 'analytics_list_scheduled_reports',
      description: 'Lista relatorios agendados',
      inputSchema: { type: 'object', properties: {} },
    },

    // === Access Analytics ===
    {
      name: 'analytics_access_summary',
      description: 'Resumo de acessos por periodo',
      inputSchema: {
        type: 'object',
        properties: {
          period_hours: { type: 'number' },
          group_by: { type: 'string', enum: ['hour', 'day', 'access_point', 'person_type'] },
          access_point_id: { type: 'string' },
        },
      },
    },
    {
      name: 'analytics_access_patterns',
      description: 'Analisa padroes de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          person_id: { type: 'string' },
          unit: { type: 'string' },
          period_days: { type: 'number' },
        },
      },
    },
    {
      name: 'analytics_peak_hours',
      description: 'Identifica horarios de pico',
      inputSchema: {
        type: 'object',
        properties: {
          access_point_id: { type: 'string' },
          period_days: { type: 'number' },
        },
      },
    },

    // === Incident Analytics ===
    {
      name: 'analytics_incident_summary',
      description: 'Resumo de incidentes',
      inputSchema: {
        type: 'object',
        properties: {
          period_days: { type: 'number' },
          severity: { type: 'string' },
          type: { type: 'string' },
        },
      },
    },
    {
      name: 'analytics_response_times',
      description: 'Analise de tempos de resposta',
      inputSchema: {
        type: 'object',
        properties: {
          period_days: { type: 'number' },
          by_severity: { type: 'boolean' },
          by_type: { type: 'boolean' },
        },
      },
    },
    {
      name: 'analytics_incident_hotspots',
      description: 'Identifica locais com mais incidentes',
      inputSchema: {
        type: 'object',
        properties: {
          period_days: { type: 'number' },
          limit: { type: 'number' },
        },
      },
    },

    // === Risk Analytics ===
    {
      name: 'analytics_risk_evolution',
      description: 'Evolucao do score de risco ao longo do tempo',
      inputSchema: {
        type: 'object',
        properties: {
          period_days: { type: 'number' },
          granularity: { type: 'string', enum: ['hour', 'day'] },
        },
      },
    },
    {
      name: 'analytics_risk_factors',
      description: 'Analise dos fatores de risco',
      inputSchema: {
        type: 'object',
        properties: {
          period_days: { type: 'number' },
        },
      },
    },
    {
      name: 'analytics_vulnerability_windows',
      description: 'Identifica janelas de vulnerabilidade',
      inputSchema: {
        type: 'object',
        properties: {
          period_days: { type: 'number' },
          threshold: { type: 'number', description: 'Score minimo para considerar vulneravel' },
        },
      },
    },

    // === Export ===
    {
      name: 'analytics_export_data',
      description: 'Exporta dados para analise externa',
      inputSchema: {
        type: 'object',
        properties: {
          data_type: { type: 'string', enum: ['access_logs', 'incidents', 'alerts', 'metrics'] },
          period_start: { type: 'string' },
          period_end: { type: 'string' },
          format: { type: 'string', enum: ['json', 'csv'] },
          filters: { type: 'object' },
        },
        required: ['data_type'],
      },
    },

    // === Dashboard ===
    {
      name: 'analytics_dashboard_data',
      description: 'Obtem todos os dados para dashboard de analytics',
      inputSchema: { type: 'object', properties: {} },
    },
  ],
}));

// === Tool Handlers ===

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const params = args as Record<string, unknown>;

  try {
    switch (name) {
      // === Metrics ===
      case 'analytics_get_metrics': {
        const period = (params.period as MetricPeriod) || 'day';
        const metrics: MetricData[] = [
          {
            name: 'access_granted',
            value: mockMetrics.accessGranted24h.value,
            unit: 'acessos',
            trend: mockMetrics.accessGranted24h.change > 0 ? 'up' : 'down',
            changePercent: mockMetrics.accessGranted24h.change,
            period,
          },
          {
            name: 'access_denied',
            value: mockMetrics.accessDenied24h.value,
            unit: 'acessos',
            trend: mockMetrics.accessDenied24h.change > 0 ? 'up' : 'down',
            changePercent: mockMetrics.accessDenied24h.change,
            period,
          },
          {
            name: 'alerts_generated',
            value: mockMetrics.alertsGenerated24h.value,
            unit: 'alertas',
            trend: mockMetrics.alertsGenerated24h.change > 0 ? 'up' : 'down',
            changePercent: mockMetrics.alertsGenerated24h.change,
            period,
          },
          {
            name: 'incidents_resolved',
            value: mockMetrics.incidentsResolved24h.value,
            unit: 'incidentes',
            trend: 'stable',
            changePercent: 0,
            period,
          },
          {
            name: 'avg_response_time',
            value: mockMetrics.avgResponseTime.value,
            unit: 'segundos',
            trend: mockMetrics.avgResponseTime.change < 0 ? 'down' : 'up',
            changePercent: mockMetrics.avgResponseTime.change,
            period,
          },
          {
            name: 'risk_score',
            value: mockMetrics.riskScore.value,
            unit: 'pontos',
            trend: mockMetrics.riskScore.change < 0 ? 'down' : 'up',
            changePercent: mockMetrics.riskScore.change,
            period,
          },
        ];

        let filtered = metrics;
        if (params.metrics) {
          filtered = metrics.filter(m => (params.metrics as string[]).includes(m.name));
        }

        return { content: [{ type: 'text', text: JSON.stringify({ metrics: filtered, period }) }] };
      }

      case 'analytics_get_kpis': {
        const kpis: Record<string, unknown> = {
          access: {
            total_access_24h: 499,
            success_rate: 97.6,
            avg_daily_access: 485,
            peak_hour: 18,
            busiest_access_point: 'Entrada Principal',
          },
          incidents: {
            total_30d: 12,
            avg_resolution_time: '2h 15min',
            escalation_rate: 16.7,
            resolved_rate: 91.7,
            most_common_type: 'Atividade Suspeita',
          },
          cameras: {
            total: 24,
            online: 23,
            availability: 95.8,
            detections_24h: 1247,
            storage_days: 30,
          },
          response: {
            avg_acknowledgment: '45s',
            avg_resolution: '2h 15min',
            sla_compliance: 94.2,
            escalations_24h: 1,
          },
          risk: {
            current_score: 35,
            avg_30d: 38,
            highest_30d: 72,
            lowest_30d: 22,
            trend: 'stable',
          },
        };

        if (params.category) {
          return { content: [{ type: 'text', text: JSON.stringify({ kpis: kpis[params.category as string] }) }] };
        }
        return { content: [{ type: 'text', text: JSON.stringify({ kpis }) }] };
      }

      case 'analytics_compare_periods': {
        const period1 = { start: params.period1_start, end: params.period1_end, value: 450 };
        const period2 = { start: params.period2_start, end: params.period2_end, value: 487 };
        const change = ((period2.value - period1.value) / period1.value) * 100;

        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              metric: params.metric,
              period1,
              period2,
              change_percent: Math.round(change * 10) / 10,
              trend: change > 0 ? 'up' : change < 0 ? 'down' : 'stable',
            }),
          }],
        };
      }

      // === Time Series ===
      case 'analytics_get_timeseries': {
        const hours = (params.hours as number) || 24;
        const data = generateTimeSeriesData(hours, 20, 10);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              metric: params.metric,
              granularity: params.granularity || 'hour',
              data,
            }),
          }],
        };
      }

      case 'analytics_get_heatmap': {
        let data = generateHeatmapData();
        if (params.location) {
          data = data.filter(d => d.location === params.location);
        }
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              type: params.type || 'access',
              data,
            }),
          }],
        };
      }

      // === Trends & Predictions ===
      case 'analytics_get_trends': {
        const metrics = (params.metrics as string[]) || ['access_granted', 'alerts', 'risk_score'];
        const trends = metrics.map(metric => ({
          metric,
          direction: Math.random() > 0.5 ? 'up' : 'down',
          change_percent: Math.round((Math.random() - 0.5) * 40),
          confidence: Math.round(70 + Math.random() * 25),
          data: generateTimeSeriesData((params.period_days as number) || 7, 100, 30),
        }));
        return { content: [{ type: 'text', text: JSON.stringify({ trends }) }] };
      }

      case 'analytics_get_predictions': {
        const hoursAhead = (params.hours_ahead as number) || 24;
        const predictions = generateTimeSeriesData(hoursAhead, 25, 8);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              metric: params.metric,
              predictions,
              confidence: 78,
              methodology: 'ARIMA + seasonal decomposition',
            }),
          }],
        };
      }

      case 'analytics_get_anomalies': {
        const anomalies: AnomalyData[] = [
          {
            id: generateId('ANO'),
            type: 'frequency_spike',
            description: 'Pico de acessos na Garagem B acima do esperado',
            severity: 0.6,
            detectedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
            affectedMetric: 'access_count',
            expectedValue: 15,
            actualValue: 42,
          },
          {
            id: generateId('ANO'),
            type: 'unusual_timing',
            description: 'Atividade fora do padrao no Bloco C as 3h',
            severity: 0.75,
            detectedAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
            affectedMetric: 'detection_count',
            expectedValue: 0,
            actualValue: 8,
          },
        ];

        let filtered = anomalies;
        if (params.min_severity) {
          filtered = anomalies.filter(a => a.severity >= (params.min_severity as number));
        }
        if (params.type) {
          filtered = filtered.filter(a => a.type === params.type);
        }

        return { content: [{ type: 'text', text: JSON.stringify({ anomalies: filtered }) }] };
      }

      // === Reports ===
      case 'analytics_generate_report': {
        const reportId = generateId('REP');
        const sections = (params.sections as string[]) || ['access_summary', 'incidents', 'risk_analysis'];

        const report = {
          id: reportId,
          type: params.type,
          generated_at: new Date().toISOString(),
          period: {
            start: params.period_start || new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
            end: params.period_end || new Date().toISOString(),
          },
          format: params.format || 'json',
          sections: sections.reduce((acc, section) => {
            switch (section) {
              case 'access_summary':
                acc[section] = {
                  total: 487,
                  granted: 475,
                  denied: 12,
                  by_type: { resident: 320, visitor: 95, employee: 60, service: 12 },
                };
                break;
              case 'incidents':
                acc[section] = {
                  total: 3,
                  by_severity: { low: 1, medium: 1, high: 1 },
                  resolved: 2,
                  pending: 1,
                };
                break;
              case 'alerts':
                acc[section] = {
                  total: 8,
                  by_type: { person_detected: 3, vehicle: 2, loitering: 2, other: 1 },
                  acknowledged: 7,
                };
                break;
              case 'risk_analysis':
                acc[section] = {
                  current_score: 35,
                  avg_period: 38,
                  peak: 52,
                  main_factors: ['Alertas recentes', 'Incidente aberto'],
                };
                break;
              case 'recommendations':
                acc[section] = [
                  'Verificar camera offline no Bloco B',
                  'Revisar regras de acesso para visitantes',
                  'Aumentar monitoramento no horario 18h-20h',
                ];
                break;
            }
            return acc;
          }, {} as Record<string, unknown>),
        };

        return { content: [{ type: 'text', text: JSON.stringify(report) }] };
      }

      case 'analytics_get_daily_summary': {
        const date = (params.date as string) || new Date().toISOString().split('T')[0];
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              date,
              summary: {
                status: 'normal',
                risk_score: 35,
                access: { total: 487, denied: 12 },
                alerts: { total: 8, critical: 0 },
                incidents: { total: 1, resolved: 0 },
                cameras: { online: 23, total: 24 },
              },
              highlights: [
                'Pico de acesso as 18h30 (42 acessos)',
                '2 alertas de atividade suspeita no periodo noturno',
                'Camera CAM-B04 offline por 2h (manutencao)',
              ],
              recommendations: [
                'Verificar padroes de acesso noturno',
                'Programar manutencao preventiva cameras Bloco B',
              ],
            }),
          }],
        };
      }

      case 'analytics_create_report_config': {
        const config: ReportConfig = {
          id: params.id as string,
          name: params.name as string,
          type: params.type as ReportType,
          sections: params.sections as string[],
          schedule: params.schedule as string,
          recipients: params.recipients as string[],
          format: (params.format as ReportFormat) || 'pdf',
        };
        reportConfigs.set(config.id, config);

        // Agendar
        if (config.schedule) {
          scheduledReports.set(config.id, {
            config,
            nextRun: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          });
        }

        return { content: [{ type: 'text', text: JSON.stringify({ success: true, config }) }] };
      }

      case 'analytics_list_scheduled_reports': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              scheduled_reports: Array.from(scheduledReports.values()),
            }),
          }],
        };
      }

      // === Access Analytics ===
      case 'analytics_access_summary': {
        const periodHours = (params.period_hours as number) || 24;
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              period_hours: periodHours,
              total: 487,
              granted: 475,
              denied: 12,
              by_hour: generateTimeSeriesData(periodHours, 20, 10),
              by_type: { resident: 320, visitor: 95, employee: 60, service: 12 },
              by_access_point: {
                'Entrada Principal': 245,
                'Garagem A': 120,
                'Garagem B': 85,
                'Portaria Social': 37,
              },
            }),
          }],
        };
      }

      case 'analytics_access_patterns': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              patterns: {
                typical_entry_time: '07:30',
                typical_exit_time: '18:45',
                most_used_access_point: 'Entrada Principal',
                access_frequency: 'daily',
                weekend_activity: 'low',
                anomalies_detected: 0,
              },
            }),
          }],
        };
      }

      case 'analytics_peak_hours': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              peak_hours: [
                { hour: 7, avg_access: 35, label: 'morning_peak' },
                { hour: 8, avg_access: 42, label: 'morning_peak' },
                { hour: 12, avg_access: 28, label: 'lunch' },
                { hour: 18, avg_access: 45, label: 'evening_peak' },
                { hour: 19, avg_access: 38, label: 'evening_peak' },
              ],
              lowest_hours: [
                { hour: 3, avg_access: 1 },
                { hour: 4, avg_access: 1 },
              ],
              recommendation: 'Reforcar monitoramento entre 18h e 19h',
            }),
          }],
        };
      }

      // === Incident Analytics ===
      case 'analytics_incident_summary': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              period_days: params.period_days || 30,
              total: 12,
              by_severity: { low: 5, medium: 4, high: 2, critical: 1 },
              by_type: { suspicious_activity: 5, unauthorized_access: 3, equipment_failure: 2, emergency: 2 },
              by_status: { resolved: 11, pending: 1 },
              avg_resolution_time: '2h 15min',
              escalation_rate: 16.7,
            }),
          }],
        };
      }

      case 'analytics_response_times': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              overall: {
                avg_acknowledgment: 45,
                avg_resolution: 8100, // 2h 15min em segundos
                p95_acknowledgment: 120,
                p95_resolution: 14400,
              },
              by_severity: {
                critical: { avg_ack: 15, avg_resolution: 1800 },
                high: { avg_ack: 30, avg_resolution: 3600 },
                medium: { avg_ack: 60, avg_resolution: 7200 },
                low: { avg_ack: 120, avg_resolution: 14400 },
              },
              trend: 'improving',
              sla_compliance: 94.2,
            }),
          }],
        };
      }

      case 'analytics_incident_hotspots': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              hotspots: [
                { location: 'Garagem B', incidents: 4, severity_avg: 0.5 },
                { location: 'Entrada Social', incidents: 3, severity_avg: 0.4 },
                { location: 'Bloco C', incidents: 2, severity_avg: 0.6 },
              ],
              recommendations: [
                'Aumentar iluminacao na Garagem B',
                'Considerar camera adicional na Entrada Social',
              ],
            }),
          }],
        };
      }

      // === Risk Analytics ===
      case 'analytics_risk_evolution': {
        const periodDays = (params.period_days as number) || 7;
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              evolution: generateTimeSeriesData(periodDays * 24, 35, 15),
              avg: 38,
              max: 72,
              min: 22,
              current: 35,
              trend: 'stable',
            }),
          }],
        };
      }

      case 'analytics_risk_factors': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              factors: [
                { name: 'Alertas ativos', contribution: 15, current: 2 },
                { name: 'Incidentes abertos', contribution: 10, current: 1 },
                { name: 'Cameras offline', contribution: 5, current: 1 },
                { name: 'Horario', contribution: 5, current: 'comercial' },
              ],
              base_score: 20,
              total_score: 35,
            }),
          }],
        };
      }

      case 'analytics_vulnerability_windows': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              windows: [
                { start: '02:00', end: '05:00', avg_score: 45, reason: 'Baixa atividade de monitoramento' },
                { start: '12:00', end: '13:00', avg_score: 42, reason: 'Troca de turno' },
              ],
              recommendations: [
                'Programar rondas adicionais entre 02h e 05h',
                'Revisar procedimento de troca de turno',
              ],
            }),
          }],
        };
      }

      // === Export ===
      case 'analytics_export_data': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              export_id: generateId('EXP'),
              data_type: params.data_type,
              format: params.format || 'json',
              records: 1000,
              file_url: `/exports/${generateId('file')}.${params.format || 'json'}`,
              expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
            }),
          }],
        };
      }

      // === Dashboard ===
      case 'analytics_dashboard_data': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              timestamp: new Date().toISOString(),
              metrics: {
                access_24h: { granted: 475, denied: 12 },
                alerts_24h: { total: 8, critical: 0 },
                incidents_open: 1,
                cameras: { online: 23, total: 24 },
                risk_score: 35,
              },
              trends: {
                access: 'up',
                alerts: 'stable',
                risk: 'down',
              },
              charts: {
                access_hourly: generateTimeSeriesData(24, 20, 10),
                risk_daily: generateTimeSeriesData(7 * 24, 35, 10),
              },
              alerts: [
                { id: 'ALT001', type: 'person_detected', severity: 'medium', time: '10min ago' },
                { id: 'ALT002', type: 'vehicle', severity: 'low', time: '25min ago' },
              ],
              recommendations: [
                'Verificar camera CAM-B04',
                'Revisar acesso visitantes Bloco C',
              ],
            }),
          }],
        };
      }

      default:
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({ error: `Ferramenta desconhecida: ${name}` }),
          }],
        };
    }
  } catch (error) {
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({ error: `Erro ao executar ${name}: ${(error as Error).message}` }),
      }],
    };
  }
});

// === Main ===

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP Guardian Analytics iniciado');
}

main().catch(console.error);
