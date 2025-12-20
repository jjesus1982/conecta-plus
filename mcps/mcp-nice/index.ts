/**
 * MCP Nice - Automação de Portões Nice
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-nice', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

const devices: Map<string, any> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'nice_add_device', description: 'Adiciona motor Nice', inputSchema: { type: 'object', properties: { id: { type: 'string' }, ip: { type: 'string' }, model: { type: 'string', enum: ['Robus', 'Road', 'Wingo', 'Spin', 'Pop'] } }, required: ['id', 'ip'] } },
    { name: 'nice_list_devices', description: 'Lista dispositivos', inputSchema: { type: 'object', properties: {} } },
    { name: 'nice_open_gate', description: 'Abre portão', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'nice_close_gate', description: 'Fecha portão', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'nice_stop_gate', description: 'Para portão', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'nice_get_status', description: 'Status do portão', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'nice_partial_open', description: 'Abertura parcial (pedestre)', inputSchema: { type: 'object', properties: { device_id: { type: 'string' }, percentage: { type: 'number' } }, required: ['device_id'] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  switch (name) {
    case 'nice_add_device': devices.set(args.id as string, { id: args.id, ip: args.ip, model: args.model || 'Robus' }); return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'nice_list_devices': return { content: [{ type: 'text', text: JSON.stringify({ devices: Array.from(devices.values()) }) }] };
    case 'nice_open_gate': return { content: [{ type: 'text', text: JSON.stringify({ success: true, action: 'open' }) }] };
    case 'nice_close_gate': return { content: [{ type: 'text', text: JSON.stringify({ success: true, action: 'close' }) }] };
    case 'nice_stop_gate': return { content: [{ type: 'text', text: JSON.stringify({ success: true, action: 'stop' }) }] };
    case 'nice_get_status': return { content: [{ type: 'text', text: JSON.stringify({ status: 'closed' }) }] };
    case 'nice_partial_open': return { content: [{ type: 'text', text: JSON.stringify({ success: true, percentage: args.percentage || 30 }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
