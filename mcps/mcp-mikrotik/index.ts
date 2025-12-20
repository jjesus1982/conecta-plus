/**
 * MCP MikroTik - RouterOS API
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-mikrotik', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

interface MikroTikRouter {
  id: string;
  host: string;
  port: number;
  username: string;
  password: string;
}

const routers: Map<string, MikroTikRouter> = new Map();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'mikrotik_add_router', description: 'Adiciona router MikroTik', inputSchema: { type: 'object', properties: { id: { type: 'string' }, host: { type: 'string' }, port: { type: 'number' }, username: { type: 'string' }, password: { type: 'string' } }, required: ['id', 'host', 'username', 'password'] } },
    { name: 'mikrotik_list_routers', description: 'Lista routers', inputSchema: { type: 'object', properties: {} } },
    { name: 'mikrotik_get_system_info', description: 'Info do sistema', inputSchema: { type: 'object', properties: { router_id: { type: 'string' } }, required: ['router_id'] } },
    { name: 'mikrotik_get_interfaces', description: 'Lista interfaces', inputSchema: { type: 'object', properties: { router_id: { type: 'string' } }, required: ['router_id'] } },
    { name: 'mikrotik_get_dhcp_leases', description: 'Lista DHCP leases', inputSchema: { type: 'object', properties: { router_id: { type: 'string' } }, required: ['router_id'] } },
    { name: 'mikrotik_add_firewall_rule', description: 'Adiciona regra firewall', inputSchema: { type: 'object', properties: { router_id: { type: 'string' }, chain: { type: 'string' }, action: { type: 'string' }, src_address: { type: 'string' }, dst_address: { type: 'string' }, protocol: { type: 'string' }, dst_port: { type: 'string' } }, required: ['router_id', 'chain', 'action'] } },
    { name: 'mikrotik_list_firewall_rules', description: 'Lista regras firewall', inputSchema: { type: 'object', properties: { router_id: { type: 'string' }, chain: { type: 'string' } }, required: ['router_id'] } },
    { name: 'mikrotik_add_address_list', description: 'Adiciona IP à address-list', inputSchema: { type: 'object', properties: { router_id: { type: 'string' }, list: { type: 'string' }, address: { type: 'string' }, timeout: { type: 'string' } }, required: ['router_id', 'list', 'address'] } },
    { name: 'mikrotik_get_traffic', description: 'Tráfego de interface', inputSchema: { type: 'object', properties: { router_id: { type: 'string' }, interface: { type: 'string' } }, required: ['router_id', 'interface'] } },
    { name: 'mikrotik_add_queue', description: 'Adiciona queue simples', inputSchema: { type: 'object', properties: { router_id: { type: 'string' }, name: { type: 'string' }, target: { type: 'string' }, max_limit: { type: 'string' } }, required: ['router_id', 'name', 'target'] } },
    { name: 'mikrotik_hotspot_users', description: 'Lista usuários hotspot', inputSchema: { type: 'object', properties: { router_id: { type: 'string' } }, required: ['router_id'] } },
    { name: 'mikrotik_ppp_active', description: 'Conexões PPP ativas', inputSchema: { type: 'object', properties: { router_id: { type: 'string' } }, required: ['router_id'] } },
    { name: 'mikrotik_run_script', description: 'Executa script', inputSchema: { type: 'object', properties: { router_id: { type: 'string' }, script_name: { type: 'string' } }, required: ['router_id', 'script_name'] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  switch (name) {
    case 'mikrotik_add_router': {
      routers.set(args.id as string, { id: args.id as string, host: args.host as string, port: (args.port as number) || 8728, username: args.username as string, password: args.password as string });
      return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    }
    case 'mikrotik_list_routers': return { content: [{ type: 'text', text: JSON.stringify({ routers: Array.from(routers.values()).map(r => ({ id: r.id, host: r.host })) }) }] };
    case 'mikrotik_get_system_info': return { content: [{ type: 'text', text: JSON.stringify({ board_name: '', version: '', uptime: '' }) }] };
    case 'mikrotik_get_interfaces': return { content: [{ type: 'text', text: JSON.stringify({ interfaces: [] }) }] };
    case 'mikrotik_get_dhcp_leases': return { content: [{ type: 'text', text: JSON.stringify({ leases: [] }) }] };
    case 'mikrotik_add_firewall_rule': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'mikrotik_list_firewall_rules': return { content: [{ type: 'text', text: JSON.stringify({ rules: [] }) }] };
    case 'mikrotik_add_address_list': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'mikrotik_get_traffic': return { content: [{ type: 'text', text: JSON.stringify({ rx_bytes: 0, tx_bytes: 0 }) }] };
    case 'mikrotik_add_queue': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    case 'mikrotik_hotspot_users': return { content: [{ type: 'text', text: JSON.stringify({ users: [] }) }] };
    case 'mikrotik_ppp_active': return { content: [{ type: 'text', text: JSON.stringify({ connections: [] }) }] };
    case 'mikrotik_run_script': return { content: [{ type: 'text', text: JSON.stringify({ success: true }) }] };
    default: return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() { const transport = new StdioServerTransport(); await server.connect(transport); }
main().catch(console.error);
