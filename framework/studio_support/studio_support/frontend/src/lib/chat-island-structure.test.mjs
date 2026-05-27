import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../components/ChatWindow.svelte', import.meta.url), 'utf8');

assert.match(source, /class="[^"]*chat-console/);
assert.match(source, /class="[^"]*chat-workbench/);
assert.match(source, /class="[^"]*chat-sidebar/);
assert.match(source, /class="[^"]*chat-session-list/);
assert.match(source, /class="[^"]*chat-main/);
assert.match(source, /class="[^"]*chat-toolbar/);
assert.match(source, /messages\.length === 0/);
assert.match(source, /class="[^"]*chat-prompt-grid/);
assert.match(source, /class="[^"]*chat-prompt-chip/);
assert.match(source, /class="[^"]*chat-composer/);
assert.match(source, /class="[^"]*select-shell/);
assert.match(source, /class="[^"]*select-icon/);

const promptGridIndex = source.indexOf('class="chat-prompt-grid"');
const emptyStateIndex = source.indexOf('class="chat-empty-state"');
assert.ok(promptGridIndex > emptyStateIndex, 'starter prompts should live inside the empty state block');
