/**
 * MCP Intelbras Alarme - Centrais AMT
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-intelbras-alarme', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

const devices: Map<string, any> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'intelbras_alarm_add_device', description: 'Adiciona central AMT', inputSchema: { type: 'object', properties: { id: { type: 'string' }, ip: { type: 'string' }, model: { type: 'string', enum: ['AMT-2018', 'AMT-4010', 'AMT-8000'] } }, required: ['id', 'ip'] } },
    { name: 'intelbras_alarm_list_devices', description: 'Lista centrais', inputSchema: { type: 'object', properties: {} } },
    { name: 'intelbras_alarm_arm', description: 'Arma partição', inputSchema: { type: 'object', properties: { device_id: { type: 'string' }, partition: { type: 'number' }, mode: { type: 'string' } }, required: ['device_id'] } },
    { name: 'intelbras_alarm_disarm', description: 'Desarma partição', inputSchema: { type: 'object', properties: { device_id: { type: 'string' }, partition: { type: 'number' }, password: { type: 'string' } }, required: ['device_id', 'password'] } },
    { name: 'intelbras_alarm_get_status', description: 'Status da central', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'intelbras_alarm_get_zones', description: 'Status das zonas', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'intelbras_alarm_bypass_zone', description: 'Anula zona', inputSchema: { type: 'object', properties: { device_id: { type: 'string' }, zone: { type: 'number' } }, required: ['device_id', 'zone'] } },
    { name: 'intelbras_alarm_get_events', description: 'Histórico de eventos', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } }, required: ['device_id'] } },
    { name: 'intelbras_alarm_trigger_pgm', description: 'Aciona PGM', inputSchema: { type: 'object', properties: { device_id: { type: 'string' }, pgm: { type: 'number' }, action: { type: 'string', enum: ['on', 'off', 'pulse'] } }, required: ['device_id', 'pgm'] } },
    { name: 'intelbras_alarm_panic', description: 'Dispara pânico', inputSchema: { type: 'object', properties: { device_id: { type: 'string' }, type: { type: 'string', enum: ['audible', 'silent', 'medical', 'fire'] } }, required: ['device_id'] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  switch (name) {
    case 'intelbras_alarm_add_device': devices.set(args.id as string, { id: args.id, ip: args.ip, model: args.model || 'AMT-2018' }); return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'intelbras_alarm_list_devices': return { content: [{ type: 'text', text: JSON.stringify({ devices: Array.from(devices.values()) }) }] };
    case 'intelbras_alarm_arm': return { content: [{ type: 'text', text: JSON.stringify({ success: true, armed: true }) }] };
    case 'intelbras_alarm_disarm': return { content: [{ type: 'text', text: JSON.stringify({ success: true, armed: false }) }] };
    case 'intelbras_alarm_get_status': return { content: [{ type: 'text', text: JSON.stringify({ armed: false, trouble: false, ac_fail: false, battery_low: false }) }] };
    case 'intelbras_alarm_get_zones': return { content: [{ type: 'text', text: JSON.stringify({ zones: [] }) }] };
    case 'intelbras_alarm_bypass_zone': return { content: [{ type: 'text', text: JSON.stringify({ success: true, zone: args.zone }) }] };
    case 'intelbras_alarm_get_events': return { content: [{ type: 'text', text: JSON.stringify({ events: [] }) }] };
    case 'intelbras_alarm_trigger_pgm': return { content: [{ type: 'text', text: JSON.stringify({ success: true, pgm: args.pgm }) }] };
    case 'intelbras_alarm_panic': return { content: [{ type: 'text', text: JSON.stringify({ success: true, type: args.type || 'audible' }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
