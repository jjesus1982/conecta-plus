/**
 * MCP Frigate NVR - Model Context Protocol para Frigate NVR
 * Conecta Plus - Plataforma de Gestão Condominial
 *
 * Frigate é um NVR open-source com detecção de objetos em tempo real
 * https://frigate.video/
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  {
    name: 'mcp-frigate-nvr',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

interface FrigateInstance {
  id: string;
  url: string;
  apiKey?: string;
  name: string;
  mqttEnabled: boolean;
  mqttHost?: string;
  mqttPort?: number;
}

interface FrigateCamera {
  name: string;
  enabled: boolean;
  detect: boolean;
  record: boolean;
  snapshots: boolean;
  rtspUrl: string;
  width: number;
  height: number;
  fps: number;
}

interface FrigateEvent {
  id: string;
  camera: string;
  label: string;
  score: number;
  startTime: number;
  endTime?: number;
  hasClip: boolean;
  hasSnapshot: boolean;
  thumbnail?: string;
}

const instances: Map<string, FrigateInstance> = new Map();

// Helper para fazer requisições à API do Frigate
async function frigateRequest(instance: FrigateInstance, endpoint: string, method = 'GET', body?: object): Promise<any> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (instance.apiKey) {
    headers['Authorization'] = `Bearer ${instance.apiKey}`;
  }

  const response = await fetch(`${instance.url}/api${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    throw new Error(`Frigate API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    // === Instance Management ===
    {
      name: 'frigate_add_instance',
      description: 'Adiciona uma instância Frigate NVR ao sistema',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'ID único da instância' },
          url: { type: 'string', description: 'URL do Frigate (ex: http://frigate:5000)' },
          api_key: { type: 'string', description: 'API Key (opcional)' },
          name: { type: 'string', description: 'Nome amigável' },
          mqtt_enabled: { type: 'boolean', description: 'MQTT habilitado' },
          mqtt_host: { type: 'string', description: 'Host MQTT' },
          mqtt_port: { type: 'number', description: 'Porta MQTT' },
        },
        required: ['id', 'url', 'name'],
      },
    },
    {
      name: 'frigate_list_instances',
      description: 'Lista instâncias Frigate cadastradas',
      inputSchema: { type: 'object', properties: {} },
    },
    {
      name: 'frigate_remove_instance',
      description: 'Remove uma instância Frigate',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'ID da instância' },
        },
        required: ['id'],
      },
    },

    // === System Info ===
    {
      name: 'frigate_get_stats',
      description: 'Obtém estatísticas do sistema Frigate (CPU, GPU, detecções)',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
        },
        required: ['instance_id'],
      },
    },
    {
      name: 'frigate_get_config',
      description: 'Obtém configuração completa do Frigate',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
        },
        required: ['instance_id'],
      },
    },
    {
      name: 'frigate_get_version',
      description: 'Obtém versão do Frigate',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
        },
        required: ['instance_id'],
      },
    },

    // === Camera Management ===
    {
      name: 'frigate_list_cameras',
      description: 'Lista todas as câmeras configuradas no Frigate',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
        },
        required: ['instance_id'],
      },
    },
    {
      name: 'frigate_get_camera_snapshot',
      description: 'Obtém snapshot atual de uma câmera',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
          timestamp: { type: 'number', description: 'Timestamp específico (opcional)' },
          bbox: { type: 'boolean', description: 'Incluir bounding boxes' },
        },
        required: ['instance_id', 'camera'],
      },
    },
    {
      name: 'frigate_get_camera_latest',
      description: 'Obtém frame mais recente de uma câmera com detecções',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
          height: { type: 'number', description: 'Altura do frame' },
        },
        required: ['instance_id', 'camera'],
      },
    },
    {
      name: 'frigate_toggle_detection',
      description: 'Ativa/desativa detecção para uma câmera',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
          enabled: { type: 'boolean', description: 'Ativar detecção' },
        },
        required: ['instance_id', 'camera', 'enabled'],
      },
    },
    {
      name: 'frigate_toggle_recording',
      description: 'Ativa/desativa gravação para uma câmera',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
          enabled: { type: 'boolean', description: 'Ativar gravação' },
        },
        required: ['instance_id', 'camera', 'enabled'],
      },
    },
    {
      name: 'frigate_toggle_snapshots',
      description: 'Ativa/desativa snapshots para uma câmera',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
          enabled: { type: 'boolean', description: 'Ativar snapshots' },
        },
        required: ['instance_id', 'camera', 'enabled'],
      },
    },

    // === Events ===
    {
      name: 'frigate_get_events',
      description: 'Busca eventos de detecção',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Filtrar por câmera' },
          label: { type: 'string', description: 'Filtrar por label (person, car, dog, etc)' },
          zone: { type: 'string', description: 'Filtrar por zona' },
          after: { type: 'number', description: 'Timestamp inicial' },
          before: { type: 'number', description: 'Timestamp final' },
          has_clip: { type: 'boolean', description: 'Apenas eventos com clipe' },
          has_snapshot: { type: 'boolean', description: 'Apenas eventos com snapshot' },
          limit: { type: 'number', description: 'Limite de resultados' },
          min_score: { type: 'number', description: 'Score mínimo (0-1)' },
        },
        required: ['instance_id'],
      },
    },
    {
      name: 'frigate_get_event',
      description: 'Obtém detalhes de um evento específico',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          event_id: { type: 'string', description: 'ID do evento' },
        },
        required: ['instance_id', 'event_id'],
      },
    },
    {
      name: 'frigate_get_event_clip',
      description: 'Obtém URL do clipe de um evento',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          event_id: { type: 'string', description: 'ID do evento' },
        },
        required: ['instance_id', 'event_id'],
      },
    },
    {
      name: 'frigate_get_event_thumbnail',
      description: 'Obtém thumbnail de um evento',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          event_id: { type: 'string', description: 'ID do evento' },
        },
        required: ['instance_id', 'event_id'],
      },
    },
    {
      name: 'frigate_delete_event',
      description: 'Deleta um evento',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          event_id: { type: 'string', description: 'ID do evento' },
        },
        required: ['instance_id', 'event_id'],
      },
    },
    {
      name: 'frigate_retain_event',
      description: 'Marca evento para retenção (não será deletado automaticamente)',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          event_id: { type: 'string', description: 'ID do evento' },
          retain: { type: 'boolean', description: 'Reter evento' },
        },
        required: ['instance_id', 'event_id', 'retain'],
      },
    },

    // === Recordings ===
    {
      name: 'frigate_get_recordings',
      description: 'Lista gravações disponíveis',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
          after: { type: 'number', description: 'Timestamp inicial' },
          before: { type: 'number', description: 'Timestamp final' },
        },
        required: ['instance_id', 'camera'],
      },
    },
    {
      name: 'frigate_get_recording_summary',
      description: 'Obtém resumo de gravações por hora/dia',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
          timezone: { type: 'string', description: 'Timezone (ex: America/Sao_Paulo)' },
        },
        required: ['instance_id', 'camera'],
      },
    },
    {
      name: 'frigate_export_recording',
      description: 'Exporta gravação para arquivo',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
          start_time: { type: 'number', description: 'Timestamp inicial' },
          end_time: { type: 'number', description: 'Timestamp final' },
          playback_factor: { type: 'number', description: 'Fator de velocidade' },
        },
        required: ['instance_id', 'camera', 'start_time', 'end_time'],
      },
    },

    // === Live Streaming ===
    {
      name: 'frigate_get_stream_url',
      description: 'Obtém URLs de streaming (RTSP, HLS, WebRTC)',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
          stream_type: { type: 'string', enum: ['rtsp', 'hls', 'webrtc', 'mse'], description: 'Tipo de stream' },
        },
        required: ['instance_id', 'camera'],
      },
    },

    // === Object Detection ===
    {
      name: 'frigate_get_object_counts',
      description: 'Obtém contagem de objetos detectados por câmera',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
        },
        required: ['instance_id'],
      },
    },
    {
      name: 'frigate_get_labels',
      description: 'Lista todos os labels (tipos de objetos) detectáveis',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
        },
        required: ['instance_id'],
      },
    },

    // === PTZ Control (para câmeras compatíveis) ===
    {
      name: 'frigate_ptz_move',
      description: 'Controle PTZ de câmeras ONVIF',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
          action: { type: 'string', enum: ['up', 'down', 'left', 'right', 'zoom_in', 'zoom_out', 'stop'] },
          speed: { type: 'number', description: 'Velocidade (0.0-1.0)' },
        },
        required: ['instance_id', 'camera', 'action'],
      },
    },
    {
      name: 'frigate_ptz_preset',
      description: 'Vai para preset PTZ',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
          preset: { type: 'string', description: 'Nome do preset' },
        },
        required: ['instance_id', 'camera', 'preset'],
      },
    },

    // === Zones ===
    {
      name: 'frigate_list_zones',
      description: 'Lista zonas configuradas para uma câmera',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
        },
        required: ['instance_id', 'camera'],
      },
    },

    // === Sub-Labels (Face Recognition) ===
    {
      name: 'frigate_set_sub_label',
      description: 'Define sub-label para um evento (ex: nome da pessoa)',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          event_id: { type: 'string', description: 'ID do evento' },
          sub_label: { type: 'string', description: 'Sub-label (ex: nome da pessoa)' },
        },
        required: ['instance_id', 'event_id', 'sub_label'],
      },
    },

    // === Timeline ===
    {
      name: 'frigate_get_timeline',
      description: 'Obtém timeline de eventos/gravações',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Nome da câmera' },
          source_id: { type: 'string', description: 'ID de evento/gravação específica' },
          limit: { type: 'number', description: 'Limite de resultados' },
        },
        required: ['instance_id'],
      },
    },

    // === Reviews ===
    {
      name: 'frigate_get_reviews',
      description: 'Obtém itens para revisão (detecções não revisadas)',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          camera: { type: 'string', description: 'Filtrar por câmera' },
          label: { type: 'string', description: 'Filtrar por label' },
          reviewed: { type: 'boolean', description: 'Incluir revisados' },
          limit: { type: 'number', description: 'Limite de resultados' },
        },
        required: ['instance_id'],
      },
    },
    {
      name: 'frigate_mark_reviewed',
      description: 'Marca item como revisado',
      inputSchema: {
        type: 'object',
        properties: {
          instance_id: { type: 'string', description: 'ID da instância Frigate' },
          review_id: { type: 'string', description: 'ID do item de revisão' },
        },
        required: ['instance_id', 'review_id'],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  // === Instance Management ===
  if (name === 'frigate_add_instance') {
    const instance: FrigateInstance = {
      id: args.id as string,
      url: (args.url as string).replace(/\/$/, ''), // Remove trailing slash
      apiKey: args.api_key as string | undefined,
      name: args.name as string,
      mqttEnabled: (args.mqtt_enabled as boolean) || false,
      mqttHost: args.mqtt_host as string | undefined,
      mqttPort: args.mqtt_port as number | undefined,
    };
    instances.set(instance.id, instance);
    return {
      content: [{ type: 'text', text: JSON.stringify({ success: true, instance_id: instance.id }) }],
    };
  }

  if (name === 'frigate_list_instances') {
    const list = Array.from(instances.values()).map(i => ({
      id: i.id,
      name: i.name,
      url: i.url,
      mqtt_enabled: i.mqttEnabled,
    }));
    return { content: [{ type: 'text', text: JSON.stringify({ instances: list }) }] };
  }

  if (name === 'frigate_remove_instance') {
    const deleted = instances.delete(args.id as string);
    return { content: [{ type: 'text', text: JSON.stringify({ success: deleted }) }] };
  }

  // Get instance helper
  const getInstance = (instanceId: string): FrigateInstance => {
    const instance = instances.get(instanceId);
    if (!instance) {
      throw new Error('Instância Frigate não encontrada');
    }
    return instance;
  };

  try {
    switch (name) {
      // === System Info ===
      case 'frigate_get_stats': {
        const instance = getInstance(args.instance_id as string);
        const stats = await frigateRequest(instance, '/stats');
        return { content: [{ type: 'text', text: JSON.stringify(stats) }] };
      }

      case 'frigate_get_config': {
        const instance = getInstance(args.instance_id as string);
        const config = await frigateRequest(instance, '/config');
        return { content: [{ type: 'text', text: JSON.stringify(config) }] };
      }

      case 'frigate_get_version': {
        const instance = getInstance(args.instance_id as string);
        const version = await frigateRequest(instance, '/version');
        return { content: [{ type: 'text', text: JSON.stringify(version) }] };
      }

      // === Camera Management ===
      case 'frigate_list_cameras': {
        const instance = getInstance(args.instance_id as string);
        const config = await frigateRequest(instance, '/config');
        const cameras = Object.entries(config.cameras || {}).map(([name, cam]: [string, any]) => ({
          name,
          enabled: cam.enabled !== false,
          detect: cam.detect?.enabled !== false,
          record: cam.record?.enabled === true,
          snapshots: cam.snapshots?.enabled === true,
        }));
        return { content: [{ type: 'text', text: JSON.stringify({ cameras }) }] };
      }

      case 'frigate_get_camera_snapshot': {
        const instance = getInstance(args.instance_id as string);
        const camera = args.camera as string;
        const params = new URLSearchParams();
        if (args.timestamp) params.append('timestamp', args.timestamp.toString());
        if (args.bbox) params.append('bbox', '1');
        const url = `${instance.url}/api/${camera}/latest.jpg?${params}`;
        return { content: [{ type: 'text', text: JSON.stringify({ snapshot_url: url }) }] };
      }

      case 'frigate_get_camera_latest': {
        const instance = getInstance(args.instance_id as string);
        const camera = args.camera as string;
        const height = args.height || 720;
        const url = `${instance.url}/api/${camera}/latest.jpg?h=${height}`;
        return { content: [{ type: 'text', text: JSON.stringify({ latest_url: url }) }] };
      }

      case 'frigate_toggle_detection': {
        const instance = getInstance(args.instance_id as string);
        const camera = args.camera as string;
        const state = args.enabled ? 'ON' : 'OFF';
        await frigateRequest(instance, `/${camera}/detect/${state}`, 'POST');
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, detect: args.enabled }) }] };
      }

      case 'frigate_toggle_recording': {
        const instance = getInstance(args.instance_id as string);
        const camera = args.camera as string;
        const state = args.enabled ? 'ON' : 'OFF';
        await frigateRequest(instance, `/${camera}/recordings/${state}`, 'POST');
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, recording: args.enabled }) }] };
      }

      case 'frigate_toggle_snapshots': {
        const instance = getInstance(args.instance_id as string);
        const camera = args.camera as string;
        const state = args.enabled ? 'ON' : 'OFF';
        await frigateRequest(instance, `/${camera}/snapshots/${state}`, 'POST');
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, snapshots: args.enabled }) }] };
      }

      // === Events ===
      case 'frigate_get_events': {
        const instance = getInstance(args.instance_id as string);
        const params = new URLSearchParams();
        if (args.camera) params.append('camera', args.camera as string);
        if (args.label) params.append('label', args.label as string);
        if (args.zone) params.append('zone', args.zone as string);
        if (args.after) params.append('after', args.after.toString());
        if (args.before) params.append('before', args.before.toString());
        if (args.has_clip !== undefined) params.append('has_clip', args.has_clip ? '1' : '0');
        if (args.has_snapshot !== undefined) params.append('has_snapshot', args.has_snapshot ? '1' : '0');
        if (args.limit) params.append('limit', args.limit.toString());
        if (args.min_score) params.append('min_score', args.min_score.toString());

        const events = await frigateRequest(instance, `/events?${params}`);
        return { content: [{ type: 'text', text: JSON.stringify({ events }) }] };
      }

      case 'frigate_get_event': {
        const instance = getInstance(args.instance_id as string);
        const event = await frigateRequest(instance, `/events/${args.event_id}`);
        return { content: [{ type: 'text', text: JSON.stringify(event) }] };
      }

      case 'frigate_get_event_clip': {
        const instance = getInstance(args.instance_id as string);
        const url = `${instance.url}/api/events/${args.event_id}/clip.mp4`;
        return { content: [{ type: 'text', text: JSON.stringify({ clip_url: url }) }] };
      }

      case 'frigate_get_event_thumbnail': {
        const instance = getInstance(args.instance_id as string);
        const url = `${instance.url}/api/events/${args.event_id}/thumbnail.jpg`;
        return { content: [{ type: 'text', text: JSON.stringify({ thumbnail_url: url }) }] };
      }

      case 'frigate_delete_event': {
        const instance = getInstance(args.instance_id as string);
        await frigateRequest(instance, `/events/${args.event_id}`, 'DELETE');
        return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
      }

      case 'frigate_retain_event': {
        const instance = getInstance(args.instance_id as string);
        await frigateRequest(instance, `/events/${args.event_id}/retain`, 'POST', { retain: args.retain });
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, retain: args.retain }) }] };
      }

      // === Recordings ===
      case 'frigate_get_recordings': {
        const instance = getInstance(args.instance_id as string);
        const camera = args.camera as string;
        const params = new URLSearchParams();
        if (args.after) params.append('after', args.after.toString());
        if (args.before) params.append('before', args.before.toString());

        const recordings = await frigateRequest(instance, `/${camera}/recordings?${params}`);
        return { content: [{ type: 'text', text: JSON.stringify({ recordings }) }] };
      }

      case 'frigate_get_recording_summary': {
        const instance = getInstance(args.instance_id as string);
        const camera = args.camera as string;
        const tz = args.timezone || 'America/Sao_Paulo';
        const summary = await frigateRequest(instance, `/${camera}/recordings/summary?timezone=${tz}`);
        return { content: [{ type: 'text', text: JSON.stringify(summary) }] };
      }

      case 'frigate_export_recording': {
        const instance = getInstance(args.instance_id as string);
        const camera = args.camera as string;
        const result = await frigateRequest(instance, `/export/${camera}/start/${args.start_time}/end/${args.end_time}`, 'POST', {
          playback: args.playback_factor || 1,
        });
        return { content: [{ type: 'text', text: JSON.stringify(result) }] };
      }

      // === Live Streaming ===
      case 'frigate_get_stream_url': {
        const instance = getInstance(args.instance_id as string);
        const camera = args.camera as string;
        const streamType = args.stream_type || 'hls';

        let url: string;
        switch (streamType) {
          case 'rtsp':
            url = `rtsp://${new URL(instance.url).host}:8554/${camera}`;
            break;
          case 'hls':
            url = `${instance.url}/api/${camera}/stream.m3u8`;
            break;
          case 'webrtc':
            url = `${instance.url}/live/webrtc/api/ws?src=${camera}`;
            break;
          case 'mse':
            url = `${instance.url}/live/mse/api/ws?src=${camera}`;
            break;
          default:
            url = `${instance.url}/api/${camera}/stream.m3u8`;
        }

        return { content: [{ type: 'text', text: JSON.stringify({ stream_url: url, type: streamType }) }] };
      }

      // === Object Detection ===
      case 'frigate_get_object_counts': {
        const instance = getInstance(args.instance_id as string);
        const stats = await frigateRequest(instance, '/stats');
        const counts: Record<string, Record<string, number>> = {};

        for (const [camera, data] of Object.entries(stats.cameras || {})) {
          counts[camera] = (data as any).detection_fps ? { detections: Math.round((data as any).detection_fps) } : {};
        }

        return { content: [{ type: 'text', text: JSON.stringify({ object_counts: counts }) }] };
      }

      case 'frigate_get_labels': {
        const instance = getInstance(args.instance_id as string);
        const config = await frigateRequest(instance, '/config');
        const labels = config.objects?.track || ['person', 'car', 'dog', 'cat', 'bird'];
        return { content: [{ type: 'text', text: JSON.stringify({ labels }) }] };
      }

      // === PTZ Control ===
      case 'frigate_ptz_move': {
        const instance = getInstance(args.instance_id as string);
        const camera = args.camera as string;
        const action = args.action as string;
        const speed = args.speed || 0.5;

        await frigateRequest(instance, `/${camera}/ptz/${action}?speed=${speed}`, 'POST');
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, action }) }] };
      }

      case 'frigate_ptz_preset': {
        const instance = getInstance(args.instance_id as string);
        const camera = args.camera as string;
        const preset = args.preset as string;

        await frigateRequest(instance, `/${camera}/ptz/preset?preset=${preset}`, 'POST');
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, preset }) }] };
      }

      // === Zones ===
      case 'frigate_list_zones': {
        const instance = getInstance(args.instance_id as string);
        const camera = args.camera as string;
        const config = await frigateRequest(instance, '/config');
        const cameraConfig = config.cameras?.[camera];
        const zones = cameraConfig?.zones ? Object.keys(cameraConfig.zones) : [];
        return { content: [{ type: 'text', text: JSON.stringify({ zones }) }] };
      }

      // === Sub-Labels ===
      case 'frigate_set_sub_label': {
        const instance = getInstance(args.instance_id as string);
        await frigateRequest(instance, `/events/${args.event_id}/sub_label`, 'POST', {
          subLabel: args.sub_label,
        });
        return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
      }

      // === Timeline ===
      case 'frigate_get_timeline': {
        const instance = getInstance(args.instance_id as string);
        const params = new URLSearchParams();
        if (args.camera) params.append('camera', args.camera as string);
        if (args.source_id) params.append('source_id', args.source_id as string);
        if (args.limit) params.append('limit', args.limit.toString());

        const timeline = await frigateRequest(instance, `/timeline?${params}`);
        return { content: [{ type: 'text', text: JSON.stringify({ timeline }) }] };
      }

      // === Reviews ===
      case 'frigate_get_reviews': {
        const instance = getInstance(args.instance_id as string);
        const params = new URLSearchParams();
        if (args.camera) params.append('camera', args.camera as string);
        if (args.label) params.append('label', args.label as string);
        if (args.reviewed !== undefined) params.append('reviewed', args.reviewed ? '1' : '0');
        if (args.limit) params.append('limit', args.limit.toString());

        const reviews = await frigateRequest(instance, `/review?${params}`);
        return { content: [{ type: 'text', text: JSON.stringify({ reviews }) }] };
      }

      case 'frigate_mark_reviewed': {
        const instance = getInstance(args.instance_id as string);
        await frigateRequest(instance, `/review/${args.review_id}/viewed`, 'POST');
        return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
      }

      default:
        return { content: [{ type: 'text', text: JSON.stringify({ error: `Ferramenta desconhecida: ${name}` }) }] };
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
    return { content: [{ type: 'text', text: JSON.stringify({ error: errorMessage }) }] };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP Frigate NVR iniciado');
}

main().catch(console.error);
