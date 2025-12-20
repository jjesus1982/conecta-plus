/**
 * MCP PPA - Automação de Portões PPA
 * Conecta Plus - Plataforma de Gestão Condominial
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-ppa', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

interface PPADevice {
  id: string;
  ip: string;
  model: string;
  type: 'gate' | 'barrier' | 'controller';
}

const devices: Map<string, PPADevice> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'ppa_add_device',
      description: 'Adiciona motor/central PPA',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          ip: { type: 'string' },
          model: { type: 'string', enum: ['Jet Flex', 'Penta', 'Rio', 'Eurus', 'Custom', 'Levante'] },
          type: { type: 'string', enum: ['gate', 'barrier', 'controller'] },
        },
        required: ['id', 'ip', 'model'],
      },
    },
    {
      name: 'ppa_list_devices',
      description: 'Lista dispositivos PPA',
      inputSchema: { type: 'object', properties: {} },
    },
    {
      name: 'ppa_open_gate',
      description: 'Abre portão',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
        },
        required: ['device_id'],
      },
    },
    {
      name: 'ppa_close_gate',
      description: 'Fecha portão',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
        },
        required: ['device_id'],
      },
    },
    {
      name: 'ppa_stop_gate',
      description: 'Para movimento do portão',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
        },
        required: ['device_id'],
      },
    },
    {
      name: 'ppa_get_status',
      description: 'Status do portão (aberto/fechado/movendo)',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
        },
        required: ['device_id'],
      },
    },
    {
      name: 'ppa_add_control',
      description: 'Cadastra controle remoto',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          control_code: { type: 'string' },
          user_id: { type: 'string' },
        },
        required: ['device_id', 'control_code'],
      },
    },
    {
      name: 'ppa_remove_control',
      description: 'Remove controle remoto',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          control_code: { type: 'string' },
        },
        required: ['device_id', 'control_code'],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'ppa_add_device': {
      const device: PPADevice = {
        id: args.id as string,
        ip: args.ip as string,
        model: args.model as string,
        type: (args.type as 'gate' | 'barrier' | 'controller') || 'gate',
      };
      devices.set(device.id, device);
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, device_id: device.id }) }] };
    }

    case 'ppa_list_devices': {
      const list = Array.from(devices.values());
      return { content: [{ type: 'text', text: JSON.stringify({ devices: list }) }] };
    }

    case 'ppa_open_gate': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, action: 'open', status: 'opening' }) }] };
    }

    case 'ppa_close_gate': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, action: 'close', status: 'closing' }) }] };
    }

    case 'ppa_stop_gate': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, action: 'stop', status: 'stopped' }) }] };
    }

    case 'ppa_get_status': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ device_id: args.device_id, status: 'closed', position: 0 }) }] };
    }

    case 'ppa_add_control': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, control_code: args.control_code }) }] };
    }

    case 'ppa_remove_control': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, removed: args.control_code }) }] };
    }

    default:
      return { content: [{ type: 'text', text: JSON.stringify({ error: `Ferramenta desconhecida: ${name}` }) }] };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP PPA iniciado');
}

main().catch(console.error);
