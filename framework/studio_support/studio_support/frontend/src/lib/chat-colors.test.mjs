import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('../../../static/studio.css', import.meta.url), 'utf8');

function ruleBody(selector) {
  const match = new RegExp(`${selector}\\s*\\{([^}]*)\\}`).exec(css);
  return match?.[1] ?? '';
}

// Graphite shell: the markdown container owns the text colour and resolves it
// from a theme token, so rendered content follows the active theme instead of
// hardcoding a palette value.
const container = ruleBody('\\.markdown-body');
assert.match(container, /color:\s*var\(--foreground\)/, '.markdown-body should colour text from a token');

for (const selector of ['\\.markdown-body p', '\\.markdown-body li']) {
  const body = ruleBody(selector);
  assert.doesNotMatch(body, /color:\s*(?:#|rgb|oklch|hsl)/, `${selector} should not hardcode colour`);
}
