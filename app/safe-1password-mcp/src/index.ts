#!/usr/bin/env node
import express from 'express';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { ConnectClient } from './connect-client.js';
import { createToolHandlers } from './tools.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { redactLog } from './redact.js';

const PORT = Number(process.env.PORT ?? 8001);
const OP_CONNECT_HOST = process.env.OP_CONNECT_HOST ?? '';
const OP_API_KEY = process.env.OP_API_KEY ?? '';
const SSE_PATH = process.env.SSE_PATH ?? '/mcp/1password';
const MESSAGE_PATH = process.env.MESSAGE_PATH ?? `${SSE_PATH}/messages`;

if (!OP_CONNECT_HOST || !OP_API_KEY) {
  console.error('FATAL: OP_CONNECT_HOST and OP_API_KEY are required');
  process.exit(1);
}

const connectClient = new ConnectClient(OP_CONNECT_HOST, OP_API_KEY);
const handlers = createToolHandlers(connectClient);
const transports = new Map<string, SSEServerTransport>();

const app = express();

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'safe-1password-mcp', active_sessions: transports.size });
});

function createMcpServer(): Server {
  const mcp = new Server(
    { name: 'safe-1password-mcp', version: '1.0.0' },
    { capabilities: { tools: {} } },
  );

  mcp.setRequestHandler(ListToolsRequestSchema, async () => handlers.listTools());
  mcp.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    console.error(redactLog(`[MCP] tool=${name} args=${JSON.stringify(args ?? {})}`));
    return await handlers.callTool(name, (args ?? {}) as Record<string, unknown>);
  });

  return mcp;
}

app.get(SSE_PATH, async (_req, res) => {
  const transport = new SSEServerTransport(MESSAGE_PATH, res);
  const mcp = createMcpServer();

  transports.set(transport.sessionId, transport);

  transport.onclose = () => {
    transports.delete(transport.sessionId);
    console.error(`[SSE] session closed sid=${transport.sessionId}`);
  };

  await mcp.connect(transport);
  console.error(`[SSE] session opened sid=${transport.sessionId}`);
});

app.post(MESSAGE_PATH, async (req, res) => {
  const sessionId = req.query.sessionId as string;
  if (!sessionId) {
    res.status(400).json({ error: 'Missing sessionId' });
    return;
  }

  const transport = transports.get(sessionId);
  if (!transport) {
    res.status(404).json({ error: `Session not found: ${sessionId}` });
    return;
  }

  await transport.handlePostMessage(req, res);
});

app.listen(PORT, '0.0.0.0', () => {
  console.error(`[safe-1password-mcp] Listening on 0.0.0.0:${PORT}`);
  console.error(`[safe-1password-mcp] SSE: GET ${SSE_PATH}`);
  console.error(`[safe-1password-mcp] Messages: POST ${MESSAGE_PATH}`);
  console.error(`[safe-1password-mcp] Connect host: ${OP_CONNECT_HOST.replace(/\/\/.*@/, '//[REDACTED]@')}`);
});
