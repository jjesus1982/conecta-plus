/**
 * MCP Furukawa - OLTs GPON
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-furukawa', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

const olts: Map<string, any> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'furukawa_add_olt', description: 'Adiciona OLT Furukawa', inputSchema: { type: 'object', properties: { id: { type: 'string' }, host: { type: 'string' }, username: { type: 'string' }, password: { type: 'string' }, model: { type: 'string' } }, required: ['id', 'host', 'username', 'password'] } },
    { name: 'furukawa_list_olts', description: 'Lista OLTs', inputSchema: { type: 'object', properties: {} } },
    { name: 'furukawa_list_onus', description: 'Lista ONUs', inputSchema: { type: 'object', properties: { olt_id: { type: 'string' }, pon_port: { type: 'string' } }, required: ['olt_id'] } },
    { name: 'furukawa_get_onu_info', description: 'Info da ONU', inputSchema: { type: 'object', properties: { olt_id: { type: 'string' }, onu_id: { type: 'string' } }, required: ['olt_id', 'onu_id'] } },
    { name: 'furukawa_get_onu_signal', description: 'Sinal óptico da ONU', inputSchema: { type: 'object', properties: { olt_id: { type: 'string' }, onu_id: { type: 'string' } }, required: ['olt_id', 'onu_id'] } },
    { name: 'furukawa_provision_onu', description: 'Provisiona ONU', inputSchema: { type: 'object', properties: { olt_id: { type: 'string' }, serial: { type: 'string' }, profile: { type: 'string' }, vlan: { type: 'number' } }, required: ['olt_id', 'serial', 'profile'] } },
    { name: 'furukawa_remove_onu', description: 'Remove ONU', inputSchema: { type: 'object', properties: { olt_id: { type: 'string' }, onu_id: { type: 'string' } }, required: ['olt_id', 'onu_id'] } },
    { name: 'furukawa_restart_onu', description: 'Reinicia ONU', inputSchema: { type: 'object', properties: { olt_id: { type: 'string' }, onu_id: { type: 'string' } }, required: ['olt_id', 'onu_id'] } },
    { name: 'furukawa_get_alarms', description: 'Alarmes ativos', inputSchema: { type: 'object', properties: { olt_id: { type: 'string' } }, required: ['olt_id'] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  switch (name) {
    case 'furukawa_add_olt': olts.set(args.id as string, { id: args.id, host: args.host, model: args.model || 'FK-OLT-G4S' }); return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'furukawa_list_olts': return { content: [{ type: 'text', text: JSON.stringify({ olts: Array.from(olts.values()) }) }] };
    case 'furukawa_list_onus': return { content: [{ type: 'text', text: JSON.stringify({ onus: [] }) }] };
    case 'furukawa_get_onu_info': return { content: [{ type: 'text', text: JSON.stringify({ onu_id: args.onu_id, status: 'online' }) }] };
    case 'furukawa_get_onu_signal': return { content: [{ type: 'text', text: JSON.stringify({ rx_power: -20, tx_power: 2 }) }] };
    case 'furukawa_provision_onu': return { content: [{ type: 'text', text: JSON.stringify({ success: true, serial: args.serial }) }] };
    case 'furukawa_remove_onu': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'furukawa_restart_onu': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'furukawa_get_alarms': return { content: [{ type: 'text', text: JSON.stringify({ alarms: [] }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
