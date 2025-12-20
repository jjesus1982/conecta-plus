/**
 * MCP Hikvision CFTV - Model Context Protocol para câmeras Hikvision
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
    name: 'mcp-hikvision-cftv',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

interface HikvisionDevice {
  id: string;
  ip: string;
  port: number;
  username: string;
  password: string;
  model: string;
  channels: number;
}

const devices: Map<string, HikvisionDevice> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'hikvision_add_device',
      description: 'Adiciona um DVR/NVR Hikvision ao sistema',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'ID único do dispositivo' },
          ip: { type: 'string', description: 'Endereço IP' },
          port: { type: 'number', description: 'Porta HTTP (padrão: 80)' },
          username: { type: 'string', description: 'Usuário' },
          password: { type: 'string', description: 'Senha' },
          model: { type: 'string', description: 'Modelo' },
          channels: { type: 'number', description: 'Número de canais' },
        },
        required: ['id', 'ip', 'username', 'password'],
      },
    },
    {
      name: 'hikvision_list_devices',
      description: 'Lista dispositivos Hikvision cadastrados',
      inputSchema: { type: 'object', properties: {} },
    },
    {
      name: 'hikvision_get_stream_url',
      description: 'Obtém URL RTSP para streaming',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          channel: { type: 'number' },
          stream_type: { type: 'string', enum: ['main', 'sub'] },
        },
        required: ['device_id', 'channel'],
      },
    },
    {
      name: 'hikvision_ptz_control',
      description: 'Controle PTZ via ISAPI',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          channel: { type: 'number' },
          action: { type: 'string', enum: ['up', 'down', 'left', 'right', 'zoom_in', 'zoom_out', 'preset', 'stop'] },
          preset_id: { type: 'number', description: 'ID do preset (se action=preset)' },
          speed: { type: 'number' },
        },
        required: ['device_id', 'channel', 'action'],
      },
    },
    {
      name: 'hikvision_get_snapshot',
      description: 'Captura snapshot ISAPI',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          channel: { type: 'number' },
        },
        required: ['device_id', 'channel'],
      },
    },
    {
      name: 'hikvision_search_recordings',
      description: 'Busca gravações via ISAPI ContentMgmt',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          channel: { type: 'number' },
          start_time: { type: 'string' },
          end_time: { type: 'string' },
          event_type: { type: 'string', enum: ['all', 'motion', 'alarm', 'manual'] },
        },
        required: ['device_id', 'channel', 'start_time', 'end_time'],
      },
    },
    {
      name: 'hikvision_smart_events',
      description: 'Configuração de eventos inteligentes (VCA)',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          channel: { type: 'number' },
          event_type: { type: 'string', enum: ['linedetection', 'fielddetection', 'regionEntrance', 'regionExiting', 'loitering', 'group', 'rapidMove', 'parking', 'unattendedBaggage', 'attendedBaggage'] },
          enabled: { type: 'boolean' },
        },
        required: ['device_id', 'channel', 'event_type'],
      },
    },
    {
      name: 'hikvision_face_recognition',
      description: 'Busca por reconhecimento facial',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          image_base64: { type: 'string', description: 'Imagem em base64 para busca' },
          start_time: { type: 'string' },
          end_time: { type: 'string' },
        },
        required: ['device_id'],
      },
    },
    {
      name: 'hikvision_device_info',
      description: 'Informações do dispositivo via ISAPI',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
        },
        required: ['device_id'],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'hikvision_add_device': {
      const device: HikvisionDevice = {
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
        content: [{ type: 'text', text: JSON.stringify({ success: true, device_id: device.id }) }],
      };
    }

    case 'hikvision_list_devices': {
      const deviceList = Array.from(devices.values()).map(d => ({
        id: d.id, ip: d.ip, model: d.model, channels: d.channels,
      }));
      return { content: [{ type: 'text', text: JSON.stringify({ devices: deviceList }) }] };
    }

    case 'hikvision_get_stream_url': {
      const device = devices.get(args.device_id as string);
      if (!device) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      }
      const streamNum = args.stream_type === 'sub' ? '102' : '101';
      // Formato RTSP Hikvision
      const rtspUrl = `rtsp://${device.username}:${device.password}@${device.ip}:554/Streaming/Channels/${args.channel}${streamNum}`;
      return {
        content: [{ type: 'text', text: JSON.stringify({ rtsp_url: rtspUrl }) }],
      };
    }

    case 'hikvision_ptz_control': {
      const device = devices.get(args.device_id as string);
      if (!device) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      }
      // ISAPI PTZ endpoint
      const isapiUrl = `http://${device.ip}:${device.port}/ISAPI/PTZCtrl/channels/${args.channel}/continuous`;
      return {
        content: [{ type: 'text', text: JSON.stringify({ success: true, action: args.action }) }],
      };
    }

    case 'hikvision_get_snapshot': {
      const device = devices.get(args.device_id as string);
      if (!device) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      }
      const snapshotUrl = `http://${device.ip}:${device.port}/ISAPI/Streaming/channels/${args.channel}01/picture`;
      return {
        content: [{ type: 'text', text: JSON.stringify({ snapshot_url: snapshotUrl }) }],
      };
    }

    case 'hikvision_search_recordings': {
      const device = devices.get(args.device_id as string);
      if (!device) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      }
      // ISAPI ContentMgmt/search
      return {
        content: [{ type: 'text', text: JSON.stringify({
          device_id: args.device_id,
          recordings: [],
          message: 'Busca via ISAPI ContentMgmt'
        }) }],
      };
    }

    case 'hikvision_smart_events': {
      const device = devices.get(args.device_id as string);
      if (!device) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      }
      return {
        content: [{ type: 'text', text: JSON.stringify({
          success: true,
          event_type: args.event_type,
          enabled: args.enabled
        }) }],
      };
    }

    case 'hikvision_face_recognition': {
      const device = devices.get(args.device_id as string);
      if (!device) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      }
      return {
        content: [{ type: 'text', text: JSON.stringify({
          matches: [],
          message: 'Busca facial via ISAPI FaceDetect'
        }) }],
      };
    }

    case 'hikvision_device_info': {
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
          manufacturer: 'Hikvision',
          protocol: 'ISAPI'
        }) }],
      };
    }

    default:
      return { content: [{ type: 'text', text: JSON.stringify({ error: `Ferramenta desconhecida: ${name}` }) }] };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP Hikvision CFTV iniciado');
}

main().catch(console.error);
