/**
 * MCP Guardian Notifications - Sistema de Notificacoes Multi-Canal
 * Conecta Plus - Plataforma de Gestao Condominial
 *
 * Canais suportados:
 * - SMS (via Twilio, Zenvia, etc)
 * - Email (SMTP, SendGrid, etc)
 * - Push Notifications (Firebase, OneSignal)
 * - WhatsApp (Twilio, Z-API, Evolution)
 * - Chamada Telefonica (Twilio, Asterisk)
 * - Intercomunicador (SIP, WebRTC)
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  {
    name: 'mcp-guardian-notifications',
    version: '2.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// === Tipos ===

type NotificationChannel = 'sms' | 'email' | 'push' | 'whatsapp' | 'call' | 'intercom' | 'dashboard';
type NotificationPriority = 'low' | 'normal' | 'high' | 'critical';
type NotificationStatus = 'pending' | 'sent' | 'delivered' | 'failed' | 'read';

interface ChannelConfig {
  enabled: boolean;
  provider: string;
  credentials: Record<string, string>;
  settings: Record<string, unknown>;
}

interface NotificationTemplate {
  id: string;
  name: string;
  channels: NotificationChannel[];
  subject?: string;
  body: string;
  variables: string[];
}

interface Notification {
  id: string;
  channel: NotificationChannel;
  recipient: string;
  subject?: string;
  message: string;
  priority: NotificationPriority;
  status: NotificationStatus;
  sentAt?: string;
  deliveredAt?: string;
  readAt?: string;
  error?: string;
  metadata: Record<string, unknown>;
}

interface Contact {
  id: string;
  name: string;
  role: string;
  phone?: string;
  email?: string;
  pushToken?: string;
  whatsapp?: string;
  preferences: {
    channels: NotificationChannel[];
    quiet_hours?: { start: string; end: string };
  };
}

interface NotificationGroup {
  id: string;
  name: string;
  contacts: string[];
  escalation_delay_minutes: number;
}

// === Estado ===

const channelConfigs: Map<NotificationChannel, ChannelConfig> = new Map();
const templates: Map<string, NotificationTemplate> = new Map();
const notifications: Map<string, Notification> = new Map();
const contacts: Map<string, Contact> = new Map();
const groups: Map<string, NotificationGroup> = new Map();

// Inicializar configuracoes padrao
channelConfigs.set('sms', { enabled: false, provider: 'twilio', credentials: {}, settings: {} });
channelConfigs.set('email', { enabled: true, provider: 'smtp', credentials: {}, settings: {} });
channelConfigs.set('push', { enabled: true, provider: 'firebase', credentials: {}, settings: {} });
channelConfigs.set('whatsapp', { enabled: false, provider: 'evolution', credentials: {}, settings: {} });
channelConfigs.set('call', { enabled: false, provider: 'asterisk', credentials: {}, settings: {} });
channelConfigs.set('intercom', { enabled: true, provider: 'sip', credentials: {}, settings: {} });
channelConfigs.set('dashboard', { enabled: true, provider: 'internal', credentials: {}, settings: {} });

// Templates padrao
templates.set('alert_security', {
  id: 'alert_security',
  name: 'Alerta de Seguranca',
  channels: ['push', 'sms', 'whatsapp'],
  subject: 'ALERTA: {alert_type}',
  body: '{severity} - {title}\nLocal: {location}\nHorario: {timestamp}\n\n{description}',
  variables: ['alert_type', 'severity', 'title', 'location', 'timestamp', 'description'],
});

templates.set('incident_created', {
  id: 'incident_created',
  name: 'Incidente Criado',
  channels: ['push', 'email', 'whatsapp'],
  subject: 'Incidente {incident_id}: {title}',
  body: 'Novo incidente detectado:\n\nID: {incident_id}\nTipo: {type}\nSeveridade: {severity}\nLocal: {location}\n\n{description}',
  variables: ['incident_id', 'type', 'severity', 'title', 'location', 'description'],
});

templates.set('incident_escalated', {
  id: 'incident_escalated',
  name: 'Incidente Escalonado',
  channels: ['call', 'sms', 'push'],
  subject: 'ESCALONAMENTO: Incidente {incident_id}',
  body: 'Incidente {incident_id} foi escalonado para nivel {level}.\n\nTitulo: {title}\nLocal: {location}\n\nAcao imediata necessaria.',
  variables: ['incident_id', 'level', 'title', 'location'],
});

templates.set('emergency', {
  id: 'emergency',
  name: 'Emergencia',
  channels: ['call', 'intercom', 'sms', 'push', 'whatsapp'],
  subject: 'EMERGENCIA: {type}',
  body: 'ATENCAO! Emergencia em andamento.\n\nTipo: {type}\nLocal: {location}\n\n{instructions}',
  variables: ['type', 'location', 'instructions'],
});

templates.set('access_denied', {
  id: 'access_denied',
  name: 'Acesso Negado',
  channels: ['push', 'dashboard'],
  subject: 'Acesso Negado: {access_point}',
  body: 'Tentativa de acesso negada.\n\nLocal: {access_point}\nHorario: {timestamp}\nMotivo: {reason}',
  variables: ['access_point', 'timestamp', 'reason'],
});

// === Helpers ===

function generateId(prefix: string): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 8);
  return `${prefix}_${timestamp}_${random}`;
}

function parseTemplate(template: string, variables: Record<string, string>): string {
  let result = template;
  for (const [key, value] of Object.entries(variables)) {
    result = result.replace(new RegExp(`\\{${key}\\}`, 'g'), value);
  }
  return result;
}

async function sendNotification(
  channel: NotificationChannel,
  recipient: string,
  subject: string | undefined,
  message: string,
  priority: NotificationPriority
): Promise<Notification> {
  const config = channelConfigs.get(channel);

  const notification: Notification = {
    id: generateId('NOT'),
    channel,
    recipient,
    subject,
    message,
    priority,
    status: 'pending',
    metadata: {},
  };

  if (!config?.enabled) {
    notification.status = 'failed';
    notification.error = `Canal ${channel} nao esta habilitado`;
    notifications.set(notification.id, notification);
    return notification;
  }

  // Simular envio (em producao, cada canal teria sua implementacao)
  try {
    switch (channel) {
      case 'sms':
        // Integrar com Twilio, Zenvia, etc
        break;
      case 'email':
        // Integrar com SMTP, SendGrid, etc
        break;
      case 'push':
        // Integrar com Firebase, OneSignal, etc
        break;
      case 'whatsapp':
        // Integrar com Evolution, Z-API, etc
        break;
      case 'call':
        // Integrar com Asterisk, Twilio Voice, etc
        break;
      case 'intercom':
        // Integrar com sistema SIP
        break;
      case 'dashboard':
        // Enviar para WebSocket
        break;
    }

    notification.status = 'sent';
    notification.sentAt = new Date().toISOString();
  } catch (error) {
    notification.status = 'failed';
    notification.error = (error as Error).message;
  }

  notifications.set(notification.id, notification);
  return notification;
}

// === Tools Definition ===

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    // === Channel Configuration ===
    {
      name: 'notification_configure_channel',
      description: 'Configura um canal de notificacao',
      inputSchema: {
        type: 'object',
        properties: {
          channel: { type: 'string', enum: ['sms', 'email', 'push', 'whatsapp', 'call', 'intercom', 'dashboard'] },
          enabled: { type: 'boolean' },
          provider: { type: 'string' },
          credentials: { type: 'object' },
          settings: { type: 'object' },
        },
        required: ['channel'],
      },
    },
    {
      name: 'notification_list_channels',
      description: 'Lista configuracao de todos os canais',
      inputSchema: { type: 'object', properties: {} },
    },
    {
      name: 'notification_test_channel',
      description: 'Testa um canal de notificacao',
      inputSchema: {
        type: 'object',
        properties: {
          channel: { type: 'string', enum: ['sms', 'email', 'push', 'whatsapp', 'call', 'intercom'] },
          recipient: { type: 'string', description: 'Destinatario para teste' },
        },
        required: ['channel', 'recipient'],
      },
    },

    // === Send Notifications ===
    {
      name: 'notification_send',
      description: 'Envia uma notificacao',
      inputSchema: {
        type: 'object',
        properties: {
          channel: { type: 'string', enum: ['sms', 'email', 'push', 'whatsapp', 'call', 'intercom', 'dashboard'] },
          recipient: { type: 'string', description: 'Destinatario (telefone, email, token, etc)' },
          subject: { type: 'string', description: 'Assunto (para email)' },
          message: { type: 'string', description: 'Conteudo da mensagem' },
          priority: { type: 'string', enum: ['low', 'normal', 'high', 'critical'] },
        },
        required: ['channel', 'recipient', 'message'],
      },
    },
    {
      name: 'notification_send_template',
      description: 'Envia notificacao usando template',
      inputSchema: {
        type: 'object',
        properties: {
          template_id: { type: 'string', description: 'ID do template' },
          recipient: { type: 'string' },
          variables: { type: 'object', description: 'Variaveis do template' },
          priority: { type: 'string', enum: ['low', 'normal', 'high', 'critical'] },
          channels: { type: 'array', items: { type: 'string' }, description: 'Canais especificos (opcional)' },
        },
        required: ['template_id', 'recipient', 'variables'],
      },
    },
    {
      name: 'notification_broadcast',
      description: 'Envia notificacao para multiplos destinatarios',
      inputSchema: {
        type: 'object',
        properties: {
          channels: { type: 'array', items: { type: 'string' } },
          recipients: { type: 'array', items: { type: 'string' } },
          subject: { type: 'string' },
          message: { type: 'string' },
          priority: { type: 'string', enum: ['low', 'normal', 'high', 'critical'] },
        },
        required: ['channels', 'recipients', 'message'],
      },
    },
    {
      name: 'notification_send_to_group',
      description: 'Envia notificacao para um grupo',
      inputSchema: {
        type: 'object',
        properties: {
          group_id: { type: 'string' },
          template_id: { type: 'string' },
          variables: { type: 'object' },
          priority: { type: 'string', enum: ['low', 'normal', 'high', 'critical'] },
        },
        required: ['group_id', 'template_id', 'variables'],
      },
    },

    // === Templates ===
    {
      name: 'notification_list_templates',
      description: 'Lista templates disponiveis',
      inputSchema: { type: 'object', properties: {} },
    },
    {
      name: 'notification_get_template',
      description: 'Obtem detalhes de um template',
      inputSchema: {
        type: 'object',
        properties: {
          template_id: { type: 'string' },
        },
        required: ['template_id'],
      },
    },
    {
      name: 'notification_create_template',
      description: 'Cria um novo template',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          name: { type: 'string' },
          channels: { type: 'array', items: { type: 'string' } },
          subject: { type: 'string' },
          body: { type: 'string' },
          variables: { type: 'array', items: { type: 'string' } },
        },
        required: ['id', 'name', 'channels', 'body'],
      },
    },
    {
      name: 'notification_update_template',
      description: 'Atualiza um template',
      inputSchema: {
        type: 'object',
        properties: {
          template_id: { type: 'string' },
          name: { type: 'string' },
          channels: { type: 'array', items: { type: 'string' } },
          subject: { type: 'string' },
          body: { type: 'string' },
        },
        required: ['template_id'],
      },
    },

    // === Contacts ===
    {
      name: 'notification_add_contact',
      description: 'Adiciona um contato',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          name: { type: 'string' },
          role: { type: 'string' },
          phone: { type: 'string' },
          email: { type: 'string' },
          whatsapp: { type: 'string' },
          push_token: { type: 'string' },
          preferred_channels: { type: 'array', items: { type: 'string' } },
        },
        required: ['id', 'name', 'role'],
      },
    },
    {
      name: 'notification_list_contacts',
      description: 'Lista contatos cadastrados',
      inputSchema: {
        type: 'object',
        properties: {
          role: { type: 'string', description: 'Filtrar por funcao' },
        },
      },
    },
    {
      name: 'notification_remove_contact',
      description: 'Remove um contato',
      inputSchema: {
        type: 'object',
        properties: {
          contact_id: { type: 'string' },
        },
        required: ['contact_id'],
      },
    },

    // === Groups ===
    {
      name: 'notification_create_group',
      description: 'Cria um grupo de notificacao',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          name: { type: 'string' },
          contact_ids: { type: 'array', items: { type: 'string' } },
          escalation_delay: { type: 'number', description: 'Delay em minutos para escalonamento' },
        },
        required: ['id', 'name', 'contact_ids'],
      },
    },
    {
      name: 'notification_list_groups',
      description: 'Lista grupos de notificacao',
      inputSchema: { type: 'object', properties: {} },
    },
    {
      name: 'notification_add_to_group',
      description: 'Adiciona contato a um grupo',
      inputSchema: {
        type: 'object',
        properties: {
          group_id: { type: 'string' },
          contact_id: { type: 'string' },
        },
        required: ['group_id', 'contact_id'],
      },
    },

    // === History ===
    {
      name: 'notification_history',
      description: 'Obtem historico de notificacoes',
      inputSchema: {
        type: 'object',
        properties: {
          channel: { type: 'string' },
          status: { type: 'string', enum: ['pending', 'sent', 'delivered', 'failed', 'read'] },
          recipient: { type: 'string' },
          limit: { type: 'number' },
        },
      },
    },
    {
      name: 'notification_get_status',
      description: 'Obtem status de uma notificacao',
      inputSchema: {
        type: 'object',
        properties: {
          notification_id: { type: 'string' },
        },
        required: ['notification_id'],
      },
    },

    // === Emergency ===
    {
      name: 'notification_emergency_broadcast',
      description: 'Envia notificacao de emergencia para todos os canais',
      inputSchema: {
        type: 'object',
        properties: {
          type: { type: 'string', enum: ['fire', 'intrusion', 'medical', 'evacuation', 'lockdown'] },
          location: { type: 'string' },
          instructions: { type: 'string' },
        },
        required: ['type', 'location'],
      },
    },
    {
      name: 'notification_intercom_announce',
      description: 'Faz anuncio no sistema de intercomunicacao',
      inputSchema: {
        type: 'object',
        properties: {
          zones: { type: 'array', items: { type: 'string' }, description: 'Zonas para anuncio' },
          message: { type: 'string' },
          repeat: { type: 'number', description: 'Numero de repeticoes' },
        },
        required: ['zones', 'message'],
      },
    },
  ],
}));

// === Tool Handlers ===

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const params = args as Record<string, unknown>;

  try {
    switch (name) {
      // === Channel Configuration ===
      case 'notification_configure_channel': {
        const channel = params.channel as NotificationChannel;
        const existing = channelConfigs.get(channel) || { enabled: false, provider: '', credentials: {}, settings: {} };

        channelConfigs.set(channel, {
          enabled: params.enabled !== undefined ? params.enabled as boolean : existing.enabled,
          provider: params.provider as string || existing.provider,
          credentials: { ...existing.credentials, ...((params.credentials as object) || {}) },
          settings: { ...existing.settings, ...((params.settings as object) || {}) },
        });

        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Canal ${channel} configurado`,
              config: channelConfigs.get(channel),
            }),
          }],
        };
      }

      case 'notification_list_channels': {
        const channels: Record<string, unknown> = {};
        channelConfigs.forEach((config, channel) => {
          channels[channel] = {
            enabled: config.enabled,
            provider: config.provider,
          };
        });
        return { content: [{ type: 'text', text: JSON.stringify({ channels }) }] };
      }

      case 'notification_test_channel': {
        const result = await sendNotification(
          params.channel as NotificationChannel,
          params.recipient as string,
          'Teste de Notificacao',
          'Esta e uma mensagem de teste do sistema Guardian.',
          'low'
        );
        return { content: [{ type: 'text', text: JSON.stringify({ success: result.status === 'sent', notification: result }) }] };
      }

      // === Send Notifications ===
      case 'notification_send': {
        const result = await sendNotification(
          params.channel as NotificationChannel,
          params.recipient as string,
          params.subject as string,
          params.message as string,
          (params.priority as NotificationPriority) || 'normal'
        );
        return { content: [{ type: 'text', text: JSON.stringify(result) }] };
      }

      case 'notification_send_template': {
        const template = templates.get(params.template_id as string);
        if (!template) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Template nao encontrado' }) }] };
        }

        const variables = params.variables as Record<string, string>;
        const subject = template.subject ? parseTemplate(template.subject, variables) : undefined;
        const message = parseTemplate(template.body, variables);
        const channelsToUse = (params.channels as NotificationChannel[]) || template.channels;

        const results: Notification[] = [];
        for (const channel of channelsToUse) {
          const result = await sendNotification(
            channel,
            params.recipient as string,
            subject,
            message,
            (params.priority as NotificationPriority) || 'normal'
          );
          results.push(result);
        }

        return { content: [{ type: 'text', text: JSON.stringify({ success: true, notifications: results }) }] };
      }

      case 'notification_broadcast': {
        const results: Notification[] = [];
        const channels = params.channels as NotificationChannel[];
        const recipients = params.recipients as string[];

        for (const recipient of recipients) {
          for (const channel of channels) {
            const result = await sendNotification(
              channel,
              recipient,
              params.subject as string,
              params.message as string,
              (params.priority as NotificationPriority) || 'normal'
            );
            results.push(result);
          }
        }

        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              total_sent: results.filter(r => r.status === 'sent').length,
              total_failed: results.filter(r => r.status === 'failed').length,
              notifications: results,
            }),
          }],
        };
      }

      case 'notification_send_to_group': {
        const group = groups.get(params.group_id as string);
        if (!group) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Grupo nao encontrado' }) }] };
        }

        const template = templates.get(params.template_id as string);
        if (!template) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Template nao encontrado' }) }] };
        }

        const variables = params.variables as Record<string, string>;
        const subject = template.subject ? parseTemplate(template.subject, variables) : undefined;
        const message = parseTemplate(template.body, variables);

        const results: Notification[] = [];
        for (const contactId of group.contacts) {
          const contact = contacts.get(contactId);
          if (!contact) continue;

          for (const channel of contact.preferences.channels) {
            let recipient = '';
            switch (channel) {
              case 'email': recipient = contact.email || ''; break;
              case 'sms': recipient = contact.phone || ''; break;
              case 'whatsapp': recipient = contact.whatsapp || contact.phone || ''; break;
              case 'push': recipient = contact.pushToken || ''; break;
              default: recipient = contact.id;
            }

            if (recipient) {
              const result = await sendNotification(
                channel,
                recipient,
                subject,
                message,
                (params.priority as NotificationPriority) || 'normal'
              );
              results.push(result);
            }
          }
        }

        return { content: [{ type: 'text', text: JSON.stringify({ success: true, notifications: results }) }] };
      }

      // === Templates ===
      case 'notification_list_templates': {
        const templateList = Array.from(templates.values()).map(t => ({
          id: t.id,
          name: t.name,
          channels: t.channels,
        }));
        return { content: [{ type: 'text', text: JSON.stringify({ templates: templateList }) }] };
      }

      case 'notification_get_template': {
        const template = templates.get(params.template_id as string);
        if (!template) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Template nao encontrado' }) }] };
        }
        return { content: [{ type: 'text', text: JSON.stringify(template) }] };
      }

      case 'notification_create_template': {
        const newTemplate: NotificationTemplate = {
          id: params.id as string,
          name: params.name as string,
          channels: params.channels as NotificationChannel[],
          subject: params.subject as string,
          body: params.body as string,
          variables: (params.variables as string[]) || [],
        };
        templates.set(newTemplate.id, newTemplate);
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, template: newTemplate }) }] };
      }

      case 'notification_update_template': {
        const template = templates.get(params.template_id as string);
        if (!template) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Template nao encontrado' }) }] };
        }
        if (params.name) template.name = params.name as string;
        if (params.channels) template.channels = params.channels as NotificationChannel[];
        if (params.subject) template.subject = params.subject as string;
        if (params.body) template.body = params.body as string;
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, template }) }] };
      }

      // === Contacts ===
      case 'notification_add_contact': {
        const newContact: Contact = {
          id: params.id as string,
          name: params.name as string,
          role: params.role as string,
          phone: params.phone as string,
          email: params.email as string,
          whatsapp: params.whatsapp as string,
          pushToken: params.push_token as string,
          preferences: {
            channels: (params.preferred_channels as NotificationChannel[]) || ['push', 'email'],
          },
        };
        contacts.set(newContact.id, newContact);
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, contact: newContact }) }] };
      }

      case 'notification_list_contacts': {
        let contactList = Array.from(contacts.values());
        if (params.role) {
          contactList = contactList.filter(c => c.role === params.role);
        }
        return { content: [{ type: 'text', text: JSON.stringify({ contacts: contactList }) }] };
      }

      case 'notification_remove_contact': {
        const deleted = contacts.delete(params.contact_id as string);
        return { content: [{ type: 'text', text: JSON.stringify({ success: deleted }) }] };
      }

      // === Groups ===
      case 'notification_create_group': {
        const newGroup: NotificationGroup = {
          id: params.id as string,
          name: params.name as string,
          contacts: params.contact_ids as string[],
          escalation_delay_minutes: (params.escalation_delay as number) || 5,
        };
        groups.set(newGroup.id, newGroup);
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, group: newGroup }) }] };
      }

      case 'notification_list_groups': {
        return { content: [{ type: 'text', text: JSON.stringify({ groups: Array.from(groups.values()) }) }] };
      }

      case 'notification_add_to_group': {
        const group = groups.get(params.group_id as string);
        if (!group) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Grupo nao encontrado' }) }] };
        }
        if (!group.contacts.includes(params.contact_id as string)) {
          group.contacts.push(params.contact_id as string);
        }
        return { content: [{ type: 'text', text: JSON.stringify({ success: true, group }) }] };
      }

      // === History ===
      case 'notification_history': {
        let history = Array.from(notifications.values());
        if (params.channel) history = history.filter(n => n.channel === params.channel);
        if (params.status) history = history.filter(n => n.status === params.status);
        if (params.recipient) history = history.filter(n => n.recipient === params.recipient);
        if (params.limit) history = history.slice(-(params.limit as number));
        return { content: [{ type: 'text', text: JSON.stringify({ notifications: history }) }] };
      }

      case 'notification_get_status': {
        const notification = notifications.get(params.notification_id as string);
        if (!notification) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Notificacao nao encontrada' }) }] };
        }
        return { content: [{ type: 'text', text: JSON.stringify(notification) }] };
      }

      // === Emergency ===
      case 'notification_emergency_broadcast': {
        const emergencyInstructions: Record<string, string> = {
          fire: 'Evacue o predio pelas saidas de emergencia. Nao use elevadores.',
          intrusion: 'Mantenha-se em local seguro. Aguarde instrucoes.',
          medical: 'Mantenha a area livre para acesso dos socorristas.',
          evacuation: 'Dirija-se ao ponto de encontro mais proximo.',
          lockdown: 'Permaneca no local. Tranque portas e janelas.',
        };

        const variables = {
          type: params.type as string,
          location: params.location as string,
          instructions: (params.instructions as string) || emergencyInstructions[params.type as string] || 'Aguarde instrucoes.',
        };

        const template = templates.get('emergency');
        if (!template) {
          return { content: [{ type: 'text', text: JSON.stringify({ error: 'Template de emergencia nao encontrado' }) }] };
        }

        const message = parseTemplate(template.body, variables);
        const results: Notification[] = [];

        // Enviar por todos os canais de emergencia
        for (const channel of template.channels) {
          if (channelConfigs.get(channel)?.enabled) {
            const result = await sendNotification(channel, 'all', 'EMERGENCIA', message, 'critical');
            results.push(result);
          }
        }

        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: 'Broadcast de emergencia enviado',
              type: params.type,
              location: params.location,
              channels_notified: results.map(r => r.channel),
            }),
          }],
        };
      }

      case 'notification_intercom_announce': {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: 'Anuncio enviado ao intercomunicador',
              zones: params.zones,
              repeat: params.repeat || 1,
            }),
          }],
        };
      }

      default:
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({ error: `Ferramenta desconhecida: ${name}` }),
          }],
        };
    }
  } catch (error) {
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({ error: `Erro ao executar ${name}: ${(error as Error).message}` }),
      }],
    };
  }
});

// === Main ===

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP Guardian Notifications iniciado');
}

main().catch(console.error);
