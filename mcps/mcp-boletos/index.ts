/**
 * MCP Boletos - Geração e gestão de boletos bancários
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-boletos', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'boleto_generate',
      description: 'Gera boleto bancário',
      inputSchema: {
        type: 'object',
        properties: {
          bank_code: { type: 'string', enum: ['001', '033', '104', '237', '341', '756'], description: 'Código do banco' },
          amount: { type: 'number', description: 'Valor em reais' },
          due_date: { type: 'string', description: 'Data vencimento (YYYY-MM-DD)' },
          payer_name: { type: 'string' },
          payer_document: { type: 'string', description: 'CPF ou CNPJ' },
          payer_address: { type: 'object' },
          description: { type: 'string' },
          fine_percentage: { type: 'number' },
          interest_percentage: { type: 'number' },
          discount_amount: { type: 'number' },
          discount_date: { type: 'string' },
        },
        required: ['bank_code', 'amount', 'due_date', 'payer_name', 'payer_document'],
      },
    },
    {
      name: 'boleto_register',
      description: 'Registra boleto no banco',
      inputSchema: {
        type: 'object',
        properties: {
          boleto_id: { type: 'string' },
        },
        required: ['boleto_id'],
      },
    },
    {
      name: 'boleto_get_status',
      description: 'Consulta status do boleto',
      inputSchema: {
        type: 'object',
        properties: {
          boleto_id: { type: 'string' },
          barcode: { type: 'string' },
        },
      },
    },
    {
      name: 'boleto_cancel',
      description: 'Cancela/baixa boleto',
      inputSchema: {
        type: 'object',
        properties: {
          boleto_id: { type: 'string' },
          reason: { type: 'string' },
        },
        required: ['boleto_id'],
      },
    },
    {
      name: 'boleto_list',
      description: 'Lista boletos por período/status',
      inputSchema: {
        type: 'object',
        properties: {
          start_date: { type: 'string' },
          end_date: { type: 'string' },
          status: { type: 'string', enum: ['pending', 'paid', 'overdue', 'cancelled'] },
          payer_document: { type: 'string' },
        },
      },
    },
    {
      name: 'boleto_get_pdf',
      description: 'Gera PDF do boleto',
      inputSchema: {
        type: 'object',
        properties: {
          boleto_id: { type: 'string' },
          format: { type: 'string', enum: ['a4', 'carne', 'ficha'] },
        },
        required: ['boleto_id'],
      },
    },
    {
      name: 'boleto_batch_generate',
      description: 'Gera lote de boletos',
      inputSchema: {
        type: 'object',
        properties: {
          boletos: { type: 'array', items: { type: 'object' } },
          competency: { type: 'string', description: 'Competência (YYYY-MM)' },
        },
        required: ['boletos'],
      },
    },
    {
      name: 'boleto_process_return',
      description: 'Processa arquivo retorno CNAB',
      inputSchema: {
        type: 'object',
        properties: {
          file_path: { type: 'string' },
          file_content: { type: 'string' },
        },
      },
    },
    {
      name: 'boleto_generate_remittance',
      description: 'Gera arquivo remessa CNAB',
      inputSchema: {
        type: 'object',
        properties: {
          boleto_ids: { type: 'array', items: { type: 'string' } },
          format: { type: 'string', enum: ['cnab240', 'cnab400'] },
        },
        required: ['boleto_ids'],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'boleto_generate': {
      const boleto_id = `BOL${Date.now()}`;
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            success: true,
            boleto_id,
            barcode: '00000.00000 00000.000000 00000.000000 0 00000000000000',
            digitable_line: '00000000000000000000000000000000000000000000000',
            amount: args.amount,
            due_date: args.due_date
          })
        }]
      };
    }

    case 'boleto_register': {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            success: true,
            boleto_id: args.boleto_id,
            registered_at: new Date().toISOString(),
            bank_number: ''
          })
        }]
      };
    }

    case 'boleto_get_status': {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            boleto_id: args.boleto_id,
            status: 'pending',
            amount: 0,
            due_date: '',
            paid_at: null,
            paid_amount: null
          })
        }]
      };
    }

    case 'boleto_cancel': {
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, cancelled: true }) }] };
    }

    case 'boleto_list': {
      return { content: [{ type: 'text', text: JSON.stringify({ boletos: [], total: 0 }) }] };
    }

    case 'boleto_get_pdf': {
      return { content: [{ type: 'text', text: JSON.stringify({ pdf_url: '', pdf_base64: '' }) }] };
    }

    case 'boleto_batch_generate': {
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, generated: 0, failed: 0 }) }] };
    }

    case 'boleto_process_return': {
      return { content: [{ type: 'text', text: JSON.stringify({ processed: 0, payments: [] }) }] };
    }

    case 'boleto_generate_remittance': {
      return { content: [{ type: 'text', text: JSON.stringify({ file_content: '', records: 0 }) }] };
    }

    default:
      return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
