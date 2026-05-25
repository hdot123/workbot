import { ConnectClient } from './connect-client.js';
import { AuditLogger } from './audit.js';
import { sanitizeItemMeta } from './sanitize.js';

const audit = new AuditLogger();

export function createToolHandlers(client: ConnectClient) {
  return {
    listTools() {
      return {
        tools: [
          {
            name: 'list_vaults',
            description: 'List all accessible 1Password vaults (metadata only)',
            inputSchema: { type: 'object', properties: {}, required: [] },
          },
          {
            name: 'search_items',
            description:
              'Search items in a vault. Requires a non-empty title query — full enumeration without a query is blocked. Returns metadata only (id, title, category, state, vault_id, tags, updated_at). Never returns fields, passwords, tokens, or secrets.',
            inputSchema: {
              type: 'object',
              properties: {
                vault_id: { type: 'string', description: 'Vault ID' },
                query: { type: 'string', description: 'Search query (title filter). REQUIRED — cannot be empty.' },
                limit: { type: 'number', description: 'Max items to return (default 50, max 100)' },
              },
              required: ['vault_id', 'query'],
            },
          },
          {
            name: 'get_item',
            description:
              'Get a single item by ID. Returns metadata plus non-sensitive fields. Sensitive fields (password, token, secret, credential, notesPlain) are redacted as [REDACTED].',
            inputSchema: {
              type: 'object',
              properties: {
                vault_id: { type: 'string', description: 'Vault ID' },
                item_id: { type: 'string', description: 'Item ID' },
              },
              required: ['vault_id', 'item_id'],
            },
          },
          {
            name: 'read_secret',
            description:
              'Read a single specific field value from an item. Requires exact vault_id, item_id, and field_label. This is the ONLY tool that returns actual field values — all other tools return metadata only. Use for passwords/tokens only when explicitly needed.',
            inputSchema: {
              type: 'object',
              properties: {
                vault_id: { type: 'string', description: 'Vault ID' },
                item_id: { type: 'string', description: 'Item ID' },
                field_label: {
                  type: 'string',
                  description: 'Exact field label to read (e.g. "password", "credential", "token")',
                },
              },
              required: ['vault_id', 'item_id', 'field_label'],
            },
          },
        ],
      };
    },

    async callTool(name: string, args: Record<string, unknown>) {
      const start = Date.now();
      client.resetCallCount();

      try {
        switch (name) {
          case 'list_vaults':
            return await handleListVaults(client, start);
          case 'search_items':
            return await handleSearchItems(client, args, start);
          case 'get_item':
            return await handleGetItem(client, args, start);
          case 'read_secret':
            return await handleReadSecret(client, args, start);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        audit.log({
          tool_name: name,
          duration_ms: Date.now() - start,
          connect_api_call_count: client.callCountSnapshot,
        });
        return { content: [{ type: 'text' as const, text: `Error: ${msg}` }], isError: true };
      }
    },
  };
}

async function handleListVaults(client: ConnectClient, start: number) {
  const vaults = await client.listVaults();
  const result = (vaults as Record<string, unknown>[]).map((v) => ({
    id: v.id,
    name: v.name,
    type: v.type,
    items: v.items,
    created_at: v.createdAt,
    updated_at: v.updatedAt,
  }));

  audit.log({
    tool_name: 'list_vaults',
    result_count: result.length,
    duration_ms: Date.now() - start,
    connect_api_call_count: client.callCountSnapshot,
  });

  return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
}

async function handleSearchItems(
  client: ConnectClient,
  args: Record<string, unknown>,
  start: number,
) {
  const vaultId = String(args.vault_id ?? '');
  if (!vaultId) throw new Error('vault_id is required');

  const query = String(args.query ?? '').trim();
  if (!query) {
    throw new Error('query is required — full vault enumeration without a search term is not allowed');
  }
  const limit = Math.min(Number(args.limit ?? 50), 100);

  const rawItems = await client.searchItems(vaultId, query);
  const items = rawItems.map(sanitizeItemMeta).slice(0, limit);

  audit.log({
    tool_name: 'search_items',
    vault_id: vaultId,
    result_count: items.length,
    duration_ms: Date.now() - start,
    connect_api_call_count: client.callCountSnapshot,
  });

  return { content: [{ type: 'text' as const, text: JSON.stringify(items, null, 2) }] };
}

async function handleGetItem(
  client: ConnectClient,
  args: Record<string, unknown>,
  start: number,
) {
  const vaultId = String(args.vault_id ?? '');
  const itemId = String(args.item_id ?? '');
  if (!vaultId || !itemId) throw new Error('vault_id and item_id are required');

  const raw = await client.getItem(vaultId, itemId) as Record<string, unknown>;

  // Build safe output: metadata + field manifest only (never field values)
  const safe: Record<string, unknown> = {
    id: raw.id,
    title: raw.title,
    category: raw.category,
    created_at: raw.created_at ?? raw.createdAt,
    updated_at: raw.updated_at ?? raw.updatedAt,
    tags: raw.tags,
    vault: raw.vault ? { id: (raw.vault as Record<string, unknown>).id } : undefined,
  };

  // Field manifest: label + type + purpose only, never value
  const fields = raw.fields as Record<string, unknown>[] | undefined;
  if (Array.isArray(fields)) {
    safe.fields = fields.map((f) => ({
      id: f.id,
      label: f.label,
      type: f.type,
      purpose: f.purpose,
    }));
  }

  // Redact sections
  const sections = raw.sections as Record<string, unknown>[] | undefined;
  if (Array.isArray(sections)) {
    safe.sections = sections.map((s) => ({
      id: s.id,
      label: s.label,
    }));
  }

  audit.log({
    tool_name: 'get_item',
    vault_id: vaultId,
    item_id: itemId,
    duration_ms: Date.now() - start,
    connect_api_call_count: client.callCountSnapshot,
  });

  return { content: [{ type: 'text' as const, text: JSON.stringify(safe, null, 2) }] };
}

async function handleReadSecret(
  client: ConnectClient,
  args: Record<string, unknown>,
  start: number,
) {
  const vaultId = String(args.vault_id ?? '');
  const itemId = String(args.item_id ?? '');
  const fieldLabel = String(args.field_label ?? '');
  if (!vaultId || !itemId || !fieldLabel) {
    throw new Error('vault_id, item_id, and field_label are all required');
  }

  const raw = await client.getItem(vaultId, itemId) as Record<string, unknown>;
  const fields = raw.fields as Record<string, unknown>[] | undefined;

  if (!Array.isArray(fields)) {
    throw new Error('Item has no fields');
  }

  // Find the exact field by label or id
  const match = fields.find((f) => {
    const fl = String(f.label ?? '').toLowerCase();
    const fi = String(f.id ?? '').toLowerCase();
    return fl === fieldLabel.toLowerCase() || fi === fieldLabel.toLowerCase();
  });

  if (!match) {
    const available = fields.map((f) => f.label ?? f.id).filter(Boolean);
    throw new Error(`Field "${fieldLabel}" not found. Available fields: ${available.join(', ')}`);
  }

  const value = match.value;
  if (value === undefined || value === null) {
    throw new Error(`Field "${fieldLabel}" exists but has no value`);
  }

  audit.log({
    tool_name: 'read_secret',
    vault_id: vaultId,
    item_id: itemId,
    field_label: fieldLabel,
    duration_ms: Date.now() - start,
    connect_api_call_count: client.callCountSnapshot,
  });

  return { content: [{ type: 'text' as const, text: String(value) }] };
}
