/**
 * MCP Ponto REP - Relógio de Ponto Eletrônico
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-ponto-rep', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

const reps: Map<string, any> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'rep_add_device', description: 'Adiciona REP', inputSchema: { type: 'object', properties: { id: { type: 'string' }, ip: { type: 'string' }, model: { type: 'string' }, brand: { type: 'string', enum: ['Henry', 'Dimep', 'Control iD', 'Tangerino'] } }, required: ['id', 'ip'] } },
    { name: 'rep_list_devices', description: 'Lista REPs', inputSchema: { type: 'object', properties: {} } },
    { name: 'rep_add_employee', description: 'Cadastra funcionário no REP', inputSchema: { type: 'object', properties: { rep_id: { type: 'string' }, employee_id: { type: 'string' }, name: { type: 'string' }, pis: { type: 'string' }, card: { type: 'string' } }, required: ['rep_id', 'employee_id', 'name', 'pis'] } },
    { name: 'rep_remove_employee', description: 'Remove funcionário do REP', inputSchema: { type: 'object', properties: { rep_id: { type: 'string' }, employee_id: { type: 'string' } }, required: ['rep_id', 'employee_id'] } },
    { name: 'rep_add_fingerprint', description: 'Cadastra digital', inputSchema: { type: 'object', properties: { rep_id: { type: 'string' }, employee_id: { type: 'string' }, template: { type: 'string' } }, required: ['rep_id', 'employee_id', 'template'] } },
    { name: 'rep_get_punches', description: 'Coleta marcações', inputSchema: { type: 'object', properties: { rep_id: { type: 'string' }, start_date: { type: 'string' }, end_date: { type: 'string' }, employee_id: { type: 'string' } }, required: ['rep_id'] } },
    { name: 'rep_export_afd', description: 'Exporta AFD (Arquivo-Fonte de Dados)', inputSchema: { type: 'object', properties: { rep_id: { type: 'string' } }, required: ['rep_id'] } },
    { name: 'rep_sync_employees', description: 'Sincroniza funcionários', inputSchema: { type: 'object', properties: { rep_id: { type: 'string' }, employees: { type: 'array', items: { type: 'object' } } }, required: ['rep_id', 'employees'] } },
    { name: 'rep_get_status', description: 'Status do REP', inputSchema: { type: 'object', properties: { rep_id: { type: 'string' } }, required: ['rep_id'] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  switch (name) {
    case 'rep_add_device': reps.set(args.id as string, { id: args.id, ip: args.ip, model: args.model, brand: args.brand || 'Henry' }); return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'rep_list_devices': return { content: [{ type: 'text', text: JSON.stringify({ devices: Array.from(reps.values()) }) }] };
    case 'rep_add_employee': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'rep_remove_employee': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'rep_add_fingerprint': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'rep_get_punches': return { content: [{ type: 'text', text: JSON.stringify({ punches: [] }) }] };
    case 'rep_export_afd': return { content: [{ type: 'text', text: JSON.stringify({ afd_content: '' }) }] };
    case 'rep_sync_employees': return { content: [{ type: 'text', text: JSON.stringify({ synced: 0, failed: 0 }) }] };
    case 'rep_get_status': return { content: [{ type: 'text', text: JSON.stringify({ online: true, last_sync: null }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
