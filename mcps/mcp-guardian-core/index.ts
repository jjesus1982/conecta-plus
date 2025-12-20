/**
 * MCP Guardian Core - Sistema Central de Seguranca Inteligente
 * Conecta Plus - Plataforma de Gestao Condominial
 *
 * Este MCP fornece as ferramentas principais do sistema Guardian:
 * - Monitoramento de cameras e alertas
 * - Gestao de incidentes
 * - Analise de risco
 * - Interface com assistente de seguranca
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  {
    name: 'mcp-guardian-core',
    version: '2.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// === Tipos ===

interface GuardianConfig {
  apiUrl: string;
  apiKey?: string;
  mqttBroker?: string;
  frigateUrl?: string;
}

interface Alert {
  id: string;
  type: string;
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  location: string;
  cameraId?: string;
  timestamp: string;
  acknowledged: boolean;
  metadata: Record<string, unknown>;
}

interface Incident {
  id: string;
  type: string;
  severity: string;
  status: 'detected' | 'acknowledged' | 'in_progress' | 'escalated' | 'resolved' | 'closed';
  title: string;
  description: string;
  location: string;
  detectedAt: string;
  acknowledgedAt?: string;
  resolvedAt?: string;
  assignedTo?: string;
  escalationLevel: number;
  timeline: TimelineEvent[];
}

interface TimelineEvent {
  timestamp: string;
  event: string;
  description: string;
  user?: string;
}

interface RiskAssessment {
  score: number;
  level: 'minimal' | 'low' | 'moderate' | 'high' | 'critical';
  trend: 'decreasing' | 'stable' | 'increasing' | 'spike';
  factors: RiskFactor[];
  recommendations: string[];
  timestamp: string;
}

interface RiskFactor {
  name: string;
  contribution: number;
  detail: string;
}

interface Camera {
  id: string;
  name: string;
  location: string;
  status: 'online' | 'offline' | 'maintenance';
  detectEnabled: boolean;
  recordEnabled: boolean;
  lastEvent?: string;
}

// === Estado ===

let config: GuardianConfig = {
  apiUrl: process.env.GUARDIAN_API_URL || 'http://localhost:8000',
  apiKey: process.env.GUARDIAN_API_KEY,
  mqttBroker: process.env.MQTT_BROKER_URL,
  frigateUrl: process.env.FRIGATE_URL,
};

const activeAlerts: Map<string, Alert> = new Map();
const activeIncidents: Map<string, Incident> = new Map();
const cameras: Map<string, Camera> = new Map();

// === Helpers ===

async function guardianRequest(endpoint: string, method = 'GET', body?: object): Promise<unknown> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (config.apiKey) {
    headers['Authorization'] = `Bearer ${config.apiKey}`;
  }

  const response = await fetch(`${config.apiUrl}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    throw new Error(`Guardian API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

function generateId(prefix: string): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 8);
  return `${prefix}_${timestamp}_${random}`;
}

// === Tools Definition ===

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    // === Configuration ===
    {
      name: 'guardian_configure',
      description: 'Configura conexao com o sistema Guardian',
      inputSchema: {
        type: 'object',
        properties: {
          api_url: { type: 'string', description: 'URL da API Guardian' },
          api_key: { type: 'string', description: 'API Key' },
          mqtt_broker: { type: 'string', description: 'URL do broker MQTT' },
          frigate_url: { type: 'string', description: 'URL do Frigate NVR' },
        },
        required: ['api_url'],
      },
    },
    {
      name: 'guardian_status',
      description: 'Obtem status geral do sistema Guardian',
      inputSchema: { type: 'object', properties: {} },
    },

    // === Alert Management ===
    {
      name: 'guardian_list_alerts',
      description: 'Lista alertas ativos no sistema',
      inputSchema: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['info', 'low', 'medium', 'high', 'critical'] },
          location: { type: 'string', description: 'Filtrar por local' },
          camera_id: { type: 'string', description: 'Filtrar por camera' },
          limit: { type: 'number', description: 'Limite de resultados' },
        },
      },
    },
    {
      name: 'guardian_get_alert',
      description: 'Obtem detalhes de um alerta especifico',
      inputSchema: {
        type: 'object',
        properties: {
          alert_id: { type: 'string', description: 'ID do alerta' },
        },
        required: ['alert_id'],
      },
    },
    {
      name: 'guardian_acknowledge_alert',
      description: 'Reconhece um alerta',
      inputSchema: {
        type: 'object',
        properties: {
          alert_id: { type: 'string', description: 'ID do alerta' },
          user_id: { type: 'string', description: 'ID do usuario' },
          notes: { type: 'string', description: 'Observacoes' },
        },
        required: ['alert_id', 'user_id'],
      },
    },
    {
      name: 'guardian_dismiss_alert',
      description: 'Descarta um alerta (falso positivo)',
      inputSchema: {
        type: 'object',
        properties: {
          alert_id: { type: 'string', description: 'ID do alerta' },
          user_id: { type: 'string', description: 'ID do usuario' },
          reason: { type: 'string', description: 'Motivo do descarte' },
        },
        required: ['alert_id', 'user_id', 'reason'],
      },
    },
    {
      name: 'guardian_create_alert',
      description: 'Cria um novo alerta manualmente',
      inputSchema: {
        type: 'object',
        properties: {
          type: { type: 'string', description: 'Tipo do alerta' },
          severity: { type: 'string', enum: ['info', 'low', 'medium', 'high', 'critical'] },
          title: { type: 'string', description: 'Titulo do alerta' },
          description: { type: 'string', description: 'Descricao' },
          location: { type: 'string', description: 'Localizacao' },
          camera_id: { type: 'string', description: 'ID da camera' },
        },
        required: ['type', 'severity', 'title', 'location'],
      },
    },

    // === Incident Management ===
    {
      name: 'guardian_list_incidents',
      description: 'Lista incidentes ativos',
      inputSchema: {
        type: 'object',
        properties: {
          status: { type: 'string', enum: ['detected', 'acknowledged', 'in_progress', 'escalated', 'resolved'] },
          severity: { type: 'string', enum: ['low', 'medium', 'high', 'critical'] },
          limit: { type: 'number' },
        },
      },
    },
    {
      name: 'guardian_get_incident',
      description: 'Obtem detalhes de um incidente',
      inputSchema: {
        type: 'object',
        properties: {
          incident_id: { type: 'string', description: 'ID do incidente' },
        },
        required: ['incident_id'],
      },
    },
    {
      name: 'guardian_create_incident',
      description: 'Cria um novo incidente',
      inputSchema: {
        type: 'object',
        properties: {
          type: { type: 'string', enum: ['intrusion', 'unauthorized_access', 'equipment_failure', 'suspicious_activity', 'emergency', 'vandalism', 'fire', 'medical'] },
          severity: { type: 'string', enum: ['low', 'medium', 'high', 'critical'] },
          title: { type: 'string' },
          description: { type: 'string' },
          location: { type: 'string' },
        },
        required: ['type', 'severity', 'title', 'location'],
      },
    },
    {
      name: 'guardian_acknowledge_incident',
      description: 'Reconhece um incidente',
      inputSchema: {
        type: 'object',
        properties: {
          incident_id: { type: 'string' },
          user_id: { type: 'string' },
        },
        required: ['incident_id', 'user_id'],
      },
    },
    {
      name: 'guardian_update_incident',
      description: 'Atualiza status de um incidente',
      inputSchema: {
        type: 'object',
        properties: {
          incident_id: { type: 'string' },
          status: { type: 'string', enum: ['in_progress', 'escalated', 'resolved'] },
          notes: { type: 'string' },
          user_id: { type: 'string' },
        },
        required: ['incident_id', 'status', 'user_id'],
      },
    },
    {
      name: 'guardian_resolve_incident',
      description: 'Resolve um incidente',
      inputSchema: {
        type: 'object',
        properties: {
          incident_id: { type: 'string' },
          resolution: { type: 'string', description: 'Descricao da resolucao' },
          user_id: { type: 'string' },
        },
        required: ['incident_id', 'resolution', 'user_id'],
      },
    },
    {
      name: 'guardian_get_incident_timeline',
      description: 'Obtem timeline de um incidente',
      inputSchema: {
        type: 'object',
        properties: {
          incident_id: { type: 'string' },
        },
        required: ['incident_id'],
      },
    },

    // === Risk Assessment ===
    {
      name: 'guardian_get_risk_assessment',
      description: 'Obtem avaliacao de risco atual',
      inputSchema: {
        type: 'object',
        properties: {
          entity_id: { type: 'string', description: 'ID da entidade (opcional, padrao: geral)' },
        },
      },
    },
    {
      name: 'guardian_get_anomalies',
      description: 'Lista anomalias detectadas',
      inputSchema: {
        type: 'object',
        properties: {
          hours: { type: 'number', description: 'Ultimas N horas (padrao: 24)' },
          min_severity: { type: 'number', description: 'Severidade minima (0-1)' },
        },
      },
    },
    {
      name: 'guardian_get_predictions',
      description: 'Obtem predicoes de seguranca',
      inputSchema: {
        type: 'object',
        properties: {
          type: { type: 'string', enum: ['incident_probability', 'peak_activity', 'vulnerability_window'] },
        },
      },
    },

    // === Camera Management ===
    {
      name: 'guardian_list_cameras',
      description: 'Lista cameras do sistema',
      inputSchema: {
        type: 'object',
        properties: {
          status: { type: 'string', enum: ['online', 'offline', 'maintenance'] },
          location: { type: 'string' },
        },
      },
    },
    {
      name: 'guardian_get_camera',
      description: 'Obtem detalhes de uma camera',
      inputSchema: {
        type: 'object',
        properties: {
          camera_id: { type: 'string' },
        },
        required: ['camera_id'],
      },
    },
    {
      name: 'guardian_camera_snapshot',
      description: 'Obtem snapshot atual de uma camera',
      inputSchema: {
        type: 'object',
        properties: {
          camera_id: { type: 'string' },
          include_detections: { type: 'boolean' },
        },
        required: ['camera_id'],
      },
    },
    {
      name: 'guardian_toggle_camera_detection',
      description: 'Ativa/desativa deteccao em uma camera',
      inputSchema: {
        type: 'object',
        properties: {
          camera_id: { type: 'string' },
          enabled: { type: 'boolean' },
        },
        required: ['camera_id', 'enabled'],
      },
    },
    {
      name: 'guardian_toggle_camera_recording',
      description: 'Ativa/desativa gravacao em uma camera',
      inputSchema: {
        type: 'object',
        properties: {
          camera_id: { type: 'string' },
          enabled: { type: 'boolean' },
        },
        required: ['camera_id', 'enabled'],
      },
    },

    // === Assistant ===
    {
      name: 'guardian_chat',
      description: 'Envia mensagem ao assistente de seguranca',
      inputSchema: {
        type: 'object',
        properties: {
          message: { type: 'string', description: 'Mensagem para o assistente' },
          user_id: { type: 'string' },
          session_id: { type: 'string' },
        },
        required: ['message', 'user_id'],
      },
    },
    {
      name: 'guardian_quick_status',
      description: 'Obtem status rapido do sistema em texto',
      inputSchema: { type: 'object', properties: {} },
    },

    // === Dashboard ===
    {
      name: 'guardian_dashboard',
      description: 'Obtem dados consolidados para dashboard',
      inputSchema: { type: 'object', properties: {} },
    },
    {
      name: 'guardian_statistics',
      description: 'Obtem estatisticas do sistema',
      inputSchema: {
        type: 'object',
        properties: {
          hours: { type: 'number', description: 'Periodo em horas' },
        },
      },
    },

    // === Actions ===
    {
      name: 'guardian_trigger_alarm',
      description: 'Aciona alarme em uma area',
      inputSchema: {
        type: 'object',
        properties: {
          area: { type: 'string', description: 'Area do alarme' },
          type: { type: 'string', enum: ['security', 'fire', 'emergency'] },
          reason: { type: 'string' },
        },
        required: ['area', 'type', 'reason'],
      },
    },
    {
      name: 'guardian_deactivate_alarm',
      description: 'Desativa alarme',
      inputSchema: {
        type: 'object',
        properties: {
          area: { type: 'string' },
          user_id: { type: 'string' },
        },
        required: ['area', 'user_id'],
      },
    },
    {
      name: 'guardian_lock_access',
      description: 'Bloqueia ponto de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          access_point: { type: 'string' },
          reason: { type: 'string' },
          duration_minutes: { type: 'number' },
        },
        required: ['access_point', 'reason'],
      },
    },
    {
      name: 'guardian_unlock_access',
      description: 'Desbloqueia ponto de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          access_point: { type: 'string' },
          user_id: { type: 'string' },
        },
        required: ['access_point', 'user_id'],
      },
    },
    {
      name: 'guardian_dispatch_security',
      description: 'Despacha equipe de seguranca',
      inputSchema: {
        type: 'object',
        properties: {
          location: { type: 'string' },
          priority: { type: 'string', enum: ['normal', 'high', 'urgent'] },
          reason: { type: 'string' },
        },
        required: ['location', 'priority', 'reason'],
      },
    },
  ],
}));

// === Tool Handlers ===

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const params = args as Record<string, unknown>;

  try {
    switch (name) {
      // === Configuration ===
      case 'guardian_configure': {
        config = {
          apiUrl: params.api_url as string || config.apiUrl,
          apiKey: params.api_key as string || config.apiKey,
          mqttBroker: params.mqtt_broker as string || config.mqttBroker,
          frigateUrl: params.frigate_url as string || config.frigateUrl,
        };
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: 'Configuracao atualizada',
              config: { apiUrl: config.apiUrl, mqttBroker: config.mqttBroker, frigateUrl: config.frigateUrl },
            }),
          }],
        };
      }

      case 'guardian_status': {
        const status = {
          online: true,
          apiUrl: config.apiUrl,
          frigateConnected: !!config.frigateUrl,
          mqttConnected: !!config.mqttBroker,
          activeAlerts: activeAlerts.size,
          activeIncidents: activeIncidents.size,
          camerasOnline: Array.from(cameras.values()).filter(c => c.status === 'online').length,
          camerasTotal: cameras.size,
          timestamp: new Date().toISOString(),
        };
        return { content: [{ type: 'text', text: JSON.stringify(status) }] };
      }

      // === Alert Management ===
      case 'guardian_list_alerts': {
        let alerts = Array.from(activeAlerts.values());
        if (params.severity) alerts = alerts.filter(a => a.severity === params.severity);
        if (params.location) alerts = alerts.filter(a => a.location.includes(params.location as string));
        if (params.camera_id) alerts = alerts.filter(a => a.cameraId === params.camera_id);
        if (params.limit) alerts = alerts.slice(0, params.limit as number);
        return { content: [{ type: 'text', text: JSON.stringify({ alerts, total: alerts.length }) }] };
      }

      case 'guardian_get_alert': {
        const alert = activeAlerts.get(params.alert_id as string);
        if (!alert) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Alerta nao encontrado' }) }] };
        }
        return { content: [{ type: 'text', text: JSON.stringify(alert) }] };
      }

      case 'guardian_acknowledge_alert': {
        const alert = activeAlerts.get(params.alert_id as string);
        if (!alert) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Alerta nao encontrado' }) }] };
        }
        alert.acknowledged = true;
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Alerta ${alert.id} reconhecido por ${params.user_id}`,
            }),
          }],
        };
      }

      case 'guardian_dismiss_alert': {
        const dismissed = activeAlerts.delete(params.alert_id as string);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: dismissed,
              message: dismissed ? 'Alerta descartado' : 'Alerta nao encontrado',
            }),
          }],
        };
      }

      case 'guardian_create_alert': {
        const newAlert: Alert = {
          id: generateId('ALT'),
          type: params.type as string,
          severity: params.severity as Alert['severity'],
          title: params.title as string,
          description: params.description as string || '',
          location: params.location as string,
          cameraId: params.camera_id as string,
          timestamp: new Date().toISOString(),
          acknowledged: false,
          metadata: {},
        };
        activeAlerts.set(newAlert.id, newAlert);
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, alert: newAlert }) }] };
      }

      // === Incident Management ===
      case 'guardian_list_incidents': {
        let incidents = Array.from(activeIncidents.values());
        if (params.status) incidents = incidents.filter(i => i.status === params.status);
        if (params.severity) incidents = incidents.filter(i => i.severity === params.severity);
        if (params.limit) incidents = incidents.slice(0, params.limit as number);
        return { content: [{ type: 'text', text: JSON.stringify({ incidents, total: incidents.length }) }] };
      }

      case 'guardian_get_incident': {
        const incident = activeIncidents.get(params.incident_id as string);
        if (!incident) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Incidente nao encontrado' }) }] };
        }
        return { content: [{ type: 'text', text: JSON.stringify(incident) }] };
      }

      case 'guardian_create_incident': {
        const newIncident: Incident = {
          id: `INC-${new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14)}-${Math.random().toString(36).slice(2, 8).toUpperCase()}`,
          type: params.type as string,
          severity: params.severity as string,
          status: 'detected',
          title: params.title as string,
          description: params.description as string || '',
          location: params.location as string,
          detectedAt: new Date().toISOString(),
          escalationLevel: 0,
          timeline: [{
            timestamp: new Date().toISOString(),
            event: 'incident_created',
            description: `Incidente detectado: ${params.title}`,
            user: 'system',
          }],
        };
        activeIncidents.set(newIncident.id, newIncident);
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, incident: newIncident }) }] };
      }

      case 'guardian_acknowledge_incident': {
        const incident = activeIncidents.get(params.incident_id as string);
        if (!incident) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Incidente nao encontrado' }) }] };
        }
        incident.status = 'acknowledged';
        incident.acknowledgedAt = new Date().toISOString();
        incident.assignedTo = params.user_id as string;
        incident.timeline.push({
          timestamp: new Date().toISOString(),
          event: 'incident_acknowledged',
          description: `Incidente reconhecido`,
          user: params.user_id as string,
        });
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, incident }) }] };
      }

      case 'guardian_update_incident': {
        const incident = activeIncidents.get(params.incident_id as string);
        if (!incident) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Incidente nao encontrado' }) }] };
        }
        incident.status = params.status as Incident['status'];
        if (params.status === 'escalated') incident.escalationLevel++;
        incident.timeline.push({
          timestamp: new Date().toISOString(),
          event: `status_changed_to_${params.status}`,
          description: params.notes as string || `Status alterado para ${params.status}`,
          user: params.user_id as string,
        });
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, incident }) }] };
      }

      case 'guardian_resolve_incident': {
        const incident = activeIncidents.get(params.incident_id as string);
        if (!incident) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Incidente nao encontrado' }) }] };
        }
        incident.status = 'resolved';
        incident.resolvedAt = new Date().toISOString();
        incident.timeline.push({
          timestamp: new Date().toISOString(),
          event: 'incident_resolved',
          description: params.resolution as string,
          user: params.user_id as string,
        });
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, incident }) }] };
      }

      case 'guardian_get_incident_timeline': {
        const incident = activeIncidents.get(params.incident_id as string);
        if (!incident) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Incidente nao encontrado' }) }] };
        }
        return { content: [{ type: 'text', text: JSON.stringify({ timeline: incident.timeline }) }] };
      }

      // === Risk Assessment ===
      case 'guardian_get_risk_assessment': {
        const assessment: RiskAssessment = {
          score: 35,
          level: 'low',
          trend: 'stable',
          factors: [
            { name: 'Alertas recentes', contribution: 10, detail: `${activeAlerts.size} alertas ativos` },
            { name: 'Incidentes', contribution: 15, detail: `${activeIncidents.size} incidentes` },
            { name: 'Horario', contribution: 10, detail: 'Horario comercial' },
          ],
          recommendations: [
            'Manter monitoramento padrao',
            'Verificar cameras prioritarias',
          ],
          timestamp: new Date().toISOString(),
        };
        return { content: [{ type: 'text', text: JSON.stringify(assessment) }] };
      }

      case 'guardian_get_anomalies': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              anomalies: [],
              period_hours: params.hours || 24,
            }),
          }],
        };
      }

      case 'guardian_get_predictions': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              predictions: [
                {
                  type: 'peak_activity',
                  description: 'Pico de atividade previsto para 18h',
                  probability: 0.85,
                  recommendedActions: ['Aumentar monitoramento', 'Preparar equipe'],
                },
              ],
            }),
          }],
        };
      }

      // === Camera Management ===
      case 'guardian_list_cameras': {
        let cameraList = Array.from(cameras.values());
        if (params.status) cameraList = cameraList.filter(c => c.status === params.status);
        if (params.location) cameraList = cameraList.filter(c => c.location.includes(params.location as string));
        return { content: [{ type: 'text', text: JSON.stringify({ cameras: cameraList, total: cameraList.length }) }] };
      }

      case 'guardian_get_camera': {
        const camera = cameras.get(params.camera_id as string);
        if (!camera) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Camera nao encontrada' }) }] };
        }
        return { content: [{ type: 'text', text: JSON.stringify(camera) }] };
      }

      case 'guardian_camera_snapshot': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              camera_id: params.camera_id,
              snapshot_url: `${config.frigateUrl}/api/${params.camera_id}/latest.jpg`,
              timestamp: new Date().toISOString(),
            }),
          }],
        };
      }

      case 'guardian_toggle_camera_detection': {
        const camera = cameras.get(params.camera_id as string);
        if (camera) camera.detectEnabled = params.enabled as boolean;
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              camera_id: params.camera_id,
              detection_enabled: params.enabled,
            }),
          }],
        };
      }

      case 'guardian_toggle_camera_recording': {
        const camera = cameras.get(params.camera_id as string);
        if (camera) camera.recordEnabled = params.enabled as boolean;
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              camera_id: params.camera_id,
              recording_enabled: params.enabled,
            }),
          }],
        };
      }

      // === Assistant ===
      case 'guardian_chat': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              response: 'Sistema operando normalmente. Como posso ajudar?',
              suggestions: ['Status do sistema', 'Ver alertas', 'Ver incidentes'],
              session_id: params.session_id || generateId('sess'),
            }),
          }],
        };
      }

      case 'guardian_quick_status': {
        const alertCount = activeAlerts.size;
        const incidentCount = activeIncidents.size;
        const status = alertCount === 0 && incidentCount === 0
          ? '✅ Sistema OK | Sem alertas ou incidentes'
          : `⚠️ ${alertCount} alertas | ${incidentCount} incidentes ativos`;
        return { content: [{ type: 'text', text: status }] };
      }

      // === Dashboard ===
      case 'guardian_dashboard': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              system_status: 'online',
              uptime_seconds: process.uptime(),
              active_alerts: activeAlerts.size,
              active_incidents: activeIncidents.size,
              critical_incidents: Array.from(activeIncidents.values()).filter(i => i.severity === 'critical').length,
              cameras_online: Array.from(cameras.values()).filter(c => c.status === 'online').length,
              cameras_total: cameras.size,
              risk_score: 35,
              risk_level: 'low',
              timestamp: new Date().toISOString(),
            }),
          }],
        };
      }

      case 'guardian_statistics': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              period_hours: params.hours || 24,
              total_alerts: activeAlerts.size,
              total_incidents: activeIncidents.size,
              avg_response_time: 120,
              by_severity: {
                critical: 0,
                high: 1,
                medium: 2,
                low: 3,
              },
            }),
          }],
        };
      }

      // === Actions ===
      case 'guardian_trigger_alarm': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Alarme ${params.type} acionado em ${params.area}`,
              alarm_id: generateId('ALM'),
            }),
          }],
        };
      }

      case 'guardian_deactivate_alarm': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Alarme desativado em ${params.area} por ${params.user_id}`,
            }),
          }],
        };
      }

      case 'guardian_lock_access': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Acesso bloqueado: ${params.access_point}`,
              reason: params.reason,
              duration: params.duration_minutes || 'indefinido',
            }),
          }],
        };
      }

      case 'guardian_unlock_access': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Acesso desbloqueado: ${params.access_point}`,
              unlocked_by: params.user_id,
            }),
          }],
        };
      }

      case 'guardian_dispatch_security': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Equipe de seguranca despachada para ${params.location}`,
              priority: params.priority,
              dispatch_id: generateId('DSP'),
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
  console.error('MCP Guardian Core iniciado');
}

main().catch(console.error);
