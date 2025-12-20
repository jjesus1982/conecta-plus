/**
 * MCP NFS-e - Nota Fiscal de Serviço Eletrônica
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-nfse', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'nfse_emit',
      description: 'Emite NFS-e',
      inputSchema: {
        type: 'object',
        properties: {
          service_code: { type: 'string', description: 'Código do serviço LC 116' },
          description: { type: 'string' },
          amount: { type: 'number' },
          client_document: { type: 'string', description: 'CPF/CNPJ do tomador' },
          client_name: { type: 'string' },
          client_address: { type: 'object' },
          iss_retention: { type: 'boolean' },
          deductions: { type: 'number' },
        },
        required: ['service_code', 'description', 'amount', 'client_document', 'client_name'],
      },
    },
    {
      name: 'nfse_cancel',
      description: 'Cancela NFS-e',
      inputSchema: {
        type: 'object',
        properties: {
          nfse_number: { type: 'string' },
          reason: { type: 'string' },
        },
        required: ['nfse_number', 'reason'],
      },
    },
    {
      name: 'nfse_get',
      description: 'Consulta NFS-e',
      inputSchema: {
        type: 'object',
        properties: {
          nfse_number: { type: 'string' },
          rps_number: { type: 'string' },
        },
      },
    },
    {
      name: 'nfse_list',
      description: 'Lista NFS-e por período',
      inputSchema: {
        type: 'object',
        properties: {
          start_date: { type: 'string' },
          end_date: { type: 'string' },
          client_document: { type: 'string' },
          status: { type: 'string', enum: ['emitida', 'cancelada'] },
        },
        required: ['start_date', 'end_date'],
      },
    },
    {
      name: 'nfse_get_pdf',
      description: 'Obtém PDF da NFS-e',
      inputSchema: {
        type: 'object',
        properties: {
          nfse_number: { type: 'string' },
        },
        required: ['nfse_number'],
      },
    },
    {
      name: 'nfse_get_xml',
      description: 'Obtém XML da NFS-e',
      inputSchema: {
        type: 'object',
        properties: {
          nfse_number: { type: 'string' },
        },
        required: ['nfse_number'],
      },
    },
    {
      name: 'nfse_batch_emit',
      description: 'Emite lote de NFS-e',
      inputSchema: {
        type: 'object',
        properties: {
          notas: { type: 'array', items: { type: 'object' } },
        },
        required: ['notas'],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'nfse_emit': {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            success: true,
            nfse_number: `NF${Date.now()}`,
            verification_code: '',
            issued_at: new Date().toISOString()
          })
        }]
      };
    }
    case 'nfse_cancel': return { content: [{ type: 'text', text: JSON.stringify({ success: true, cancelled_at: new Date().toISOString() }) }] };
    case 'nfse_get': return { content: [{ type: 'text', text: JSON.stringify({ nfse: null }) }] };
    case 'nfse_list': return { content: [{ type: 'text', text: JSON.stringify({ notas: [], total: 0 }) }] };
    case 'nfse_get_pdf': return { content: [{ type: 'text', text: JSON.stringify({ pdf_url: '', pdf_base64: '' }) }] };
    case 'nfse_get_xml': return { content: [{ type: 'text', text: JSON.stringify({ xml: '' }) }] };
    case 'nfse_batch_emit': return { content: [{ type: 'text', text: JSON.stringify({ emitted: 0, failed: 0 }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
