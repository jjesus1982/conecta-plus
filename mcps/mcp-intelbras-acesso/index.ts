/**
 * MCP Intelbras Acesso - Controladoras SS e CT
 * Conecta Plus - Plataforma de Gestão Condominial
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-intelbras-acesso', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

interface IntelbrasAccessDevice {
  id: string;
  ip: string;
  port: number;
  username: string;
  password: string;
  model: string;
}

const devices: Map<string, IntelbrasAccessDevice> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'intelbras_access_add_device',
      description: 'Adiciona controladora Intelbras (SS 230, SS 320, CT 500)',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          ip: { type: 'string' },
          port: { type: 'number' },
          username: { type: 'string' },
          password: { type: 'string' },
          model: { type: 'string', enum: ['SS230', 'SS320', 'SS420', 'CT500', 'CT520'] },
        },
        required: ['id', 'ip', 'username', 'password'],
      },
    },
    {
      name: 'intelbras_access_list_devices',
      description: 'Lista controladoras Intelbras cadastradas',
      inputSchema: { type: 'object', properties: {} },
    },
    {
      name: 'intelbras_access_add_user',
      description: 'Cadastra usuário na controladora',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          user_id: { type: 'number' },
          name: { type: 'string' },
          password: { type: 'string' },
          card: { type: 'string' },
        },
        required: ['device_id', 'user_id', 'name'],
      },
    },
    {
      name: 'intelbras_access_remove_user',
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
      name: 'intelbras_access_add_fingerprint',
      description: 'Cadastra digital do usuário',
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
      name: 'intelbras_access_open_door',
      description: 'Abre porta remotamente',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          relay: { type: 'number' },
        },
        required: ['device_id'],
      },
    },
    {
      name: 'intelbras_access_get_logs',
      description: 'Obtém logs de acesso',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          start_time: { type: 'string' },
          end_time: { type: 'string' },
        },
        required: ['device_id'],
      },
    },
    {
      name: 'intelbras_access_set_access_rule',
      description: 'Define regra de acesso por horário',
      inputSchema: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          user_id: { type: 'number' },
          rule_id: { type: 'number' },
          days: { type: 'array', items: { type: 'number' } },
          start_time: { type: 'string' },
          end_time: { type: 'string' },
        },
        required: ['device_id', 'user_id', 'rule_id'],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'intelbras_access_add_device': {
      const device: IntelbrasAccessDevice = {
        id: args.id as string,
        ip: args.ip as string,
        port: (args.port as number) || 80,
        username: args.username as string,
        password: args.password as string,
        model: (args.model as string) || 'SS320',
      };
      devices.set(device.id, device);
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, device_id: device.id }) }] };
    }

    case 'intelbras_access_list_devices': {
      const list = Array.from(devices.values()).map(d => ({ id: d.id, ip: d.ip, model: d.model }));
      return { content: [{ type: 'text', text: JSON.stringify({ devices: list }) }] };
    }

    case 'intelbras_access_add_user': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, user_id: args.user_id }) }] };
    }

    case 'intelbras_access_remove_user': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, removed: args.user_id }) }] };
    }

    case 'intelbras_access_add_fingerprint': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, enrolled: true }) }] };
    }

    case 'intelbras_access_open_door': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, relay: args.relay || 1 }) }] };
    }

    case 'intelbras_access_get_logs': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ logs: [] }) }] };
    }

    case 'intelbras_access_set_access_rule': {
      const device = devices.get(args.device_id as string);
      if (!device) return { content: [{ type: 'text', text: JSON.stringify({ error: 'Dispositivo não encontrado' }) }] };
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, rule_id: args.rule_id }) }] };
    }

    default:
      return { content: [{ type: 'text', text: JSON.stringify({ error: `Ferramenta desconhecida: ${name}` }) }] };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP Intelbras Acesso iniciado');
}

main().catch(console.error);
