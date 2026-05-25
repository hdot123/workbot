const SENSITIVE_KEYS = [
  'password', 'token', 'secret', 'credential', 'apikey', 'api_key',
  'authorization', 'cookie', 'notesplain', 'onetimepassword', 'otp',
  'concealed', 'section_value',
];

export function redactSensitive(obj: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    const lk = key.toLowerCase();
    const isSensitive = SENSITIVE_KEYS.some(s => lk.includes(s));
    if (isSensitive && typeof value === 'string') {
      result[key] = '[REDACTED]';
    } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      result[key] = redactSensitive(value as Record<string, unknown>);
    } else {
      result[key] = value;
    }
  }
  return result;
}

const LOG_REDACT_PATTERNS = [
  /apikey["\s:=]+[\w-]+/gi,
  /authorization["\s:=]+[\w.-]+/gi,
  /op_connect_token["\s:=]+[\w.-]+/gi,
  /"value"\s*:\s*"[^"]{6,}"/gi,
];

export function redactLog(input: string): string {
  let result = input;
  for (const pattern of LOG_REDACT_PATTERNS) {
    result = result.replace(pattern, '[REDACTED]');
  }
  return result;
}
