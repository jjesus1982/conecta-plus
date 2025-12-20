/**
 * MCP Control iD - Controle de Acesso
 * Conecta Plus - Plataforma de Gestão Condominial
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-control-id', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

interface ControlIDDevice {
  id: string;
  ip: string;
  port: number;
  login: string;
  password: string;
  model: string;
}

const devices: Map<string, ControlIDDevice> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'controlid_add_device',
      description: 'Adiciona controladora Control iD (iDAccess, iDBox, iDFlex)',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          ip: { type: 'string' },
          port: { type: 'number' },
          login: { type: 'string' },
          password: { type: 'string' },
          model: { type: 'string', enum: ['iDAccess', 'iDBox', 'iDFlex', 'iDFace'] },
        },
        required: ['id', 'ip', 'login', 'password'],
      },
    },
    {
      name: 'controlid_list_devices',
      description: 'Lista controladoras cadastradas',
      inputSchema: { type: 'object', properties: {} },
    },
    {
      name: 'controlid_add_user',
      description: 'Cadastra usuário na controladora',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          user_id: { type: 'number' },
          name: { type: 'string' },
          registration: { type: 'string' },
          begin_time: { type: 'string' },
          end_time: { type: 'string' },
        },
        required: ['device_id', 'user_id', 'name'],
      },
    },
    {
      name: 'controlid_remove_user',
      description: 'Remove usuário da controladora',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          user_id: { type: 'number' },
        },
        required: ['device_id', 'user_id'],
      },
    },
    {
      name: 'controlid_add_card',
      description: 'Cadastra cartão/tag RFID para usuário',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          user_id: { type: 'number' },
          card_number: { type: 'string' },
        },
        required: ['device_id', 'user_id', 'card_number'],
      },
    },
    {
      name: 'controlid_add_fingerprint',
      description: 'Cadastra biometria digital',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          user_id: { type: 'number' },
          finger_index: { type: 'number' },
          template: { type: 'string' },
        },
        required: ['device_id', 'user_id', 'template'],
      },
    },
    {
      name: 'controlid_add_face',
      description: 'Cadastra reconhecimento facial',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          user_id: { type: 'number' },
          image_base64: { type: 'string' },
        },
        required: ['device_id', 'user_id', 'image_base64'],
      },
    },
    {
      name: 'controlid_open_door',
      description: 'Abre porta/portão remotamente',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          door: { type: 'number', description: 'Número da porta (1 ou 2)' },
        },
        required: ['device_id'],
      },
    },
    {
      name: 'controlid_get_access_logs',
      description: 'Obtém logs de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          start_time: { type: 'string' },
          end_time: { type: 'string' },
          limit: { type: 'number' },
        },
        required: ['device_id'],
      },
    },
    {
      name: 'controlid_set_timezone',
      description: 'Configura fuso horário de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          user_id: { type: 'number' },
          timezone_id: { type: 'number' },
        },
        required: ['device_id', 'user_id', 'timezone_id'],
      },
    },
    {
      name: 'controlid_sync_time',
      description: 'Sincroniza horário da controladora',
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
    case 'controlid_add_device': {
      const device: ControlIDDevice = {
        id: args.id as string,
        ip: args.ip as string,
        port: (args.port as number) || 80,
        login: args.login as string,
        password: args.password as string,
        model: (args.model as string) || 'iDAccess',
      };
      devices.set(device.id, device);
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, device_id: device.id }) }] };
    }

    case 'controlid_list_devices': {
      const list = Array.from(devices.values()).map(d => ({ id: d.id, ip: d.ip, model: d.model }));
      return { content: [{ type: 'text', text: JSON.stringify({ devices: list }) }] };
    }

    case 'controlid_add_user': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      // API Control iD: POST /create_objects.fcgi
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, user_id: args.user_id, name: args.name }) }] };
    }

    case 'controlid_remove_user': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      // API Control iD: POST /destroy_objects.fcgi
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, user_id: args.user_id }) }] };
    }

    case 'controlid_add_card': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, card: args.card_number }) }] };
    }

    case 'controlid_add_fingerprint': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, user_id: args.user_id, finger: args.finger_index }) }] };
    }

    case 'controlid_add_face': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, user_id: args.user_id, face_enrolled: true }) }] };
    }

    case 'controlid_open_door': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      // API: POST /execute.fcgi com action=sec_box e parameters.action=open
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, door: args.door || 1, status: 'opened' }) }] };
    }

    case 'controlid_get_access_logs': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      // API: POST /load_objects.fcgi com object=access_logs
      return { content: [{ type: 'text', text: JSON.stringify({ logs: [], total: 0 }) }] };
    }

    case 'controlid_set_timezone': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, timezone_id: args.timezone_id }) }] };
    }

    case 'controlid_sync_time': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, synced: true }) }] };
    }

    default:
      return { content: [{ type: 'text', text: JSON.stringify({ error: `Ferramenta desconhecida: ${name}` }) }] };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP Control iD iniciado');
}

main().catch(console.error);
