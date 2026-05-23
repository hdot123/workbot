const BLOCKED_FIELDS = new Set([
  'password', 'token', 'secret', 'credential', 'notesplain', 'note',
  'onetimepassword', 'otp', 'concealed', 'section_value',
]);

const BLOCKED_SUBSTRINGS = [
  'password', 'passphrase', 'private key', 'secret key', 'access key',
  'api key', 'api secret', 'auth token', 'bearer', 'private_key',
  'secret_key', 'otp', 'one-time', 'onetimepassword',
];

const BLOCKED_PURPOSES = new Set(['PASSWORD']);

interface RawItem {
  id?: string;
  title?: string;
  category?: string;
  state?: string;
  vault?: { id?: string };
  tags?: string[];
  updated_at?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface SafeItemMeta {
  id: string;
  title: string;
  category: string;
  state: string;
  vault_id: string;
  tags: string[];
  updated_at: string;
}

export function sanitizeItemMeta(raw: unknown): SafeItemMeta {
  const item = raw as RawItem;
  return {
    id: item.id ?? '',
    title: item.title ?? '',
    category: item.category ?? '',
    state: item.state ?? '',
    vault_id: item.vault?.id ?? '',
    tags: Array.isArray(item.tags) ? item.tags : [],
    updated_at: item.updated_at ?? item.updatedAt ?? '',
  };
}

export function isFieldAllowed(fieldId: string, fieldLabel: string, fieldPurpose?: string): boolean {
  // Check by purpose (PASSWORD fields always blocked)
  if (fieldPurpose && BLOCKED_PURPOSES.has(fieldPurpose.toUpperCase())) {
    return false;
  }

  const lid = (fieldId ?? '').toLowerCase();
  const ll = (fieldLabel ?? '').toLowerCase();

  // Exact match against blocked set
  if (BLOCKED_FIELDS.has(lid) || BLOCKED_FIELDS.has(ll)) return false;

  // Substring match for compound names like "private key"
  for (const sub of BLOCKED_SUBSTRINGS) {
    if (lid.includes(sub) || ll.includes(sub)) return false;
  }

  return true;
}
