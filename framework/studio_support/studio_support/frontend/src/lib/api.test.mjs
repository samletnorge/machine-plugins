import assert from 'node:assert/strict';

import { putJson } from './api.ts';

const originalFetch = globalThis.fetch;

try {
  let request = null;
  globalThis.fetch = async (url, options) => {
    request = { url, options };
    return {
      ok: true,
      json: async () => ({ status: 'ok' })
    };
  };

  const payload = { tenant_slug: 'northwind', project_slug: 'fuel-ops' };
  const response = await putJson('/api/context', payload);

  assert.deepEqual(response, { status: 'ok' });
  assert.equal(request.url, '/api/context');
  assert.equal(request.options.method, 'PUT');
  assert.deepEqual(request.options.headers, {
    'Content-Type': 'application/json'
  });
  assert.equal(request.options.body, JSON.stringify(payload));

  globalThis.fetch = async () => ({
    ok: false,
    status: 409,
    json: async () => ({ detail: 'conflict' })
  });

  await assert.rejects(
    () => putJson('/api/context', payload),
    /Request failed: 409/
  );
} finally {
  globalThis.fetch = originalFetch;
}
