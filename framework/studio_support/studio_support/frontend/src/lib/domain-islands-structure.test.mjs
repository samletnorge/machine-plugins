import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const domains = [
  { name: 'memory', title: 'Memory', target: 'memory-island', endpoint: '/api/memory/threads' },
  { name: 'rag', title: 'RAG', target: 'rag-island', endpoint: '/api/rag/pipelines' },
  { name: 'evals', title: 'Evals', target: 'evals-island', endpoint: '/api/evals/runs' },
  { name: 'storage', title: 'Storage', target: 'storage-island', endpoint: '/api/storage/files' },
  { name: 'observe', title: 'Observability', target: 'observe-island', endpoint: '/api/observe/traces' },
  { name: 'deploy', title: 'Deploy', target: 'deploy-island', endpoint: '/api/deploy/targets' },
  { name: 'auth', title: 'Auth', target: 'auth-island', endpoint: '/api/auth/keys' },
  { name: 'workspace', title: 'Workspace', target: 'workspace-island', endpoint: '/api/workspace/files' },
  { name: 'browser', title: 'Browser', target: 'browser-island', endpoint: '/api/browser/sessions' },
  { name: 'voice', title: 'Voice', target: 'voice-island', endpoint: '/api/voice/voices' },
  { name: 'pubsub', title: 'Pub/Sub', target: 'pubsub-island', endpoint: '/api/pubsub/events' }
];

const panel = readFileSync(new URL('../components/DomainPanel.svelte', import.meta.url), 'utf8');
const viteConfig = readFileSync(new URL('../../vite.config.ts', import.meta.url), 'utf8');

assert.match(panel, /import \{ getJson \} from '\.\.\/lib\/api'/);
assert.match(panel, /getJson<DomainPayload>\(endpoint\)/);
assert.match(panel, /installed/);
assert.match(panel, /not installed/);
assert.match(panel, /This surface is empty because its plugin is not installed/);
assert.match(panel, /class="[^"]*domain-table/);
assert.match(panel, /class="[^"]*domain-category/);
assert.match(panel, /<table/);
assert.match(panel, /item\.operations/);
assert.match(panel, /class="[^"]*domain-skeleton/);
assert.match(panel, /class="[^"]*domain-state error"[^>]*role="alert"/);
assert.match(panel, /class="[^"]*domain-stats/);
assert.match(panel, /data-label="Operations"/);
assert.match(panel, /aria-busy=\{loading\}/);
assert.match(panel, /<style>/);

for (const { name, title, target, endpoint } of domains) {
  const island = readFileSync(new URL(`../islands/${name}.ts`, import.meta.url), 'utf8');

  assert.match(island, /import DomainPanel from '\.\.\/components\/DomainPanel\.svelte'/);
  assert.match(island, new RegExp(`getElementById\\('${target}'\\)`));
  assert.match(island, new RegExp(`domain: '${name}'`));
  assert.match(island, new RegExp(`title: '${title.replace('/', '\\/')}'`));
  assert.ok(island.includes(endpoint), `${name} island should reference ${endpoint}`);
  assert.match(island, /target\.dataset\.endpoint/);
  assert.match(island, /mount\(DomainPanel/);

  assert.ok(
    viteConfig.includes(`${name}: resolve(__dirname, 'src/islands/${name}.ts')`),
    `vite.config.ts should register the ${name} island input`
  );
}

for (const legacy of ['chat', 'tools', 'workflows']) {
  assert.ok(
    viteConfig.includes(`${legacy}: resolve(__dirname, 'src/islands/${legacy}.ts')`),
    `vite.config.ts should keep the ${legacy} island input`
  );
}
