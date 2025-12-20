/**
 * MCP Asterisk - PBX VoIP
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-asterisk', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

const pbxs: Map<string, any> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'asterisk_add_pbx', description: 'Adiciona PBX Asterisk', inputSchema: { type: 'object', properties: { id: { type: 'string' }, host: { type: 'string' }, ami_port: { type: 'number' }, username: { type: 'string' }, secret: { type: 'string' } }, required: ['id', 'host', 'username', 'secret'] } },
    { name: 'asterisk_list_pbxs', description: 'Lista PBXs', inputSchema: { type: 'object', properties: {} } },
    { name: 'asterisk_list_extensions', description: 'Lista ramais', inputSchema: { type: 'object', properties: { pbx_id: { type: 'string' } }, required: ['pbx_id'] } },
    { name: 'asterisk_get_extension_status', description: 'Status do ramal', inputSchema: { type: 'object', properties: { pbx_id: { type: 'string' }, extension: { type: 'string' } }, required: ['pbx_id', 'extension'] } },
    { name: 'asterisk_originate_call', description: 'Origina chamada', inputSchema: { type: 'object', properties: { pbx_id: { type: 'string' }, channel: { type: 'string' }, extension: { type: 'string' }, context: { type: 'string' }, caller_id: { type: 'string' } }, required: ['pbx_id', 'channel', 'extension'] } },
    { name: 'asterisk_hangup', description: 'Desliga chamada', inputSchema: { type: 'object', properties: { pbx_id: { type: 'string' }, channel: { type: 'string' } }, required: ['pbx_id', 'channel'] } },
    { name: 'asterisk_get_active_calls', description: 'Chamadas ativas', inputSchema: { type: 'object', properties: { pbx_id: { type: 'string' } }, required: ['pbx_id'] } },
    { name: 'asterisk_get_queues', description: 'Status das filas', inputSchema: { type: 'object', properties: { pbx_id: { type: 'string' } }, required: ['pbx_id'] } },
    { name: 'asterisk_queue_add', description: 'Adiciona agente à fila', inputSchema: { type: 'object', properties: { pbx_id: { type: 'string' }, queue: { type: 'string' }, interface: { type: 'string' } }, required: ['pbx_id', 'queue', 'interface'] } },
    { name: 'asterisk_queue_remove', description: 'Remove agente da fila', inputSchema: { type: 'object', properties: { pbx_id: { type: 'string' }, queue: { type: 'string' }, interface: { type: 'string' } }, required: ['pbx_id', 'queue', 'interface'] } },
    { name: 'asterisk_play_sound', description: 'Toca áudio no canal', inputSchema: { type: 'object', properties: { pbx_id: { type: 'string' }, channel: { type: 'string' }, sound: { type: 'string' } }, required: ['pbx_id', 'channel', 'sound'] } },
    { name: 'asterisk_get_cdr', description: 'Registros de chamadas', inputSchema: { type: 'object', properties: { pbx_id: { type: 'string' }, start_date: { type: 'string' }, end_date: { type: 'string' }, extension: { type: 'string' } }, required: ['pbx_id'] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  switch (name) {
    case 'asterisk_add_pbx': pbxs.set(args.id as string, { id: args.id, host: args.host, ami_port: args.ami_port || 5038 }); return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'asterisk_list_pbxs': return { content: [{ type: 'text', text: JSON.stringify({ pbxs: Array.from(pbxs.values()) }) }] };
    case 'asterisk_list_extensions': return { content: [{ type: 'text', text: JSON.stringify({ extensions: [] }) }] };
    case 'asterisk_get_extension_status': return { content: [{ type: 'text', text: JSON.stringify({ extension: args.extension, status: 'idle' }) }] };
    case 'asterisk_originate_call': return { content: [{ type: 'text', text: JSON.stringify({ success: true, action_id: Date.now().toString() }) }] };
    case 'asterisk_hangup': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'asterisk_get_active_calls': return { content: [{ type: 'text', text: JSON.stringify({ calls: [] }) }] };
    case 'asterisk_get_queues': return { content: [{ type: 'text', text: JSON.stringify({ queues: [] }) }] };
    case 'asterisk_queue_add': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'asterisk_queue_remove': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'asterisk_play_sound': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'asterisk_get_cdr': return { content: [{ type: 'text', text: JSON.stringify({ records: [] }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
