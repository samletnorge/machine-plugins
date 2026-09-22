import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (relative) => readFileSync(new URL(relative, import.meta.url), 'utf8');

const domainPanel = read('../components/DomainPanel.svelte');
const chatWindow = read('../components/ChatWindow.svelte');
const dagViewer = read('../components/DAGViewer.svelte');
const schemaForm = read('../components/SchemaForm.svelte');
const viteConfig = read('../../vite.config.ts');

for (const [name, source] of [
  ['DomainPanel', domainPanel],
  ['ChatWindow', chatWindow],
  ['DAGViewer', dagViewer],
  ['SchemaForm', schemaForm]
]) {
  assert.match(source, /<style>/, `${name} should ship component-scoped styles`);
  const variableCount = (source.match(/var\(--/g) ?? []).length;
  assert.ok(variableCount >= 5, `${name} should theme itself with studio.css variables`);
  assert.match(source, /@media/, `${name} should include responsive rules`);
}

assert.match(domainPanel, /@media \(max-width: 640px\)/);
assert.match(domainPanel, /\.domain-table td::before/);
assert.match(domainPanel, /prefers-reduced-motion/);

assert.match(chatWindow, /class="[^"]*chat-avatar/);
assert.match(chatWindow, /class="[^"]*chat-time/);
assert.match(chatWindow, /class="[^"]*chat-typing/);
assert.match(chatWindow, /role="log"/);
assert.match(chatWindow, /position: sticky/);
assert.match(chatWindow, /prefers-reduced-motion/);

assert.match(dagViewer, /class="dag-canvas"/);
assert.match(chatWindow, /aria-busy=\{sending\}/);
assert.match(dagViewer, /role="img"/);
assert.match(dagViewer, /viewBox=/);
assert.match(dagViewer, /class="dag-edge"/);
assert.match(dagViewer, /class=\{`dag-node/);

assert.match(schemaForm, /executeEndpoint/);
assert.match(schemaForm, /class="schema-form"/);
assert.match(schemaForm, /class="schema-field"/);
assert.match(schemaForm, /aria-invalid=\{Boolean\(errors\[name\]\)\}/);
assert.match(schemaForm, /postJson<Record<string, unknown>>\(executeEndpoint/);

const islandNames = [
  'chat',
  'tools',
  'workflows',
  'memory',
  'rag',
  'evals',
  'storage',
  'observe',
  'deploy',
  'auth',
  'workspace',
  'browser',
  'voice',
  'pubsub'
];

for (const island of islandNames) {
  assert.ok(
    viteConfig.includes(`${island}: resolve(__dirname, 'src/islands/${island}.ts')`),
    `vite.config.ts should emit the ${island} island`
  );
}

assert.match(viteConfig, /studio-css-injected-by-js/);
