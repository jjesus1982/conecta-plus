/**
 * MCP Guardian Access - Controle de Acesso Unificado
 * Conecta Plus - Plataforma de Gestao Condominial
 *
 * Integra multiplos fabricantes de controladoras de acesso:
 * - Control iD (iDAccess, iDBox, iDFlex, iDFace)
 * - Intelbras (SS 3530, SS 5530, etc)
 * - Hikvision (DS-K series)
 * - Garen, Nice, PPA, JFL
 *
 * Funcionalidades:
 * - Validacao biometrica (face, digital)
 * - Leitura de placas (ANPR/LPR)
 * - Controle de catracas e cancelas
 * - Gestao de credenciais
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  {
    name: 'mcp-guardian-access',
    version: '2.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// === Tipos ===

type ControllerType = 'controlid' | 'intelbras' | 'hikvision' | 'garen' | 'nice' | 'ppa' | 'jfl' | 'generic';
type AccessPointType = 'pedestrian' | 'vehicle' | 'turnstile' | 'barrier' | 'door' | 'gate';
type CredentialType = 'face' | 'fingerprint' | 'card' | 'qrcode' | 'plate' | 'pin' | 'bluetooth';
type AccessDirection = 'entry' | 'exit' | 'both';
type AccessResult = 'granted' | 'denied' | 'pending' | 'timeout' | 'error';
type PersonType = 'resident' | 'visitor' | 'employee' | 'service' | 'delivery' | 'vip' | 'blocked';

interface Controller {
  id: string;
  name: string;
  type: ControllerType;
  ip: string;
  port: number;
  credentials: Record<string, string>;
  accessPoints: string[];
  status: 'online' | 'offline' | 'error';
  lastSeen?: string;
  capabilities: CredentialType[];
}

interface AccessPoint {
  id: string;
  name: string;
  type: AccessPointType;
  controllerId: string;
  direction: AccessDirection;
  location: string;
  status: 'active' | 'locked' | 'unlocked' | 'maintenance';
  antiPassback: boolean;
}

interface Person {
  id: string;
  name: string;
  type: PersonType;
  document?: string;
  unit?: string;
  photo?: string;
  credentials: PersonCredential[];
  accessRules: AccessRule[];
  validFrom?: string;
  validUntil?: string;
  blocked: boolean;
  blockReason?: string;
}

interface PersonCredential {
  type: CredentialType;
  value: string;
  enabled: boolean;
  addedAt: string;
  lastUsed?: string;
}

interface AccessRule {
  accessPointIds: string[];
  schedule?: string;
  daysOfWeek?: number[];
  timeRanges?: { start: string; end: string }[];
}

interface AccessLog {
  id: string;
  timestamp: string;
  accessPointId: string;
  personId?: string;
  personName?: string;
  credentialType: CredentialType;
  direction: AccessDirection;
  result: AccessResult;
  reason?: string;
  photo?: string;
  plateNumber?: string;
  confidence?: number;
}

interface Vehicle {
  id: string;
  plate: string;
  model?: string;
  color?: string;
  ownerId: string;
  ownerName: string;
  type: 'car' | 'motorcycle' | 'truck' | 'van';
  authorized: boolean;
}

// === Estado ===

const controllers: Map<string, Controller> = new Map();
const accessPoints: Map<string, AccessPoint> = new Map();
const persons: Map<string, Person> = new Map();
const vehicles: Map<string, Vehicle> = new Map();
const accessLogs: AccessLog[] = [];

// === Helpers ===

function generateId(prefix: string): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 8);
  return `${prefix}_${timestamp}_${random}`;
}

async function sendToController(controller: Controller, command: string, data: unknown): Promise<unknown> {
  // Em producao, implementaria comunicacao real com cada tipo de controladora
  // Aqui simulamos a resposta
  return { success: true, command, data };
}

function checkPersonAccess(person: Person, accessPointId: string): { allowed: boolean; reason: string } {
  if (person.blocked) {
    return { allowed: false, reason: person.blockReason || 'Pessoa bloqueada' };
  }

  if (person.validFrom && new Date(person.validFrom) > new Date()) {
    return { allowed: false, reason: 'Acesso ainda nao iniciado' };
  }

  if (person.validUntil && new Date(person.validUntil) < new Date()) {
    return { allowed: false, reason: 'Acesso expirado' };
  }

  const hasRule = person.accessRules.some(rule =>
    rule.accessPointIds.includes(accessPointId) || rule.accessPointIds.includes('*')
  );

  if (!hasRule) {
    return { allowed: false, reason: 'Sem permissao para este acesso' };
  }

  return { allowed: true, reason: 'Acesso autorizado' };
}

// === Tools Definition ===

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    // === Controller Management ===
    {
      name: 'access_add_controller',
      description: 'Adiciona uma controladora de acesso ao sistema',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          name: { type: 'string' },
          type: { type: 'string', enum: ['controlid', 'intelbras', 'hikvision', 'garen', 'nice', 'ppa', 'jfl', 'generic'] },
          ip: { type: 'string' },
          port: { type: 'number' },
          username: { type: 'string' },
          password: { type: 'string' },
          capabilities: { type: 'array', items: { type: 'string' } },
        },
        required: ['id', 'name', 'type', 'ip'],
      },
    },
    {
      name: 'access_list_controllers',
      description: 'Lista controladoras cadastradas',
      inputSchema: {
        type: 'object',
        properties: {
          type: { type: 'string', description: 'Filtrar por tipo' },
          status: { type: 'string', enum: ['online', 'offline', 'error'] },
        },
      },
    },
    {
      name: 'access_controller_status',
      description: 'Verifica status de uma controladora',
      inputSchema: {
        type: 'object',
        properties: {
          controller_id: { type: 'string' },
        },
        required: ['controller_id'],
      },
    },
    {
      name: 'access_sync_controller',
      description: 'Sincroniza dados com a controladora',
      inputSchema: {
        type: 'object',
        properties: {
          controller_id: { type: 'string' },
          sync_type: { type: 'string', enum: ['full', 'users', 'credentials', 'logs'] },
        },
        required: ['controller_id'],
      },
    },

    // === Access Point Management ===
    {
      name: 'access_add_point',
      description: 'Adiciona um ponto de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          name: { type: 'string' },
          type: { type: 'string', enum: ['pedestrian', 'vehicle', 'turnstile', 'barrier', 'door', 'gate'] },
          controller_id: { type: 'string' },
          direction: { type: 'string', enum: ['entry', 'exit', 'both'] },
          location: { type: 'string' },
          anti_passback: { type: 'boolean' },
        },
        required: ['id', 'name', 'type', 'controller_id', 'location'],
      },
    },
    {
      name: 'access_list_points',
      description: 'Lista pontos de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          type: { type: 'string' },
          status: { type: 'string', enum: ['active', 'locked', 'unlocked', 'maintenance'] },
          location: { type: 'string' },
        },
      },
    },
    {
      name: 'access_lock_point',
      description: 'Bloqueia um ponto de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          access_point_id: { type: 'string' },
          reason: { type: 'string' },
          duration_minutes: { type: 'number' },
        },
        required: ['access_point_id', 'reason'],
      },
    },
    {
      name: 'access_unlock_point',
      description: 'Desbloqueia um ponto de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          access_point_id: { type: 'string' },
          user_id: { type: 'string' },
        },
        required: ['access_point_id', 'user_id'],
      },
    },
    {
      name: 'access_open_point',
      description: 'Abre remotamente um ponto de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          access_point_id: { type: 'string' },
          duration_seconds: { type: 'number' },
          reason: { type: 'string' },
          user_id: { type: 'string' },
        },
        required: ['access_point_id', 'user_id'],
      },
    },

    // === Person Management ===
    {
      name: 'access_add_person',
      description: 'Cadastra uma pessoa no sistema de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          name: { type: 'string' },
          type: { type: 'string', enum: ['resident', 'visitor', 'employee', 'service', 'delivery', 'vip'] },
          document: { type: 'string' },
          unit: { type: 'string' },
          photo: { type: 'string', description: 'Base64 da foto' },
          valid_from: { type: 'string', description: 'Data inicio validade' },
          valid_until: { type: 'string', description: 'Data fim validade' },
          access_point_ids: { type: 'array', items: { type: 'string' } },
        },
        required: ['id', 'name', 'type'],
      },
    },
    {
      name: 'access_get_person',
      description: 'Obtem dados de uma pessoa',
      inputSchema: {
        type: 'object',
        properties: {
          person_id: { type: 'string' },
        },
        required: ['person_id'],
      },
    },
    {
      name: 'access_list_persons',
      description: 'Lista pessoas cadastradas',
      inputSchema: {
        type: 'object',
        properties: {
          type: { type: 'string' },
          unit: { type: 'string' },
          blocked: { type: 'boolean' },
          search: { type: 'string', description: 'Busca por nome ou documento' },
          limit: { type: 'number' },
        },
      },
    },
    {
      name: 'access_block_person',
      description: 'Bloqueia acesso de uma pessoa',
      inputSchema: {
        type: 'object',
        properties: {
          person_id: { type: 'string' },
          reason: { type: 'string' },
        },
        required: ['person_id', 'reason'],
      },
    },
    {
      name: 'access_unblock_person',
      description: 'Desbloqueia acesso de uma pessoa',
      inputSchema: {
        type: 'object',
        properties: {
          person_id: { type: 'string' },
        },
        required: ['person_id'],
      },
    },

    // === Credential Management ===
    {
      name: 'access_add_credential',
      description: 'Adiciona credencial a uma pessoa',
      inputSchema: {
        type: 'object',
        properties: {
          person_id: { type: 'string' },
          type: { type: 'string', enum: ['face', 'fingerprint', 'card', 'qrcode', 'plate', 'pin', 'bluetooth'] },
          value: { type: 'string', description: 'Valor da credencial (numero cartao, template biometrico, etc)' },
        },
        required: ['person_id', 'type', 'value'],
      },
    },
    {
      name: 'access_remove_credential',
      description: 'Remove credencial de uma pessoa',
      inputSchema: {
        type: 'object',
        properties: {
          person_id: { type: 'string' },
          type: { type: 'string' },
          value: { type: 'string' },
        },
        required: ['person_id', 'type'],
      },
    },
    {
      name: 'access_enroll_face',
      description: 'Cadastra biometria facial',
      inputSchema: {
        type: 'object',
        properties: {
          person_id: { type: 'string' },
          photo: { type: 'string', description: 'Foto em base64' },
          controller_ids: { type: 'array', items: { type: 'string' }, description: 'Controladoras para sincronizar' },
        },
        required: ['person_id', 'photo'],
      },
    },
    {
      name: 'access_enroll_fingerprint',
      description: 'Cadastra biometria digital',
      inputSchema: {
        type: 'object',
        properties: {
          person_id: { type: 'string' },
          finger_index: { type: 'number', description: 'Indice do dedo (1-10)' },
          template: { type: 'string', description: 'Template biometrico' },
          controller_ids: { type: 'array', items: { type: 'string' } },
        },
        required: ['person_id', 'template'],
      },
    },

    // === Vehicle Management ===
    {
      name: 'access_add_vehicle',
      description: 'Cadastra um veiculo',
      inputSchema: {
        type: 'object',
        properties: {
          plate: { type: 'string' },
          model: { type: 'string' },
          color: { type: 'string' },
          owner_id: { type: 'string' },
          type: { type: 'string', enum: ['car', 'motorcycle', 'truck', 'van'] },
        },
        required: ['plate', 'owner_id'],
      },
    },
    {
      name: 'access_list_vehicles',
      description: 'Lista veiculos cadastrados',
      inputSchema: {
        type: 'object',
        properties: {
          owner_id: { type: 'string' },
          plate: { type: 'string', description: 'Busca parcial por placa' },
          authorized: { type: 'boolean' },
        },
      },
    },
    {
      name: 'access_authorize_vehicle',
      description: 'Autoriza/desautoriza um veiculo',
      inputSchema: {
        type: 'object',
        properties: {
          plate: { type: 'string' },
          authorized: { type: 'boolean' },
        },
        required: ['plate', 'authorized'],
      },
    },

    // === Access Validation ===
    {
      name: 'access_validate',
      description: 'Valida uma solicitacao de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          access_point_id: { type: 'string' },
          credential_type: { type: 'string', enum: ['face', 'fingerprint', 'card', 'qrcode', 'plate', 'pin'] },
          credential_value: { type: 'string' },
          direction: { type: 'string', enum: ['entry', 'exit'] },
          photo: { type: 'string', description: 'Foto capturada (para face)' },
          confidence: { type: 'number', description: 'Confianca do reconhecimento' },
        },
        required: ['access_point_id', 'credential_type', 'credential_value'],
      },
    },
    {
      name: 'access_validate_plate',
      description: 'Valida acesso por placa de veiculo',
      inputSchema: {
        type: 'object',
        properties: {
          access_point_id: { type: 'string' },
          plate: { type: 'string' },
          confidence: { type: 'number' },
          direction: { type: 'string', enum: ['entry', 'exit'] },
        },
        required: ['access_point_id', 'plate'],
      },
    },

    // === Access Logs ===
    {
      name: 'access_get_logs',
      description: 'Obtem logs de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          access_point_id: { type: 'string' },
          person_id: { type: 'string' },
          result: { type: 'string', enum: ['granted', 'denied', 'pending', 'timeout', 'error'] },
          direction: { type: 'string', enum: ['entry', 'exit'] },
          from: { type: 'string', description: 'Data/hora inicial' },
          to: { type: 'string', description: 'Data/hora final' },
          limit: { type: 'number' },
        },
      },
    },
    {
      name: 'access_statistics',
      description: 'Obtem estatisticas de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          period_hours: { type: 'number' },
          access_point_id: { type: 'string' },
          group_by: { type: 'string', enum: ['hour', 'day', 'access_point', 'result'] },
        },
      },
    },

    // === Visitor Management ===
    {
      name: 'access_create_visitor',
      description: 'Cria acesso para visitante',
      inputSchema: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          document: { type: 'string' },
          photo: { type: 'string' },
          visiting_unit: { type: 'string' },
          authorized_by: { type: 'string' },
          valid_from: { type: 'string' },
          valid_until: { type: 'string' },
          access_point_ids: { type: 'array', items: { type: 'string' } },
        },
        required: ['name', 'visiting_unit', 'authorized_by'],
      },
    },
    {
      name: 'access_list_visitors',
      description: 'Lista visitantes ativos',
      inputSchema: {
        type: 'object',
        properties: {
          unit: { type: 'string' },
          status: { type: 'string', enum: ['waiting', 'inside', 'left'] },
        },
      },
    },
    {
      name: 'access_checkout_visitor',
      description: 'Registra saida de visitante',
      inputSchema: {
        type: 'object',
        properties: {
          visitor_id: { type: 'string' },
        },
        required: ['visitor_id'],
      },
    },

    // === Interlock / Emergency ===
    {
      name: 'access_emergency_unlock_all',
      description: 'Desbloqueia todos os pontos de acesso (emergencia)',
      inputSchema: {
        type: 'object',
        properties: {
          reason: { type: 'string' },
          user_id: { type: 'string' },
        },
        required: ['reason', 'user_id'],
      },
    },
    {
      name: 'access_emergency_lock_all',
      description: 'Bloqueia todos os pontos de acesso (lockdown)',
      inputSchema: {
        type: 'object',
        properties: {
          reason: { type: 'string' },
          user_id: { type: 'string' },
          except_emergency_exits: { type: 'boolean' },
        },
        required: ['reason', 'user_id'],
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
      // === Controller Management ===
      case 'access_add_controller': {
        const controller: Controller = {
          id: params.id as string,
          name: params.name as string,
          type: params.type as ControllerType,
          ip: params.ip as string,
          port: (params.port as number) || 80,
          credentials: {
            username: params.username as string || 'admin',
            password: params.password as string || '',
          },
          accessPoints: [],
          status: 'offline',
          capabilities: (params.capabilities as CredentialType[]) || ['card'],
        };
        controllers.set(controller.id, controller);
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, controller }) }] };
      }

      case 'access_list_controllers': {
        let list = Array.from(controllers.values());
        if (params.type) list = list.filter(c => c.type === params.type);
        if (params.status) list = list.filter(c => c.status === params.status);
        return { content: [{ type: 'text', text: JSON.stringify({ controllers: list }) }] };
      }

      case 'access_controller_status': {
        const controller = controllers.get(params.controller_id as string);
        if (!controller) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Controladora nao encontrada' }) }] };
        }
        // Simular ping
        controller.status = 'online';
        controller.lastSeen = new Date().toISOString();
        return { content: [{ type: 'text', text: JSON.stringify({ controller }) }] };
      }

      case 'access_sync_controller': {
        const controller = controllers.get(params.controller_id as string);
        if (!controller) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Controladora nao encontrada' }) }] };
        }
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              sync_type: params.sync_type || 'full',
              users_synced: persons.size,
              message: 'Sincronizacao concluida',
            }),
          }],
        };
      }

      // === Access Point Management ===
      case 'access_add_point': {
        const point: AccessPoint = {
          id: params.id as string,
          name: params.name as string,
          type: params.type as AccessPointType,
          controllerId: params.controller_id as string,
          direction: (params.direction as AccessDirection) || 'both',
          location: params.location as string,
          status: 'active',
          antiPassback: (params.anti_passback as boolean) || false,
        };
        accessPoints.set(point.id, point);
        const controller = controllers.get(point.controllerId);
        if (controller) controller.accessPoints.push(point.id);
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, access_point: point }) }] };
      }

      case 'access_list_points': {
        let list = Array.from(accessPoints.values());
        if (params.type) list = list.filter(p => p.type === params.type);
        if (params.status) list = list.filter(p => p.status === params.status);
        if (params.location) list = list.filter(p => p.location.includes(params.location as string));
        return { content: [{ type: 'text', text: JSON.stringify({ access_points: list }) }] };
      }

      case 'access_lock_point': {
        const point = accessPoints.get(params.access_point_id as string);
        if (!point) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ponto de acesso nao encontrado' }) }] };
        }
        point.status = 'locked';
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Ponto ${point.name} bloqueado`,
              reason: params.reason,
            }),
          }],
        };
      }

      case 'access_unlock_point': {
        const point = accessPoints.get(params.access_point_id as string);
        if (!point) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ponto de acesso nao encontrado' }) }] };
        }
        point.status = 'active';
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, message: `Ponto ${point.name} desbloqueado` }) }] };
      }

      case 'access_open_point': {
        const point = accessPoints.get(params.access_point_id as string);
        if (!point) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ponto de acesso nao encontrado' }) }] };
        }
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Ponto ${point.name} aberto remotamente`,
              duration: params.duration_seconds || 5,
              opened_by: params.user_id,
            }),
          }],
        };
      }

      // === Person Management ===
      case 'access_add_person': {
        const person: Person = {
          id: params.id as string,
          name: params.name as string,
          type: params.type as PersonType,
          document: params.document as string,
          unit: params.unit as string,
          photo: params.photo as string,
          credentials: [],
          accessRules: [{
            accessPointIds: (params.access_point_ids as string[]) || ['*'],
          }],
          validFrom: params.valid_from as string,
          validUntil: params.valid_until as string,
          blocked: false,
        };
        persons.set(person.id, person);
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, person }) }] };
      }

      case 'access_get_person': {
        const person = persons.get(params.person_id as string);
        if (!person) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Pessoa nao encontrada' }) }] };
        }
        return { content: [{ type: 'text', text: JSON.stringify(person) }] };
      }

      case 'access_list_persons': {
        let list = Array.from(persons.values());
        if (params.type) list = list.filter(p => p.type === params.type);
        if (params.unit) list = list.filter(p => p.unit === params.unit);
        if (params.blocked !== undefined) list = list.filter(p => p.blocked === params.blocked);
        if (params.search) {
          const search = (params.search as string).toLowerCase();
          list = list.filter(p =>
            p.name.toLowerCase().includes(search) ||
            (p.document && p.document.includes(search))
          );
        }
        if (params.limit) list = list.slice(0, params.limit as number);
        return { content: [{ type: 'text', text: JSON.stringify({ persons: list, total: list.length }) }] };
      }

      case 'access_block_person': {
        const person = persons.get(params.person_id as string);
        if (!person) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Pessoa nao encontrada' }) }] };
        }
        person.blocked = true;
        person.blockReason = params.reason as string;
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, message: `${person.name} bloqueado` }) }] };
      }

      case 'access_unblock_person': {
        const person = persons.get(params.person_id as string);
        if (!person) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Pessoa nao encontrada' }) }] };
        }
        person.blocked = false;
        person.blockReason = undefined;
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, message: `${person.name} desbloqueado` }) }] };
      }

      // === Credential Management ===
      case 'access_add_credential': {
        const person = persons.get(params.person_id as string);
        if (!person) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Pessoa nao encontrada' }) }] };
        }
        const cred: PersonCredential = {
          type: params.type as CredentialType,
          value: params.value as string,
          enabled: true,
          addedAt: new Date().toISOString(),
        };
        person.credentials.push(cred);
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, credential: cred }) }] };
      }

      case 'access_remove_credential': {
        const person = persons.get(params.person_id as string);
        if (!person) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Pessoa nao encontrada' }) }] };
        }
        const index = person.credentials.findIndex(c =>
          c.type === params.type && (!params.value || c.value === params.value)
        );
        if (index !== -1) {
          person.credentials.splice(index, 1);
        }
        return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
      }

      case 'access_enroll_face': {
        const person = persons.get(params.person_id as string);
        if (!person) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Pessoa nao encontrada' }) }] };
        }
        person.photo = params.photo as string;
        const faceCred: PersonCredential = {
          type: 'face',
          value: `face_${person.id}`,
          enabled: true,
          addedAt: new Date().toISOString(),
        };
        person.credentials = person.credentials.filter(c => c.type !== 'face');
        person.credentials.push(faceCred);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Face cadastrada para ${person.name}`,
              synced_to: params.controller_ids || [],
            }),
          }],
        };
      }

      case 'access_enroll_fingerprint': {
        const person = persons.get(params.person_id as string);
        if (!person) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Pessoa nao encontrada' }) }] };
        }
        const fpCred: PersonCredential = {
          type: 'fingerprint',
          value: params.template as string,
          enabled: true,
          addedAt: new Date().toISOString(),
        };
        person.credentials.push(fpCred);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Digital cadastrada para ${person.name}`,
              finger_index: params.finger_index || 1,
            }),
          }],
        };
      }

      // === Vehicle Management ===
      case 'access_add_vehicle': {
        const vehicle: Vehicle = {
          id: generateId('VEH'),
          plate: (params.plate as string).toUpperCase().replace(/[^A-Z0-9]/g, ''),
          model: params.model as string,
          color: params.color as string,
          ownerId: params.owner_id as string,
          ownerName: persons.get(params.owner_id as string)?.name || 'Desconhecido',
          type: (params.type as Vehicle['type']) || 'car',
          authorized: true,
        };
        vehicles.set(vehicle.plate, vehicle);
        // Tambem criar credencial de placa para o dono
        const owner = persons.get(vehicle.ownerId);
        if (owner) {
          owner.credentials.push({
            type: 'plate',
            value: vehicle.plate,
            enabled: true,
            addedAt: new Date().toISOString(),
          });
        }
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, vehicle }) }] };
      }

      case 'access_list_vehicles': {
        let list = Array.from(vehicles.values());
        if (params.owner_id) list = list.filter(v => v.ownerId === params.owner_id);
        if (params.plate) list = list.filter(v => v.plate.includes((params.plate as string).toUpperCase()));
        if (params.authorized !== undefined) list = list.filter(v => v.authorized === params.authorized);
        return { content: [{ type: 'text', text: JSON.stringify({ vehicles: list }) }] };
      }

      case 'access_authorize_vehicle': {
        const plate = (params.plate as string).toUpperCase().replace(/[^A-Z0-9]/g, '');
        const vehicle = vehicles.get(plate);
        if (!vehicle) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Veiculo nao encontrado' }) }] };
        }
        vehicle.authorized = params.authorized as boolean;
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, vehicle }) }] };
      }

      // === Access Validation ===
      case 'access_validate': {
        const accessPoint = accessPoints.get(params.access_point_id as string);
        if (!accessPoint) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ponto de acesso nao encontrado' }) }] };
        }

        if (accessPoint.status === 'locked') {
          return {
            content: [{
              type: 'text',
              text: JSON.stringify({
                result: 'denied',
                reason: 'Ponto de acesso bloqueado',
              }),
            }],
          };
        }

        // Buscar pessoa pela credencial
        const credType = params.credential_type as CredentialType;
        const credValue = params.credential_value as string;

        let foundPerson: Person | undefined;
        for (const person of persons.values()) {
          const hasCred = person.credentials.some(c =>
            c.type === credType && c.value === credValue && c.enabled
          );
          if (hasCred) {
            foundPerson = person;
            break;
          }
        }

        if (!foundPerson) {
          const log: AccessLog = {
            id: generateId('LOG'),
            timestamp: new Date().toISOString(),
            accessPointId: accessPoint.id,
            credentialType: credType,
            direction: (params.direction as AccessDirection) || 'entry',
            result: 'denied',
            reason: 'Credencial nao cadastrada',
            confidence: params.confidence as number,
          };
          accessLogs.push(log);
          return { content: [{ type: 'text', text: JSON.stringify({ result: 'denied', reason: 'Credencial nao cadastrada' }) }] };
        }

        const check = checkPersonAccess(foundPerson, accessPoint.id);
        const log: AccessLog = {
          id: generateId('LOG'),
          timestamp: new Date().toISOString(),
          accessPointId: accessPoint.id,
          personId: foundPerson.id,
          personName: foundPerson.name,
          credentialType: credType,
          direction: (params.direction as AccessDirection) || 'entry',
          result: check.allowed ? 'granted' : 'denied',
          reason: check.reason,
          confidence: params.confidence as number,
          photo: params.photo as string,
        };
        accessLogs.push(log);

        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              result: check.allowed ? 'granted' : 'denied',
              reason: check.reason,
              person: {
                id: foundPerson.id,
                name: foundPerson.name,
                type: foundPerson.type,
                unit: foundPerson.unit,
              },
              log_id: log.id,
            }),
          }],
        };
      }

      case 'access_validate_plate': {
        const plate = (params.plate as string).toUpperCase().replace(/[^A-Z0-9]/g, '');
        const vehicle = vehicles.get(plate);

        if (!vehicle) {
          return {
            content: [{
              type: 'text',
              text: JSON.stringify({
                result: 'denied',
                reason: 'Veiculo nao cadastrado',
                plate,
              }),
            }],
          };
        }

        if (!vehicle.authorized) {
          return {
            content: [{
              type: 'text',
              text: JSON.stringify({
                result: 'denied',
                reason: 'Veiculo nao autorizado',
                vehicle,
              }),
            }],
          };
        }

        const log: AccessLog = {
          id: generateId('LOG'),
          timestamp: new Date().toISOString(),
          accessPointId: params.access_point_id as string,
          personId: vehicle.ownerId,
          personName: vehicle.ownerName,
          credentialType: 'plate',
          direction: (params.direction as AccessDirection) || 'entry',
          result: 'granted',
          plateNumber: plate,
          confidence: params.confidence as number,
        };
        accessLogs.push(log);

        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              result: 'granted',
              vehicle,
              log_id: log.id,
            }),
          }],
        };
      }

      // === Access Logs ===
      case 'access_get_logs': {
        let logs = [...accessLogs];
        if (params.access_point_id) logs = logs.filter(l => l.accessPointId === params.access_point_id);
        if (params.person_id) logs = logs.filter(l => l.personId === params.person_id);
        if (params.result) logs = logs.filter(l => l.result === params.result);
        if (params.direction) logs = logs.filter(l => l.direction === params.direction);
        logs = logs.slice(-(params.limit as number || 100));
        return { content: [{ type: 'text', text: JSON.stringify({ logs, total: logs.length }) }] };
      }

      case 'access_statistics': {
        const periodMs = ((params.period_hours as number) || 24) * 60 * 60 * 1000;
        const cutoff = new Date(Date.now() - periodMs);
        const recentLogs = accessLogs.filter(l => new Date(l.timestamp) > cutoff);

        const stats = {
          period_hours: params.period_hours || 24,
          total: recentLogs.length,
          granted: recentLogs.filter(l => l.result === 'granted').length,
          denied: recentLogs.filter(l => l.result === 'denied').length,
          entries: recentLogs.filter(l => l.direction === 'entry').length,
          exits: recentLogs.filter(l => l.direction === 'exit').length,
        };
        return { content: [{ type: 'text', text: JSON.stringify(stats) }] };
      }

      // === Visitor Management ===
      case 'access_create_visitor': {
        const visitor: Person = {
          id: generateId('VIS'),
          name: params.name as string,
          type: 'visitor',
          document: params.document as string,
          unit: params.visiting_unit as string,
          photo: params.photo as string,
          credentials: [],
          accessRules: [{
            accessPointIds: (params.access_point_ids as string[]) || ['*'],
          }],
          validFrom: params.valid_from as string || new Date().toISOString(),
          validUntil: params.valid_until as string || new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          blocked: false,
        };
        persons.set(visitor.id, visitor);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              visitor,
              authorized_by: params.authorized_by,
            }),
          }],
        };
      }

      case 'access_list_visitors': {
        const now = new Date();
        let visitors = Array.from(persons.values()).filter(p => p.type === 'visitor');
        if (params.unit) visitors = visitors.filter(v => v.unit === params.unit);
        return { content: [{ type: 'text', text: JSON.stringify({ visitors }) }] };
      }

      case 'access_checkout_visitor': {
        const visitor = persons.get(params.visitor_id as string);
        if (!visitor || visitor.type !== 'visitor') {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Visitante nao encontrado' }) }] };
        }
        visitor.validUntil = new Date().toISOString();
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, message: `Saida de ${visitor.name} registrada` }) }] };
      }

      // === Emergency ===
      case 'access_emergency_unlock_all': {
        for (const point of accessPoints.values()) {
          point.status = 'unlocked';
        }
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: 'Todos os pontos de acesso desbloqueados',
              reason: params.reason,
              unlocked_by: params.user_id,
              points_affected: accessPoints.size,
            }),
          }],
        };
      }

      case 'access_emergency_lock_all': {
        for (const point of accessPoints.values()) {
          if (params.except_emergency_exits && point.type === 'door') continue;
          point.status = 'locked';
        }
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: 'Lockdown ativado',
              reason: params.reason,
              locked_by: params.user_id,
              emergency_exits_open: params.except_emergency_exits || false,
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
  console.error('MCP Guardian Access iniciado');
}

main().catch(console.error);
