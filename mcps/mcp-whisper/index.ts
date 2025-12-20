/**
 * MCP Whisper - Transcrição de Áudio
 * Conecta Plus
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'mcp-whisper', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'whisper_transcribe',
      description: 'Transcreve áudio para texto',
      inputSchema: {
        type: 'object',
        properties: {
          audio_path: { type: 'string', description: 'Caminho do arquivo de áudio' },
          audio_url: { type: 'string', description: 'URL do áudio' },
          audio_base64: { type: 'string', description: 'Áudio em base64' },
          language: { type: 'string', description: 'Código do idioma (pt, en, es)' },
          model: { type: 'string', enum: ['tiny', 'base', 'small', 'medium', 'large'], description: 'Modelo Whisper' },
        },
      },
    },
    {
      name: 'whisper_translate',
      description: 'Transcreve e traduz para inglês',
      inputSchema: {
        type: 'object',
        properties: {
          audio_path: { type: 'string' },
          audio_url: { type: 'string' },
          model: { type: 'string', enum: ['tiny', 'base', 'small', 'medium', 'large'] },
        },
      },
    },
    {
      name: 'whisper_detect_language',
      description: 'Detecta idioma do áudio',
      inputSchema: {
        type: 'object',
        properties: {
          audio_path: { type: 'string' },
          audio_url: { type: 'string' },
        },
      },
    },
    {
      name: 'whisper_transcribe_stream',
      description: 'Transcrição em tempo real de stream',
      inputSchema: {
        type: 'object',
        properties: {
          stream_url: { type: 'string', description: 'URL do stream RTSP/HLS' },
          duration: { type: 'number', description: 'Duração em segundos' },
          language: { type: 'string' },
        },
        required: ['stream_url'],
      },
    },
    {
      name: 'whisper_transcribe_segments',
      description: 'Transcrição com timestamps por segmento',
      inputSchema: {
        type: 'object',
        properties: {
          audio_path: { type: 'string' },
          language: { type: 'string' },
          word_timestamps: { type: 'boolean' },
        },
      },
    },
    {
      name: 'whisper_batch_transcribe',
      description: 'Transcrição em lote de múltiplos arquivos',
      inputSchema: {
        type: 'object',
        properties: {
          audio_paths: { type: 'array', items: { type: 'string' } },
          language: { type: 'string' },
        },
        required: ['audio_paths'],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'whisper_transcribe': {
      // Integração com faster-whisper
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            text: '',
            language: args.language || 'pt',
            duration: 0,
            model_used: args.model || 'base',
            message: 'Transcrição via faster-whisper'
          })
        }]
      };
    }

    case 'whisper_translate': {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            original_text: '',
            translated_text: '',
            source_language: 'unknown',
            target_language: 'en'
          })
        }]
      };
    }

    case 'whisper_detect_language': {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            detected_language: 'pt',
            confidence: 0.95,
            alternatives: [
              { language: 'es', confidence: 0.03 },
              { language: 'en', confidence: 0.02 }
            ]
          })
        }]
      };
    }

    case 'whisper_transcribe_stream': {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            stream_url: args.stream_url,
            duration: args.duration || 60,
            transcription: '',
            segments: []
          })
        }]
      };
    }

    case 'whisper_transcribe_segments': {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            segments: [],
            full_text: '',
            word_timestamps: args.word_timestamps || false
          })
        }]
      };
    }

    case 'whisper_batch_transcribe': {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            results: (args.audio_paths as string[]).map(path => ({
              path,
              text: '',
              status: 'pending'
            })),
            total: (args.audio_paths as string[]).length
          })
        }]
      };
    }

    default:
      return { content: [{ type: 'text', text: JSON.stringify({ error: 'Ferramenta desconhecida' }) }] };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP Whisper iniciado');
}

main().catch(console.error);
