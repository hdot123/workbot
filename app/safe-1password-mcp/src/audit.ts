import { v4 as uuidv4 } from 'uuid';
import { redactLog } from './redact';

export interface AuditEntry {
  request_id: string;
  tool_name: string;
  vault_id?: string;
  item_id?: string;
  field_label?: string;
  result_count?: number;
  duration_ms: number;
  connect_api_call_count: number;
  timestamp: string;
}

export class AuditLogger {
  private stream: NodeJS.WritableStream;

  constructor(stream?: NodeJS.WritableStream) {
    this.stream = stream ?? process.stderr;
  }

  log(entry: Omit<AuditEntry, 'request_id' | 'timestamp'>): string {
    const request_id = uuidv4();
    const record: AuditEntry = {
      ...entry,
      request_id,
      timestamp: new Date().toISOString(),
    };
    const line = JSON.stringify(record);
    this.stream.write(redactLog(line) + '\n');
    return request_id;
  }
}
