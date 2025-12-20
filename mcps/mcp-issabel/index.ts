/**
 * MCP Issabel - PBX (fork Elastix)
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-issabel', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

const servers: Map<string, any> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'issabel_add_server', description: 'Adiciona servidor Issabel', inputSchema: { type: 'object', properties: { id: { type: 'string' }, url: { type: 'string' }, username: { type: 'string' }, password: { type: 'string' } }, required: ['id', 'url', 'username', 'password'] } },
    { name: 'issabel_list_servers', description: 'Lista servidores', inputSchema: { type: 'object', properties: {} } },
    { name: 'issabel_list_extensions', description: 'Lista ramais', inputSchema: { type: 'object', properties: { server_id: { type: 'string' } }, required: ['server_id'] } },
    { name: 'issabel_create_extension', description: 'Cria ramal', inputSchema: { type: 'object', properties: { server_id: { type: 'string' }, extension: { type: 'string' }, name: { type: 'string' }, password: { type: 'string' } }, required: ['server_id', 'extension', 'name'] } },
    { name: 'issabel_delete_extension', description: 'Remove ramal', inputSchema: { type: 'object', properties: { server_id: { type: 'string' }, extension: { type: 'string' } }, required: ['server_id', 'extension'] } },
    { name: 'issabel_get_cdr', description: 'Registros de chamadas', inputSchema: { type: 'object', properties: { server_id: { type: 'string' }, start_date: { type: 'string' }, end_date: { type: 'string' } }, required: ['server_id'] } },
    { name: 'issabel_list_trunks', description: 'Lista troncos', inputSchema: { type: 'object', properties: { server_id: { type: 'string' } }, required: ['server_id'] } },
    { name: 'issabel_list_queues', description: 'Lista filas', inputSchema: { type: 'object', properties: { server_id: { type: 'string' } }, required: ['server_id'] } },
    { name: 'issabel_get_voicemails', description: 'Lista voicemails', inputSchema: { type: 'object', properties: { server_id: { type: 'string' }, extension: { type: 'string' } }, required: ['server_id'] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  switch (name) {
    case 'issabel_add_server': servers.set(args.id as string, { id: args.id, url: args.url }); return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'issabel_list_servers': return { content: [{ type: 'text', text: JSON.stringify({ servers: Array.from(servers.values()) }) }] };
    case 'issabel_list_extensions': return { content: [{ type: 'text', text: JSON.stringify({ extensions: [] }) }] };
    case 'issabel_create_extension': return { content: [{ type: 'text', text: JSON.stringify({ success: true, extension: args.extension }) }] };
    case 'issabel_delete_extension': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'issabel_get_cdr': return { content: [{ type: 'text', text: JSON.stringify({ records: [] }) }] };
    case 'issabel_list_trunks': return { content: [{ type: 'text', text: JSON.stringify({ trunks: [] }) }] };
    case 'issabel_list_queues': return { content: [{ type: 'text', text: JSON.stringify({ queues: [] }) }] };
    case 'issabel_get_voicemails': return { content: [{ type: 'text', text: JSON.stringify({ voicemails: [] }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
