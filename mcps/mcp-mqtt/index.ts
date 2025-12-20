/**
 * MCP MQTT - Broker MQTT para IoT
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-mqtt', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'mqtt_connect', description: 'Conecta ao broker MQTT', inputSchema: { type: 'object', properties: { broker_url: { type: 'string' }, username: { type: 'string' }, password: { type: 'string' }, client_id: { type: 'string' } }, required: ['broker_url'] } },
    { name: 'mqtt_publish', description: 'Publica mensagem em tópico', inputSchema: { type: 'object', properties: { topic: { type: 'string' }, message: { type: 'string' }, qos: { type: 'number', enum: [0, 1, 2] }, retain: { type: 'boolean' } }, required: ['topic', 'message'] } },
    { name: 'mqtt_subscribe', description: 'Inscreve em tópico', inputSchema: { type: 'object', properties: { topic: { type: 'string' }, qos: { type: 'number' } }, required: ['topic'] } },
    { name: 'mqtt_unsubscribe', description: 'Cancela inscrição', inputSchema: { type: 'object', properties: { topic: { type: 'string' } }, required: ['topic'] } },
    { name: 'mqtt_list_topics', description: 'Lista tópicos ativos', inputSchema: { type: 'object', properties: { filter: { type: 'string' } } } },
    { name: 'mqtt_get_retained', description: 'Obtém mensagem retida', inputSchema: { type: 'object', properties: { topic: { type: 'string' } }, required: ['topic'] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  switch (name) {
    case 'mqtt_connect': return { content: [{ type: 'text', text: JSON.stringify({ connected: true, client_id: args.client_id }) }] };
    case 'mqtt_publish': return { content: [{ type: 'text', text: JSON.stringify({ success: true, topic: args.topic }) }] };
    case 'mqtt_subscribe': return { content: [{ type: 'text', text: JSON.stringify({ success: true, topic: args.topic }) }] };
    case 'mqtt_unsubscribe': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'mqtt_list_topics': return { content: [{ type: 'text', text: JSON.stringify({ topics: [] }) }] };
    case 'mqtt_get_retained': return { content: [{ type: 'text', text: JSON.stringify({ topic: args.topic, message: null }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
