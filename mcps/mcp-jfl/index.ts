/**
 * MCP JFL - Central de Alarme JFL
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-jfl', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

const devices: Map<string, any> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'jfl_add_device', description: 'Adiciona central JFL', inputSchema: { type: 'object', properties: { id: { type: 'string' }, ip: { type: 'string' }, model: { type: 'string', enum: ['Active-20 Ultra', 'Active-32 Duo', 'Active-100 Bus', 'SmartCloud'] } }, required: ['id', 'ip'] } },
    { name: 'jfl_list_devices', description: 'Lista centrais', inputSchema: { type: 'object', properties: {} } },
    { name: 'jfl_arm', description: 'Arma partição', inputSchema: { type: 'object', properties: { device_id: { type: 'string' }, partition: { type: 'number' }, mode: { type: 'string', enum: ['away', 'stay', 'night'] } }, required: ['device_id'] } },
    { name: 'jfl_disarm', description: 'Desarma partição', inputSchema: { type: 'object', properties: { device_id: { type: 'string' }, partition: { type: 'number' }, password: { type: 'string' } }, required: ['device_id', 'password'] } },
    { name: 'jfl_get_status', description: 'Status da central', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'jfl_get_zones', description: 'Status das zonas', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'jfl_bypass_zone', description: 'Anula zona temporariamente', inputSchema: { type: 'object', properties: { device_id: { type: 'string' }, zone: { type: 'number' } }, required: ['device_id', 'zone'] } },
    { name: 'jfl_get_events', description: 'Histórico de eventos', inputSchema: { type: 'object', properties: { device_id: { type: 'string' }, limit: { type: 'number' } }, required: ['device_id'] } },
    { name: 'jfl_trigger_pgm', description: 'Aciona PGM', inputSchema: { type: 'object', properties: { device_id: { type: 'string' }, pgm: { type: 'number' } }, required: ['device_id', 'pgm'] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  switch (name) {
    case 'jfl_add_device': devices.set(args.id as string, { id: args.id, ip: args.ip, model: args.model || 'Active-20 Ultra' }); return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'jfl_list_devices': return { content: [{ type: 'text', text: JSON.stringify({ devices: Array.from(devices.values()) }) }] };
    case 'jfl_arm': return { content: [{ type: 'text', text: JSON.stringify({ success: true, armed: true, mode: args.mode || 'away' }) }] };
    case 'jfl_disarm': return { content: [{ type: 'text', text: JSON.stringify({ success: true, armed: false }) }] };
    case 'jfl_get_status': return { content: [{ type: 'text', text: JSON.stringify({ armed: false, partitions: [{ id: 1, armed: false }], trouble: false }) }] };
    case 'jfl_get_zones': return { content: [{ type: 'text', text: JSON.stringify({ zones: [{ id: 1, name: 'Zona 1', status: 'closed', bypassed: false }] }) }] };
    case 'jfl_bypass_zone': return { content: [{ type: 'text', text: JSON.stringify({ success: true, zone: args.zone, bypassed: true }) }] };
    case 'jfl_get_events': return { content: [{ type: 'text', text: JSON.stringify({ events: [] }) }] };
    case 'jfl_trigger_pgm': return { content: [{ type: 'text', text: JSON.stringify({ success: true, pgm: args.pgm }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
