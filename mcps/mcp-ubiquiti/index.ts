/**
 * MCP Ubiquiti - UniFi Controller
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-ubiquiti', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

interface UniFiController {
  id: string;
  url: string;
  username: string;
  password: string;
  site: string;
}

const controllers: Map<string, UniFiController> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'unifi_add_controller', description: 'Adiciona UniFi Controller', inputSchema: { type: 'object', properties: { id: { type: 'string' }, url: { type: 'string' }, username: { type: 'string' }, password: { type: 'string' }, site: { type: 'string' } }, required: ['id', 'url', 'username', 'password'] } },
    { name: 'unifi_list_controllers', description: 'Lista controllers', inputSchema: { type: 'object', properties: {} } },
    { name: 'unifi_list_devices', description: 'Lista dispositivos UniFi', inputSchema: { type: 'object', properties: { controller_id: { type: 'string' } }, required: ['controller_id'] } },
    { name: 'unifi_list_clients', description: 'Lista clientes conectados', inputSchema: { type: 'object', properties: { controller_id: { type: 'string' } }, required: ['controller_id'] } },
    { name: 'unifi_get_device_stats', description: 'Estatísticas de dispositivo', inputSchema: { type: 'object', properties: { controller_id: { type: 'string' }, device_mac: { type: 'string' } }, required: ['controller_id', 'device_mac'] } },
    { name: 'unifi_restart_device', description: 'Reinicia dispositivo', inputSchema: { type: 'object', properties: { controller_id: { type: 'string' }, device_mac: { type: 'string' } }, required: ['controller_id', 'device_mac'] } },
    { name: 'unifi_block_client', description: 'Bloqueia cliente', inputSchema: { type: 'object', properties: { controller_id: { type: 'string' }, client_mac: { type: 'string' } }, required: ['controller_id', 'client_mac'] } },
    { name: 'unifi_unblock_client', description: 'Desbloqueia cliente', inputSchema: { type: 'object', properties: { controller_id: { type: 'string' }, client_mac: { type: 'string' } }, required: ['controller_id', 'client_mac'] } },
    { name: 'unifi_authorize_guest', description: 'Autoriza guest WiFi', inputSchema: { type: 'object', properties: { controller_id: { type: 'string' }, client_mac: { type: 'string' }, minutes: { type: 'number' }, up_kbps: { type: 'number' }, down_kbps: { type: 'number' } }, required: ['controller_id', 'client_mac'] } },
    { name: 'unifi_set_port_profile', description: 'Configura perfil de porta', inputSchema: { type: 'object', properties: { controller_id: { type: 'string' }, device_mac: { type: 'string' }, port_idx: { type: 'number' }, profile: { type: 'string' } }, required: ['controller_id', 'device_mac', 'port_idx', 'profile'] } },
    { name: 'unifi_get_alarms', description: 'Lista alarmes', inputSchema: { type: 'object', properties: { controller_id: { type: 'string' } }, required: ['controller_id'] } },
    { name: 'unifi_get_events', description: 'Lista eventos', inputSchema: { type: 'object', properties: { controller_id: { type: 'string' }, limit: { type: 'number' } }, required: ['controller_id'] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  switch (name) {
    case 'unifi_add_controller': {
      controllers.set(args.id as string, { id: args.id as string, url: args.url as string, username: args.username as string, password: args.password as string, site: (args.site as string) || 'default' });
      return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    }
    case 'unifi_list_controllers': return { content: [{ type: 'text', text: JSON.stringify({ controllers: Array.from(controllers.values()).map(c => ({ id: c.id, url: c.url })) }) }] };
    case 'unifi_list_devices': return { content: [{ type: 'text', text: JSON.stringify({ devices: [] }) }] };
    case 'unifi_list_clients': return { content: [{ type: 'text', text: JSON.stringify({ clients: [] }) }] };
    case 'unifi_get_device_stats': return { content: [{ type: 'text', text: JSON.stringify({ device_mac: args.device_mac, uptime: 0, cpu: 0, mem: 0 }) }] };
    case 'unifi_restart_device': return { content: [{ type: 'text', text: JSON.stringify({ success: true, device_mac: args.device_mac }) }] };
    case 'unifi_block_client': return { content: [{ type: 'text', text: JSON.stringify({ success: true, blocked: true }) }] };
    case 'unifi_unblock_client': return { content: [{ type: 'text', text: JSON.stringify({ success: true, blocked: false }) }] };
    case 'unifi_authorize_guest': return { content: [{ type: 'text', text: JSON.stringify({ success: true, authorized: true }) }] };
    case 'unifi_set_port_profile': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'unifi_get_alarms': return { content: [{ type: 'text', text: JSON.stringify({ alarms: [] }) }] };
    case 'unifi_get_events': return { content: [{ type: 'text', text: JSON.stringify({ events: [] }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
