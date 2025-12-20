/**
 * MCP PIX - API PIX do Banco Central
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-pix', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'pix_create_charge',
      description: 'Cria cobrança PIX (QR Code)',
      inputSchema: {
        type: 'object',
        properties: {
          amount: { type: 'number', description: 'Valor em reais' },
          payer_cpf: { type: 'string' },
          payer_name: { type: 'string' },
          description: { type: 'string' },
          expiration_seconds: { type: 'number' },
          txid: { type: 'string', description: 'ID único da transação' },
        },
        required: ['amount'],
      },
    },
    {
      name: 'pix_create_static',
      description: 'Cria QR Code estático',
      inputSchema: {
        type: 'object',
        properties: {
          pix_key: { type: 'string' },
          amount: { type: 'number' },
          description: { type: 'string' },
          merchant_name: { type: 'string' },
          merchant_city: { type: 'string' },
        },
        required: ['pix_key'],
      },
    },
    {
      name: 'pix_get_charge',
      description: 'Consulta cobrança PIX',
      inputSchema: {
        type: 'object',
        properties: {
          txid: { type: 'string' },
        },
        required: ['txid'],
      },
    },
    {
      name: 'pix_list_charges',
      description: 'Lista cobranças por período',
      inputSchema: {
        type: 'object',
        properties: {
          start_date: { type: 'string' },
          end_date: { type: 'string' },
          status: { type: 'string', enum: ['ATIVA', 'CONCLUIDA', 'REMOVIDA_PELO_USUARIO_RECEBEDOR'] },
        },
        required: ['start_date', 'end_date'],
      },
    },
    {
      name: 'pix_get_payment',
      description: 'Consulta pagamento recebido',
      inputSchema: {
        type: 'object',
        properties: {
          e2eid: { type: 'string', description: 'End-to-end ID' },
        },
        required: ['e2eid'],
      },
    },
    {
      name: 'pix_list_payments',
      description: 'Lista pagamentos recebidos',
      inputSchema: {
        type: 'object',
        properties: {
          start_date: { type: 'string' },
          end_date: { type: 'string' },
          txid: { type: 'string' },
        },
        required: ['start_date', 'end_date'],
      },
    },
    {
      name: 'pix_refund',
      description: 'Solicita devolução PIX',
      inputSchema: {
        type: 'object',
        properties: {
          e2eid: { type: 'string' },
          amount: { type: 'number' },
          reason: { type: 'string' },
        },
        required: ['e2eid'],
      },
    },
    {
      name: 'pix_configure_webhook',
      description: 'Configura webhook para notificações',
      inputSchema: {
        type: 'object',
        properties: {
          webhook_url: { type: 'string' },
          pix_key: { type: 'string' },
        },
        required: ['webhook_url', 'pix_key'],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'pix_create_charge': {
      const txid = args.txid || `TX${Date.now()}`;
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            txid,
            status: 'ATIVA',
            qr_code: '00020126...',
            qr_code_base64: '',
            copy_paste: '00020126...',
            expires_at: new Date(Date.now() + (args.expiration_seconds || 3600) * 1000).toISOString()
          })
        }]
      };
    }

    case 'pix_create_static': {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            qr_code: '00020126...',
            qr_code_base64: '',
            copy_paste: '00020126...'
          })
        }]
      };
    }

    case 'pix_get_charge': {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            txid: args.txid,
            status: 'ATIVA',
            amount: 0,
            payer: null,
            created_at: ''
          })
        }]
      };
    }

    case 'pix_list_charges': {
      return { content: [{ type: 'text', text: JSON.stringify({ charges: [], total: 0 }) }] };
    }

    case 'pix_get_payment': {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            e2eid: args.e2eid,
            txid: '',
            amount: 0,
            payer: {},
            received_at: ''
          })
        }]
      };
    }

    case 'pix_list_payments': {
      return { content: [{ type: 'text', text: JSON.stringify({ payments: [], total: 0 }) }] };
    }

    case 'pix_refund': {
      return { content: [{ type: 'text', text: JSON.stringify({ success: true, refund_id: '' }) }] };
    }

    case 'pix_configure_webhook': {
      return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    }

    default:
      return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
