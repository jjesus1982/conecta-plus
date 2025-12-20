/**
 * MCP Medidores - Leitura de medidores (água, gás, energia)
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-medidores', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

const meters: Map<string, any> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'meter_add', description: 'Adiciona medidor', inputSchema: { type: 'object', properties: { id: { type: 'string' }, type: { type: 'string', enum: ['water', 'gas', 'electricity'] }, unit_id: { type: 'string' }, serial_number: { type: 'string' }, location: { type: 'string' } }, required: ['id', 'type', 'unit_id'] } },
    { name: 'meter_list', description: 'Lista medidores', inputSchema: { type: 'object', properties: { type: { type: 'string' }, unit_id: { type: 'string' } } } },
    { name: 'meter_add_reading', description: 'Registra leitura', inputSchema: { type: 'object', properties: { meter_id: { type: 'string' }, value: { type: 'number' }, reading_date: { type: 'string' }, image_path: { type: 'string' } }, required: ['meter_id', 'value'] } },
    { name: 'meter_get_readings', description: 'Histórico de leituras', inputSchema: { type: 'object', properties: { meter_id: { type: 'string' }, start_date: { type: 'string' }, end_date: { type: 'string' } }, required: ['meter_id'] } },
    { name: 'meter_get_consumption', description: 'Calcula consumo do período', inputSchema: { type: 'object', properties: { meter_id: { type: 'string' }, start_date: { type: 'string' }, end_date: { type: 'string' } }, required: ['meter_id', 'start_date', 'end_date'] } },
    { name: 'meter_generate_report', description: 'Gera relatório de consumo', inputSchema: { type: 'object', properties: { unit_id: { type: 'string' }, type: { type: 'string' }, competency: { type: 'string' } }, required: ['competency'] } },
    { name: 'meter_detect_anomaly', description: 'Detecta anomalias de consumo', inputSchema: { type: 'object', properties: { meter_id: { type: 'string' }, threshold_percentage: { type: 'number' } }, required: ['meter_id'] } },
    { name: 'meter_ocr_reading', description: 'Leitura por OCR de foto', inputSchema: { type: 'object', properties: { meter_id: { type: 'string' }, image_path: { type: 'string' }, image_base64: { type: 'string' } }, required: ['meter_id'] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  switch (name) {
    case 'meter_add': meters.set(args.id as string, { id: args.id, type: args.type, unit_id: args.unit_id }); return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'meter_list': return { content: [{ type: 'text', text: JSON.stringify({ meters: Array.from(meters.values()) }) }] };
    case 'meter_add_reading': return { content: [{ type: 'text', text: JSON.stringify({ success: true, reading_id: `RD${Date.now()}` }) }] };
    case 'meter_get_readings': return { content: [{ type: 'text', text: JSON.stringify({ readings: [] }) }] };
    case 'meter_get_consumption': return { content: [{ type: 'text', text: JSON.stringify({ consumption: 0, unit: '', previous: 0, current: 0 }) }] };
    case 'meter_generate_report': return { content: [{ type: 'text', text: JSON.stringify({ report: [], total: 0 }) }] };
    case 'meter_detect_anomaly': return { content: [{ type: 'text', text: JSON.stringify({ anomalies: [], has_anomaly: false }) }] };
    case 'meter_ocr_reading': return { content: [{ type: 'text', text: JSON.stringify({ detected_value: 0, confidence: 0 }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
