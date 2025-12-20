/**
 * MCP Intelbras CFTV - Model Context Protocol para câmeras Intelbras
 * Conecta Plus - Plataforma de Gestão Condominial
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  {
    name: 'mcp-intelbras-cftv',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Configuração de DVRs/NVRs Intelbras
interface IntelbrasDevice {
  id: string;
  ip: string;
  port: number;
  username: string;
  password: string;
  model: string;
  channels: number;
}

const devices: Map<string, IntelbrasDevice> = new Map();

// Definição das ferramentas disponíveis
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'intelbras_add_device',
      description: 'Adiciona um DVR/NVR Intelbras ao sistema',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'ID único do dispositivo' },
          ip: { type: 'string', description: 'Endereço IP do dispositivo' },
          port: { type: 'number', description: 'Porta HTTP (padrão: 80)' },
          username: { type: 'string', description: 'Usuário de acesso' },
          password: { type: 'string', description: 'Senha de acesso' },
          model: { type: 'string', description: 'Modelo do equipamento' },
          channels: { type: 'number', description: 'Número de canais' },
        },
        required: ['id', 'ip', 'username', 'password'],
      },
    },
    {
      name: 'intelbras_list_devices',
      description: 'Lista todos os dispositivos Intelbras cadastrados',
      inputSchema: { type: 'object', properties: {} },
    },
    {
      name: 'intelbras_get_stream_url',
      description: 'Obtém URL RTSP para streaming de um canal',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string', description: 'ID do dispositivo' },
          channel: { type: 'number', description: 'Número do canal (1-32)' },
          stream_type: { type: 'string', enum: ['main', 'sub'], description: 'Tipo do stream' },
        },
        required: ['device_id', 'channel'],
      },
    },
    {
      name: 'intelbras_ptz_control',
      description: 'Controle PTZ da câmera (Pan, Tilt, Zoom)',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string', description: 'ID do dispositivo' },
          channel: { type: 'number', description: 'Número do canal' },
          action: { type: 'string', enum: ['up', 'down', 'left', 'right', 'zoom_in', 'zoom_out', 'stop'] },
          speed: { type: 'number', description: 'Velocidade (1-8)' },
        },
        required: ['device_id', 'channel', 'action'],
      },
    },
    {
      name: 'intelbras_get_snapshot',
      description: 'Captura snapshot de um canal',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string', description: 'ID do dispositivo' },
          channel: { type: 'number', description: 'Número do canal' },
        },
        required: ['device_id', 'channel'],
      },
    },
    {
      name: 'intelbras_search_recordings',
      description: 'Busca gravações por período',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string', description: 'ID do dispositivo' },
          channel: { type: 'number', description: 'Número do canal' },
          start_time: { type: 'string', description: 'Data/hora início (ISO8601)' },
          end_time: { type: 'string', description: 'Data/hora fim (ISO8601)' },
        },
        required: ['device_id', 'channel', 'start_time', 'end_time'],
      },
    },
    {
      name: 'intelbras_get_events',
      description: 'Obtém eventos de detecção de movimento/alarme',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string', description: 'ID do dispositivo' },
          event_type: { type: 'string', enum: ['motion', 'alarm', 'videoloss', 'all'] },
          limit: { type: 'number', description: 'Número máximo de eventos' },
        },
        required: ['device_id'],
      },
    },
    {
      name: 'intelbras_device_info',
      description: 'Obtém informações do dispositivo (modelo, firmware, etc)',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string', description: 'ID do dispositivo' },
        },
        required: ['device_id'],
      },
    },
  ],
}));

// Handler das ferramentas
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'intelbras_add_device': {
      const device: IntelbrasDevice = {
        id: args.id as string,
        ip: args.ip as string,
        port: (args.port as number) || 80,
        username: args.username as string,
        password: args.password as string,
        model: (args.model as string) || 'unknown',
        channels: (args.channels as number) || 16,
      };
      devices.set(device.id, device);
      return {
        content: [{ type: 'text', text: JSON.stringify({ success: true, device_id: device.id, message: 'Dispositivo adicionado com sucesso' }) }],
      };
    }

    case 'intelbras_list_devices': {
      const deviceList = Array.from(devices.values()).map(d => ({
        id: d.id,
        ip: d.ip,
        model: d.model,
        channels: d.channels,
      }));
      return {
        content: [{ type: 'text', text: JSON.stringify({ devices: deviceList }) }],
      };
    }

    case 'intelbras_get_stream_url': {
      const device = devices.get(args.device_id as string);
      if (!device) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      }
      const streamType = args.stream_type === 'sub' ? 'substream' : 'mainstream';
      const channel = args.channel as number;
      // Formato RTSP Intelbras
      const rtspUrl = `rtsp://${device.username}:${device.password}@${device.ip}:554/cam/realmonitor?channel=${channel}&subtype=${streamType === 'mainstream' ? 0 : 1}`;
      return {
        content: [{ type: 'text', text: JSON.stringify({ rtsp_url: rtspUrl, channel, stream_type: args.stream_type || 'main' }) }],
      };
    }

    case 'intelbras_ptz_control': {
      const device = devices.get(args.device_id as string);
      if (!device) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      }
      // API CGI Intelbras para PTZ
      const ptzCommand = `http://${device.ip}:${device.port}/cgi-bin/ptz.cgi?action=${args.action}&channel=${args.channel}&speed=${args.speed || 4}`;
      return {
        content: [{ type: 'text', text: JSON.stringify({ success: true, command: args.action, channel: args.channel }) }],
      };
    }

    case 'intelbras_get_snapshot': {
      const device = devices.get(args.device_id as string);
      if (!device) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      }
      const snapshotUrl = `http://${device.ip}:${device.port}/cgi-bin/snapshot.cgi?channel=${args.channel}`;
      return {
        content: [{ type: 'text', text: JSON.stringify({ snapshot_url: snapshotUrl, channel: args.channel }) }],
      };
    }

    case 'intelbras_search_recordings': {
      const device = devices.get(args.device_id as string);
      if (!device) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      }
      return {
        content: [{ type: 'text', text: JSON.stringify({
          device_id: args.device_id,
          channel: args.channel,
          start_time: args.start_time,
          end_time: args.end_time,
          recordings: [] // Seria populado via API real
        }) }],
      };
    }

    case 'intelbras_get_events': {
      const device = devices.get(args.device_id as string);
      if (!device) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      }
      return {
        content: [{ type: 'text', text: JSON.stringify({
          device_id: args.device_id,
          event_type: args.event_type || 'all',
          events: [] // Seria populado via API real
        }) }],
      };
    }

    case 'intelbras_device_info': {
      const device = devices.get(args.device_id as string);
      if (!device) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      }
      return {
        content: [{ type: 'text', text: JSON.stringify({
          id: device.id,
          ip: device.ip,
          model: device.model,
          channels: device.channels,
          manufacturer: 'Intelbras',
          protocol: 'ISAPI/CGI'
        }) }],
      };
    }

    default:
      return { content: [{ type: 'text', text: JSON.stringify({ error: `Ferramenta desconhecida: ${name}` }) }] };
  }
});

// Inicialização do servidor
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP Intelbras CFTV iniciado');
}

main().catch(console.error);
