import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('../../../static/studio.css', import.meta.url), 'utf8');

assert.match(css, /\.markdown-body p\s*\{[^}]*color:\s*inherit;/);
assert.match(css, /\.markdown-body li\s*\{[^}]*color:\s*inherit;/);
