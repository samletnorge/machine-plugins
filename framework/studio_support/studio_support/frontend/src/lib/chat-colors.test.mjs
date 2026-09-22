import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('../../../static/studio.css', import.meta.url), 'utf8');

function inheritsColor(selector) {
  return new RegExp(`${selector}[^{}]*\\{[^}]*color:\\s*inherit;`).test(css);
}

assert.ok(inheritsColor('\\.markdown-body p'), '.markdown-body p should inherit color');
assert.ok(inheritsColor('\\.markdown-body li'), '.markdown-body li should inherit color');
