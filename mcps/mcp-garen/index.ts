/**
 * MCP Garen - Automação de Portões Garen
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-garen', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

const devices: Map<string, any> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'garen_add_device', description: 'Adiciona motor Garen', inputSchema: { type: 'object', properties: { id: { type: 'string' }, ip: { type: 'string' }, model: { type: 'string' } }, required: ['id', 'ip'] } },
    { name: 'garen_list_devices', description: 'Lista dispositivos', inputSchema: { type: 'object', properties: {} } },
    { name: 'garen_open_gate', description: 'Abre portão', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'garen_close_gate', description: 'Fecha portão', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'garen_stop_gate', description: 'Para portão', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'garen_get_status', description: 'Status do portão', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'garen_add_control', description: 'Cadastra controle', inputSchema: { type: 'object', properties: { device_id: { type: 'string' }, control_code: { type: 'string' } }, required: ['device_id', 'control_code'] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  switch (name) {
    case 'garen_add_device': devices.set(args.id as string, { id: args.id, ip: args.ip, model: args.model || 'Speed' }); return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'garen_list_devices': return { content: [{ type: 'text', text: JSON.stringify({ devices: Array.from(devices.values()) }) }] };
    case 'garen_open_gate': return { content: [{ type: 'text', text: JSON.stringify({ success: true, action: 'open' }) }] };
    case 'garen_close_gate': return { content: [{ type: 'text', text: JSON.stringify({ success: true, action: 'close' }) }] };
    case 'garen_stop_gate': return { content: [{ type: 'text', text: JSON.stringify({ success: true, action: 'stop' }) }] };
    case 'garen_get_status': return { content: [{ type: 'text', text: JSON.stringify({ status: 'closed' }) }] };
    case 'garen_add_control': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
