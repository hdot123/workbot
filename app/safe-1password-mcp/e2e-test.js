#!/usr/bin/env node
/**
 * E2E test for safe-1password-mcp server
 * Tests SSE transport → JSON-RPC → tool calls against http://192.168.88.15:8001
 *
 * Uses raw HTTP/SSE approach with proper event parsing.
 * CRITICAL: This script never prints actual secret values.
 */

const BASE_URL = 'http://192.168.88.15:8001';
const SSE_PATH = '/mcp/1password';
const MESSAGE_PATH = '/mcp/1password/messages';

let globalId = 0;
function nextId() { return ++globalId; }
function elapsed(start) { return `${Date.now() - start}ms`; }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

/**
 * SSE client that captures all events from the stream.
 * Returns sessionId and a way to wait for specific JSON-RPC responses.
 */
async function connectSSE() {
  const res = await fetch(`${BASE_URL}${SSE_PATH}`);
  if (!res.ok) throw new Error(`SSE GET → ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let sessionId = null;
  const pendingResolvers = [];
  const responseQueue = [];
  let currentEvent = { type: 'message', data: '' };

  function parseSSEEvents(chunk) {
    buffer += chunk;
    while (true) {
      const idx = buffer.indexOf('\n\n');
      if (idx === -1) break;
      const block = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);

      let eventType = 'message';
      let dataLines = [];
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trim());
        }
      }
      const data = dataLines.join('\n');

      if (eventType === 'endpoint') {
        const match = data.match(/sessionId=([a-f0-9-]+)/);
        if (match) sessionId = match[1];
      } else if (eventType === 'message') {
        try {
          const parsed = JSON.parse(data);
          if (responseQueue.length === 0 && pendingResolvers.length > 0) {
            pendingResolvers.shift()(parsed);
          } else {
            responseQueue.push(parsed);
          }
        } catch (e) { /* ignore non-JSON */ }
      }
    }
  }

  // Read stream in background
  const readPromise = (async () => {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      parseSSEEvents(decoder.decode(value, { stream: true }));
    }
  })();

  // Wait for sessionId
  await sleep(800);
  if (!sessionId) throw new Error('Failed to obtain sessionId');

  return {
    sessionId,
    waitForResponse(timeout = 15000) {
      if (responseQueue.length > 0) {
        return Promise.resolve(responseQueue.shift());
      }
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('Response timeout')), timeout);
        pendingResolvers.push((val) => { clearTimeout(timer); resolve(val); });
      });
    },
  };
}

/**
 * Send a JSON-RPC request and wait for the response on SSE.
 */
async function rpc(session, method, params, timeout = 15000) {
  const start = Date.now();
  const id = nextId();

  const url = `${BASE_URL}${MESSAGE_PATH}?sessionId=${session.sessionId}`;
  const body = JSON.stringify({
    jsonrpc: '2.0',
    id,
    method,
    ...(params !== undefined ? { params } : {}),
  });

  // Fire POST (server ACKs the POST, actual response comes via SSE)
  const postRes = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  });

  // POST response is just an ACK, the real response comes via SSE
  // Drain the POST response body
  await postRes.text();

  // Now wait for the JSON-RPC response on SSE (matching our request id)
  const response = await session.waitForResponse(timeout);

  // Make sure we got the right response (match by id)
  if (response && response.id !== id && response.id !== undefined) {
    // Might have gotten an out-of-order response; try again
    const second = await session.waitForResponse(timeout);
    return { response: second, duration: elapsed(start) };
  }

  return { response, duration: elapsed(start) };
}

/**
 * Send a notification (no response expected).
 */
async function notify(session, method, params) {
  const url = `${BASE_URL}${MESSAGE_PATH}?sessionId=${session.sessionId}`;
  const body = JSON.stringify({
    jsonrpc: '2.0',
    method,
    ...(params !== undefined ? { params } : {}),
  });
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  });
  await res.text();
}

// ─── Security check ─────────────────────────────────────────────────────

const SENSITIVE_KEYWORDS = ['password', 'token', 'secret', 'credential', 'api_key', 'apikey', 'private_key'];

function checkForLeaks(obj, path = '') {
  const leaks = [];
  if (typeof obj === 'string') {
    if (obj === '[REDACTED]' || obj.length < 8) return leaks;
    for (const kw of SENSITIVE_KEYWORDS) {
      if (path.toLowerCase().includes(kw) && obj !== '[REDACTED]') {
        if (/[A-Za-z0-9+/=_-]{12,}/.test(obj)) {
          leaks.push({ path, preview: `${obj.slice(0, 3)}...${obj.slice(-3)}` });
        }
      }
    }
  } else if (Array.isArray(obj)) {
    for (let i = 0; i < obj.length; i++) leaks.push(...checkForLeaks(obj[i], `${path}[${i}]`));
  } else if (obj && typeof obj === 'object') {
    for (const [key, val] of Object.entries(obj)) {
      leaks.push(...checkForLeaks(val, path ? `${path}.${key}` : key));
    }
  }
  return leaks;
}

function extractText(result) {
  const content = result?.result?.content;
  if (Array.isArray(content)) {
    return content.filter(c => c.type === 'text').map(c => c.text).join('\n');
  }
  return JSON.stringify(result);
}

function isError(result) {
  return result?.error !== undefined || result?.result?.isError === true;
}

// ─── Main ───────────────────────────────────────────────────────────────

async function runTests() {
  const totalStart = Date.now();
  const results = [];

  console.log('═══════════════════════════════════════════════════════════');
  console.log('  safe-1password-mcp E2E Test');
  console.log(`  Server: ${BASE_URL}`);
  console.log(`  Started: ${new Date().toISOString()}`);
  console.log('═══════════════════════════════════════════════════════════\n');

  // ── Step 0: Health Check ──
  console.log('--- Step 0: Health Check ---');
  try {
    const t = Date.now();
    const h = await (await fetch(`${BASE_URL}/health`)).json();
    console.log(`  ${JSON.stringify(h)}`);
    console.log(`  Time: ${elapsed(t)}`);
    console.log('  ✅ PASS\n');
  } catch (e) {
    console.log(`  ❌ FAIL: ${e.message}\n  Aborting.\n`);
    process.exit(1);
  }

  // ── Step 1: SSE Connect ──
  console.log('--- Step 1: SSE Connection ---');
  let session;
  try {
    const t = Date.now();
    session = await connectSSE();
    console.log(`  Session: ${session.sessionId}`);
    console.log(`  Time: ${elapsed(t)}`);
    console.log('  ✅ PASS\n');
  } catch (e) {
    console.log(`  ❌ FAIL: ${e.message}\n`);
    process.exit(1);
  }

  // ── Step 2: Initialize ──
  console.log('--- Step 2: Initialize ---');
  try {
    const { response, duration } = await rpc(session, 'initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'e2e-test', version: '1.0.0' },
    });
    console.log(`  Time: ${duration}`);
    console.log(`  Server: ${JSON.stringify(response?.result?.serverInfo)}`);
    const ok = response?.result?.serverInfo?.name === 'safe-1password-mcp';
    console.log(`  ${ok ? '✅ PASS' : '❌ FAIL'}\n`);
    if (!ok) { console.log(`  Full response: ${JSON.stringify(response).slice(0, 500)}\n`); }

    // Send initialized notification
    await notify(session, 'notifications/initialized', {});
    await sleep(300);
  } catch (e) {
    console.log(`  ❌ FAIL: ${e.message}\n`);
    process.exit(1);
  }

  // ── Step 3: tools/list ──
  console.log('--- Step 3: tools/list (expect exactly 4 tools) ---');
  try {
    const { response, duration } = await rpc(session, 'tools/list', {});
    const tools = response?.result?.tools || [];
    const names = tools.map(t => t.name);
    const expected = ['list_vaults', 'search_items', 'get_item', 'read_secret'];

    console.log(`  Time: ${duration}`);
    console.log(`  Found (${names.length}): ${names.join(', ')}`);

    const pass = names.length === 4 && expected.every(n => names.includes(n)) && names.every(n => expected.includes(n));
    console.log(`  ${pass ? '✅ PASS' : '❌ FAIL'}\n`);
    results.push({ step: 'tools/list', pass, duration });
  } catch (e) {
    console.log(`  ❌ FAIL: ${e.message}\n`);
    results.push({ step: 'tools/list', pass: false, error: e.message });
  }

  // ── Step 4: list_vaults ──
  console.log('--- Step 4: list_vaults ---');
  let vaultId = null;
  try {
    const { response, duration } = await rpc(session, 'tools/call', { name: 'list_vaults', arguments: {} });
    console.log(`  Time: ${duration}`);
    if (isError(response)) {
      console.log(`  ❌ Error: ${extractText(response)}`);
      results.push({ step: 'list_vaults', pass: false, duration });
    } else {
      const vaults = JSON.parse(extractText(response));
      console.log(`  Vaults: ${vaults.length}`);
      for (const v of vaults) console.log(`    - ${v.name} (${v.id})`);
      if (vaults.length > 0) {
        vaultId = vaults[0].id;
        console.log(`  Using: ${vaults[0].name}`);
        console.log('  ✅ PASS\n');
        results.push({ step: 'list_vaults', pass: true, duration });
      } else {
        console.log('  ❌ FAIL: no vaults\n');
        results.push({ step: 'list_vaults', pass: false, duration });
      }
    }
  } catch (e) {
    console.log(`  ❌ FAIL: ${e.message}\n`);
    results.push({ step: 'list_vaults', pass: false, error: e.message });
  }

  if (!vaultId) {
    console.log('⚠️  No vault ID, cannot continue.\n');
    printSummary(results, totalStart);
    return;
  }

  // ── Step 5: search_items (metadata-only) ──
  console.log('--- Step 5: search_items (metadata-only, limit 3) ---');
  let firstItemId = null;
  try {
    const { response, duration } = await rpc(session, 'tools/call', {
      name: 'search_items',
      arguments: { vault_id: vaultId, limit: 3 },
    });
    console.log(`  Time: ${duration}`);
    if (isError(response)) {
      console.log(`  ❌ Error: ${extractText(response)}`);
      results.push({ step: 'search_items', pass: false, duration });
    } else {
      const items = JSON.parse(extractText(response));
      console.log(`  Items: ${items.length}`);

      const forbiddenKeys = ['fields', 'value', 'password', 'token', 'secret'];
      let metaOk = true;
      for (const item of items) {
        const keys = Object.keys(item);
        const bad = forbiddenKeys.filter(k => keys.includes(k));
        if (bad.length) { metaOk = false; console.log(`    ⚠️ "${item.title}" has: ${bad.join(',')}`); }
        console.log(`    - ${item.title} (${item.category}) [${item.id}]`);
      }

      const leaks = checkForLeaks(items, 'search_items');
      leaks.length ? console.log(`  🚨 ${leaks.length} leak(s) in search_items`) : console.log('  🔒 No leaks');

      if (items.length > 0) firstItemId = items[0].id;
      const pass = metaOk && leaks.length === 0;
      console.log(`  ${pass ? '✅ PASS' : '❌ FAIL'}\n`);
      results.push({ step: 'search_items', pass, duration, leaks: leaks.length });
    }
  } catch (e) {
    console.log(`  ❌ FAIL: ${e.message}\n`);
    results.push({ step: 'search_items', pass: false, error: e.message });
  }

  if (!firstItemId) {
    console.log('⚠️  No item ID, cannot continue.\n');
    printSummary(results, totalStart);
    return;
  }

  // ── Step 6: get_item (verify [REDACTED]) ──
  console.log('--- Step 6: get_item (verify sensitive fields are [REDACTED]) ---');
  let firstFieldLabel = null;
  try {
    const { response, duration } = await rpc(session, 'tools/call', {
      name: 'get_item',
      arguments: { vault_id: vaultId, item_id: firstItemId },
    });
    console.log(`  Time: ${duration}`);
    if (isError(response)) {
      console.log(`  ❌ Error: ${extractText(response)}`);
      results.push({ step: 'get_item', pass: false, duration });
    } else {
      const item = JSON.parse(extractText(response));
      console.log(`  Item: ${item.title} (${item.category})`);

      let redactionOk = true;
      const sensitiveLabels = ['password', 'token', 'secret', 'credential', 'notesplain'];
      if (Array.isArray(item.fields)) {
        for (const f of item.fields) {
          const label = String(f.label || f.id || '?');
          const value = f.value;
          const isSensitive = sensitiveLabels.some(s =>
            label.toLowerCase().includes(s) || String(f.id || '').toLowerCase().includes(s)
          );
          if (isSensitive && value !== '[REDACTED]') {
            redactionOk = false;
            console.log(`    🚨 "${label}" NOT REDACTED`);
          } else {
            const display = value === '[REDACTED]' ? '[REDACTED] ✅' : `(type=${typeof value}, len=${String(value).length})`;
            console.log(`    "${label}": ${display}`);
          }
        }

        // Find a sensitive field for read_secret test
        for (const f of item.fields) {
          const label = String(f.label || f.id || '');
          if (['password', 'credential', 'token'].some(k => label.toLowerCase().includes(k) || String(f.id || '').toLowerCase().includes(k))) {
            firstFieldLabel = label;
            break;
          }
        }
        if (!firstFieldLabel && item.fields.length > 0) {
          firstFieldLabel = String(item.fields[0].label || item.fields[0].id || '');
        }
      }

      const leaks = checkForLeaks(item, 'get_item');
      leaks.length ? console.log(`  🚨 ${leaks.length} leak(s)`) : console.log('  🔒 No leaks');

      const pass = redactionOk && leaks.length === 0;
      console.log(`  ${pass ? '✅ PASS' : '❌ FAIL'}\n`);
      results.push({ step: 'get_item', pass, duration, leaks: leaks.length });
    }
  } catch (e) {
    console.log(`  ❌ FAIL: ${e.message}\n`);
    results.push({ step: 'get_item', pass: false, error: e.message });
  }

  // ── Step 7: read_secret ──
  if (!firstFieldLabel) {
    console.log('⚠️  No field label, skipping read_secret.\n');
    results.push({ step: 'read_secret', pass: false, error: 'No field label' });
  } else {
    console.log(`--- Step 7: read_secret (field: "${firstFieldLabel}") ---`);
    try {
      const { response, duration } = await rpc(session, 'tools/call', {
        name: 'read_secret',
        arguments: { vault_id: vaultId, item_id: firstItemId, field_label: firstFieldLabel },
      });
      console.log(`  Time: ${duration}`);
      if (isError(response)) {
        console.log(`  ❌ Error: ${extractText(response)}`);
        results.push({ step: 'read_secret', pass: false, duration });
      } else {
        const text = extractText(response);
        const isRedacted = text === '[REDACTED]';
        const len = text.length;
        console.log(`  Value length: ${len} chars`);
        console.log(`  Is [REDACTED]: ${isRedacted}`);

        const pass = !isRedacted && len > 0;
        if (pass) {
          console.log('  ✅ PASS: returned actual value (NOT printed for security)');
        } else if (isRedacted) {
          console.log('  ❌ FAIL: returned [REDACTED]');
        } else {
          console.log('  ❌ FAIL: empty or invalid');
        }
        console.log();
        results.push({ step: 'read_secret', pass, duration });
      }
    } catch (e) {
      console.log(`  ❌ FAIL: ${e.message}\n`);
      results.push({ step: 'read_secret', pass: false, error: e.message });
    }
  }

  printSummary(results, totalStart);
}

function printSummary(results, totalStart) {
  const total = elapsed(totalStart);
  const passed = results.filter(r => r.pass).length;
  const failed = results.filter(r => !r.pass).length;

  console.log('═══════════════════════════════════════════════════════════');
  console.log('  SUMMARY');
  console.log('═══════════════════════════════════════════════════════════\n');
  console.log(`  Total: ${results.length} | Passed: ${passed} | Failed: ${failed}`);
  console.log(`  Overall: ${failed === 0 ? '✅ ALL PASSED' : '❌ SOME FAILURES'}`);
  console.log(`  Duration: ${total}\n`);

  console.log('  Step                    | Result | Duration | Notes');
  console.log('  ────────────────────────┼────────┼──────────┼─────────────────');
  for (const r of results) {
    const step = r.step.padEnd(24);
    const res = r.pass ? '✅ PASS' : '❌ FAIL';
    const dur = (r.duration || 'N/A').toString().padEnd(8);
    const note = r.error ? `err: ${String(r.error).slice(0, 40)}` :
                 r.leaks ? `leaks: ${r.leaks}` :
                 r.reason || '';
    console.log(`  ${step} | ${res} | ${dur} | ${note}`);
  }

  console.log('\n  Security:');
  for (const r of results.filter(r => r.step === 'search_items' || r.step === 'get_item')) {
    if (r.leaks === 0) console.log(`    ${r.step}: 🔒 No secrets leaked`);
    else if (r.leaks) console.log(`    ${r.step}: 🚨 ${r.leaks} leak(s)!`);
  }
  console.log('    read_secret: Returns actual values (by design)');
  console.log('    ⚠️  No actual secret values printed in this report.\n');
  console.log('═══════════════════════════════════════════════════════════\n');
}

runTests().catch(e => { console.error('Fatal:', e); process.exit(1); });
