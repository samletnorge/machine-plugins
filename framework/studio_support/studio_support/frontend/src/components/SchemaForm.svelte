<script lang="ts">
  import { getJson, postJson } from '../lib/api';
  import type { JsonSchemaProperty, ToolDetail } from '../lib/types';

  interface Props {
    detailEndpoint: string;
    executeEndpoint?: string;
  }

  let { detailEndpoint, executeEndpoint = '' }: Props = $props();

  let detail = $state<ToolDetail | null>(null);
  let loadError = $state('');
  let loading = $state(true);
  let reloadToken = $state(0);
  let values = $state<Record<string, unknown>>({});
  let errors = $state<Record<string, string>>({});
  let running = $state(false);
  let result = $state<unknown>(null);
  let resultError = $state('');
  let hasExecuted = $state(false);
  let copied = $state(false);

  let properties = $derived(Object.entries(detail?.input_schema.properties ?? {}));
  let requiredNames = $derived(new Set(detail?.input_schema.required ?? []));
  let canRun = $derived(Boolean(executeEndpoint) && !running);

  const playIcon = `<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M6 4.5v11l9-5.5-9-5.5Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>`;
  const spinnerIcon = `<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.8" opacity="0.28"/><path d="M17 10a7 7 0 0 0-7-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;
  const copyIcon = `<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><rect x="7" y="7" width="9" height="9" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M13 7V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h1" stroke="currentColor" stroke-width="1.5"/></svg>`;
  const checkIcon = `<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m5 10.5 3.2 3.2L15 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  function fieldId(name: string) {
    return `schema-field-${name.replace(/[^a-zA-Z0-9_-]/g, '-')}`;
  }

  function controlKind(prop: JsonSchemaProperty) {
    if (prop.enum && prop.enum.length) return 'select';
    if (prop.type === 'boolean') return 'boolean';
    if (prop.type === 'number' || prop.type === 'integer') return 'number';
    if (prop.type === 'object') return 'textarea';
    if (prop.type === 'array' && prop.items?.type === 'object') return 'textarea';
    if (prop.type === 'array') return 'input';
    return 'input';
  }

  function inputType(prop: JsonSchemaProperty) {
    if (prop.format === 'date') return 'date';
    if (prop.format === 'date-time') return 'datetime-local';
    if (prop.format === 'email') return 'email';
    if (prop.format === 'uri' || prop.format === 'url') return 'url';
    if (prop.format === 'password') return 'password';
    return 'text';
  }

  function asText(value: unknown) {
    if (value === undefined || value === null) return '';
    return String(value);
  }

  function defaultsFor(source: ToolDetail) {
    const next: Record<string, unknown> = {};
    for (const [name, prop] of Object.entries(source.input_schema.properties ?? {})) {
      next[name] = prop.default ?? (prop.type === 'boolean' ? false : '');
    }
    return next;
  }

  function updateValue(name: string, value: unknown) {
    values = { ...values, [name]: value };
    if (errors[name]) {
      const next = { ...errors };
      delete next[name];
      errors = next;
    }
  }

  function serializeValue(prop: JsonSchemaProperty, raw: unknown): unknown {
    if (prop.type === 'boolean') return Boolean(raw);
    if (prop.type === 'number' || prop.type === 'integer') {
      if (raw === '' || raw === undefined || raw === null) return undefined;
      const parsed = Number(raw);
      return Number.isFinite(parsed) ? parsed : raw;
    }
    if (prop.type === 'array') {
      if (prop.items?.type === 'object') {
        const text = String(raw ?? '').trim();
        if (!text) return undefined;
        try {
          return JSON.parse(text);
        } catch {
          return raw;
        }
      }
      return String(raw ?? '')
        .split(',')
        .map((entry) => entry.trim())
        .filter(Boolean);
    }
    if (prop.type === 'object') {
      const text = String(raw ?? '').trim();
      if (!text) return undefined;
      try {
        return JSON.parse(text);
      } catch {
        return raw;
      }
    }
    return raw;
  }

  function validate() {
    const next: Record<string, string> = {};
    for (const [name, prop] of properties) {
      const value = values[name];
      if (requiredNames.has(name) && prop.type !== 'boolean') {
        if (value === '' || value === undefined || value === null) {
          next[name] = 'This field is required.';
          continue;
        }
      }
      if (prop.type === 'object' && typeof value === 'string' && value.trim()) {
        try {
          JSON.parse(value);
        } catch {
          next[name] = 'Enter valid JSON.';
        }
      }
      if (prop.type === 'array' && prop.items?.type === 'object' && typeof value === 'string' && value.trim()) {
        try {
          JSON.parse(value);
        } catch {
          next[name] = 'Enter a valid JSON array.';
        }
      }
    }
    errors = next;
    return Object.keys(next).length === 0;
  }

  function formatResult(value: unknown) {
    if (value === undefined || value === null) return '';
    if (typeof value === 'string') return value;
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }

  async function copyResult() {
    if (!navigator?.clipboard) return;
    try {
      await navigator.clipboard.writeText(formatResult(result));
      copied = true;
    } catch {
      copied = false;
    }
  }

  async function runTool() {
    if (!canRun) return;
    if (!validate()) return;
    running = true;
    resultError = '';
    try {
      const body: Record<string, unknown> = {};
      for (const [name, prop] of properties) {
        const value = serializeValue(prop, values[name]);
        if (value !== undefined) body[name] = value;
      }
      const data = await postJson<Record<string, unknown>>(executeEndpoint, body);
      result = data && typeof data === 'object' && 'result' in data ? data.result : data;
      hasExecuted = true;
      copied = false;
    } catch (error) {
      result = null;
      hasExecuted = true;
      resultError = error instanceof Error ? error.message : 'Execution failed';
    } finally {
      running = false;
    }
  }

  function resetValues() {
    if (detail) values = defaultsFor(detail);
    errors = {};
  }

  async function loadDetail() {
    loading = true;
    try {
      const payload = await getJson<ToolDetail>(detailEndpoint);
      detail = payload;
      values = defaultsFor(payload);
      errors = {};
      loadError = '';
    } catch (error) {
      loadError = error instanceof Error ? error.message : 'Failed to load tool detail';
    } finally {
      loading = false;
    }
  }

  function retry() {
    reloadToken += 1;
    void loadDetail();
  }

  $effect(() => {
    void reloadToken;
    void loadDetail();
  });
</script>

<section class="panel schema-panel" aria-busy={loading}>
  <header class="panel-header compact schema-header">
    <div class="schema-heading">
      <span class="eyebrow">Schema form</span>
      <h3>{detail?.name ?? 'Tool runner'}</h3>
      <p class="schema-subtitle">
        {detail?.description ?? (loading ? 'Loading tool schema…' : 'Run a registered tool from its JSON schema.')}
      </p>
    </div>
    {#if detail}
      <div class="schema-meta">
        <span class="meta-tag"><span class="meta-label">Owner</span>{detail.owner ?? 'runtime'}</span>
        <span class="meta-tag"><span class="meta-label">Ops</span>{detail.operations.join(', ') || '—'}</span>
      </div>
    {/if}
  </header>

  {#if loadError}
    <div class="schema-state error" role="alert">
      <h4>Unable to load tool</h4>
      <p>{loadError}</p>
      <button type="button" class="schema-retry" onclick={retry}>Try again</button>
    </div>
  {:else if loading}
    <div class="schema-skeleton" aria-hidden="true">
      <div class="skeleton-field"></div>
      <div class="skeleton-field"></div>
      <div class="skeleton-field short"></div>
    </div>
  {:else if detail}
    {#if properties.length === 0}
      <div class="schema-state">
        <h4>No inputs declared</h4>
        <p>This tool takes no structured input. You can still execute it with an empty payload.</p>
      </div>
    {/if}

    <form
      class="schema-form"
      onsubmit={(event) => {
        event.preventDefault();
        void runTool();
      }}
    >
      {#if properties.length > 0}
        <div class="schema-fields">
          {#each properties as [name, prop] (name)}
            {@const id = fieldId(name)}
            {@const isRequired = requiredNames.has(name)}
            {@const kind = controlKind(prop)}
            <div class="schema-field" class:invalid={Boolean(errors[name])}>
              <div class="field-head">
                <label for={id}>{prop.title || name}</label>
                {#if isRequired}<span class="required-badge">required</span>{/if}
              </div>
              {#if prop.description}
                <p class="field-hint" id={`${id}-hint`}>{prop.description}</p>
              {:else if prop.type === 'array'}
                <p class="field-hint" id={`${id}-hint`}>{prop.items?.type === 'object' ? 'Provide a JSON array.' : 'Comma-separated values.'}</p>
              {/if}

              {#if kind === 'boolean'}
                <label class="switch" for={id}>
                  <input
                    id={id}
                    type="checkbox"
                    checked={Boolean(values[name])}
                    aria-describedby={prop.description ? `${id}-hint` : undefined}
                    onchange={(event) => updateValue(name, event.currentTarget.checked)}
                  />
                  <span class="switch-track" aria-hidden="true"><span class="switch-thumb"></span></span>
                  <span class="switch-label">{values[name] ? 'true' : 'false'}</span>
                </label>
              {:else if kind === 'select'}
                <select
                  id={id}
                  class="control-input"
                  value={asText(values[name])}
                  aria-required={isRequired}
                  aria-invalid={Boolean(errors[name])}
                  aria-describedby={prop.description ? `${id}-hint` : undefined}
                  onchange={(event) => updateValue(name, event.currentTarget.value)}
                >
                  <option value="">Select an option…</option>
                  {#each prop.enum ?? [] as option (String(option))}
                    <option value={String(option)}>{String(option)}</option>
                  {/each}
                </select>
              {:else if kind === 'textarea'}
                <textarea
                  id={id}
                  class="control-input schema-textarea"
                  rows="4"
                  spellcheck="false"
                  value={asText(values[name])}
                  aria-required={isRequired}
                  aria-invalid={Boolean(errors[name])}
                  aria-describedby={prop.description ? `${id}-hint` : undefined}
                  oninput={(event) => updateValue(name, event.currentTarget.value)}
                ></textarea>
              {:else if kind === 'number'}
                <input
                  id={id}
                  class="control-input"
                  type="number"
                  value={asText(values[name])}
                  min={prop.minimum}
                  max={prop.maximum}
                  step="any"
                  aria-required={isRequired}
                  aria-invalid={Boolean(errors[name])}
                  aria-describedby={prop.description ? `${id}-hint` : undefined}
                  oninput={(event) => updateValue(name, event.currentTarget.value)}
                />
              {:else}
                <input
                  id={id}
                  class="control-input"
                  type={inputType(prop)}
                  value={asText(values[name])}
                  placeholder={prop.example != null ? String(prop.example) : ''}
                  aria-required={isRequired}
                  aria-invalid={Boolean(errors[name])}
                  aria-describedby={prop.description ? `${id}-hint` : undefined}
                  oninput={(event) => updateValue(name, event.currentTarget.value)}
                />
              {/if}

              {#if errors[name]}
                <p class="field-error" role="alert">{errors[name]}</p>
              {/if}
            </div>
          {/each}
        </div>
      {/if}

      <div class="schema-actions">
        <button type="submit" class="primary-button schema-run" disabled={!canRun}>
          <span class="icon" class:spin={running}>{@html running ? spinnerIcon : playIcon}</span>
          <span>{running ? 'Running…' : 'Run tool'}</span>
        </button>
        <button type="button" class="secondary-button schema-reset" onclick={resetValues} disabled={running}>Reset</button>
        {#if !executeEndpoint}
          <span class="schema-note muted">Execution endpoint unavailable for this tool.</span>
        {/if}
      </div>
    </form>

    {#if resultError || hasExecuted}
      <div class="result-panel">
        <div class="result-head">
          <span class="eyebrow">Result</span>
          {#if hasExecuted && !resultError}
            <button type="button" class="result-copy" class:copied={copied} onclick={copyResult}>
              <span class="icon">{@html copied ? checkIcon : copyIcon}</span>
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          {/if}
        </div>
        {#if resultError}
          <pre class="result-body result-error" role="alert">{resultError}</pre>
        {:else}
          <pre class="result-body">{formatResult(result) || 'No output returned.'}</pre>
        {/if}
      </div>
    {/if}
  {/if}
</section>

<style>
  .schema-panel {
    --hair: color-mix(in oklab, var(--border) 100%, transparent);
    --r: var(--radius);
    --mono: var(--font-mono, ui-monospace, SFMono-Regular, 'JetBrains Mono', Menlo, Consolas, monospace);
    display: grid;
    gap: 1rem;
    background: transparent;
    border: 0;
    border-radius: 0;
  }

  .schema-panel > :not(.schema-header) {
    margin-inline: 18px;
  }

  .schema-panel > :last-child {
    margin-bottom: 18px;
  }

  .schema-header {
    align-items: flex-start;
    margin-bottom: 0;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--hair);
  }

  .schema-heading {
    display: grid;
    gap: 0.25rem;
    min-width: 0;
  }

  .schema-heading h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: -0.01em;
  }

  .schema-subtitle {
    margin: 0;
    max-width: 46rem;
    font-size: 0.8125rem;
    line-height: 1.5;
    color: var(--muted-foreground);
  }

  .schema-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    justify-content: flex-end;
  }

  .meta-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.2rem 0.5rem;
    border: 1px solid var(--hair);
    border-radius: var(--r);
    background: transparent;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--foreground);
  }

  .meta-label {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted-foreground);
  }

  .schema-form {
    display: grid;
    gap: 1rem;
  }

  .schema-fields {
    display: grid;
    gap: 0.75rem;
  }

  .schema-field {
    display: grid;
    gap: 0.375rem;
    padding: 0.75rem;
    border: 1px solid var(--hair);
    border-radius: var(--r);
    transition: border-color 120ms ease;
  }

  .schema-field.invalid {
    border-color: color-mix(in oklab, var(--danger) 55%, var(--border));
  }

  .field-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .field-head label {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted-foreground);
  }

  .required-badge {
    padding: 0.1rem 0.4rem;
    border: 1px solid color-mix(in oklab, var(--danger) 42%, var(--border));
    border-radius: 999px;
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: color-mix(in oklab, var(--danger) 88%, var(--foreground));
  }

  .field-hint {
    margin: 0;
    font-size: 0.75rem;
    color: var(--muted-foreground);
  }

  .field-error {
    margin: 0;
    font-family: var(--mono);
    font-size: 0.75rem;
    color: color-mix(in oklab, var(--danger) 88%, var(--foreground));
  }

  .control-input {
    width: 100%;
    padding: 0.5rem 0.625rem;
    border: 1px solid var(--hair);
    border-radius: var(--r);
    background: var(--input);
    color: var(--foreground);
    font-size: 0.875rem;
    transition: border-color 120ms ease, box-shadow 160ms ease;
  }

  .control-input:focus-visible {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--ring) 28%, transparent);
  }

  .control-input[aria-invalid='true'] {
    border-color: color-mix(in oklab, var(--danger) 55%, var(--border));
  }

  .schema-textarea {
    min-height: 6rem;
    font-family: var(--mono);
    font-size: 0.8125rem;
    resize: vertical;
  }

  .switch {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
  }

  .switch input {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
  }

  .switch-track {
    position: relative;
    width: 2.25rem;
    height: 1.25rem;
    border: 1px solid var(--hair);
    border-radius: 999px;
    background: color-mix(in oklab, var(--muted) 82%, transparent);
    transition: background-color 120ms ease, border-color 120ms ease;
  }

  .switch-thumb {
    position: absolute;
    top: 50%;
    left: 0.15rem;
    width: 0.9rem;
    height: 0.9rem;
    border-radius: 50%;
    background: var(--muted-foreground);
    transform: translateY(-50%);
    transition: left 120ms ease, background-color 120ms ease;
  }

  .switch input:checked + .switch-track {
    border-color: color-mix(in oklab, var(--primary) 55%, var(--border));
    background: color-mix(in oklab, var(--primary) 55%, transparent);
  }

  .switch input:checked + .switch-track .switch-thumb {
    left: calc(100% - 1.05rem);
    background: var(--primary-foreground);
  }

  .switch input:focus-visible + .switch-track {
    outline: none;
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--ring) 30%, transparent);
  }

  .switch-label {
    font-family: var(--mono);
    font-size: 0.75rem;
    color: var(--muted-foreground);
    font-variant-numeric: tabular-nums;
  }

  .schema-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
  }

  .primary-button.schema-run,
  .secondary-button.schema-reset {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    padding: 0.5rem 0.875rem;
    border: 1px solid var(--hair);
    border-radius: var(--r);
    font-size: 0.8125rem;
    font-weight: 600;
    cursor: pointer;
    box-shadow: none;
    transition: border-color 120ms ease, background-color 120ms ease, filter 120ms ease, opacity 120ms ease, transform 120ms ease;
  }

  .primary-button.schema-run:active:not(:disabled),
  .secondary-button.schema-reset:active:not(:disabled) {
    transform: scale(0.98);
  }

  .primary-button.schema-run {
    border-color: transparent;
    background: var(--primary);
    color: var(--primary-foreground);
  }

  .primary-button.schema-run:hover:not(:disabled) {
    filter: brightness(1.06);
  }

  .secondary-button.schema-reset {
    background: transparent;
    color: var(--foreground);
  }

  .secondary-button.schema-reset:hover:not(:disabled) {
    border-color: color-mix(in oklab, var(--primary) 45%, var(--border));
    background: color-mix(in oklab, var(--primary) 8%, transparent);
  }

  .primary-button.schema-run:disabled,
  .secondary-button.schema-reset:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .primary-button.schema-run:focus-visible,
  .secondary-button.schema-reset:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--ring) 30%, transparent);
  }

  .icon {
    display: inline-flex;
    width: 1rem;
    height: 1rem;
  }

  .icon :global(svg) {
    width: 100%;
    height: 100%;
  }

  .icon.spin {
    animation: schema-spin 900ms linear infinite;
  }

  .schema-note {
    font-size: 0.75rem;
  }

  .result-panel {
    display: grid;
    gap: 0.5rem;
    animation: schema-result-in 220ms ease-out backwards;
  }

  .result-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .result-copy {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.6rem;
    border: 1px solid var(--hair);
    border-radius: var(--r);
    background: transparent;
    color: var(--foreground);
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    cursor: pointer;
    transition: border-color 120ms ease, background-color 120ms ease, transform 120ms ease;
  }

  .result-copy:hover {
    border-color: color-mix(in oklab, var(--primary) 45%, var(--border));
    background: color-mix(in oklab, var(--primary) 8%, transparent);
  }

  .result-copy:active {
    transform: scale(0.98);
  }

  .result-copy .icon {
    transition: transform 160ms ease;
  }

  .result-copy.copied .icon {
    animation: schema-check-pop 220ms ease-out;
  }

  .result-copy:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--ring) 30%, transparent);
  }

  .result-body {
    margin: 0;
    max-height: 20rem;
    overflow: auto;
    padding: 0.75rem 0.875rem;
    border: 1px solid var(--hair);
    border-radius: var(--r);
    background: color-mix(in oklab, var(--background) 78%, transparent);
    color: var(--foreground);
    font-family: var(--mono);
    font-size: 0.8125rem;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .result-body.result-error {
    border-color: color-mix(in oklab, var(--danger) 52%, var(--border));
    background: color-mix(in oklab, var(--danger) 8%, transparent);
    color: color-mix(in oklab, var(--danger) 88%, var(--foreground));
  }

  .schema-state {
    display: grid;
    gap: 0.5rem;
    justify-items: start;
    padding: 1rem;
    border: 1px solid var(--hair);
    border-radius: var(--r);
  }

  .schema-state h4 {
    margin: 0;
    font-size: 0.9375rem;
    font-weight: 600;
  }

  .schema-state p {
    margin: 0;
    color: var(--muted-foreground);
    line-height: 1.55;
  }

  .schema-state.error {
    border-color: color-mix(in oklab, var(--danger) 52%, var(--border));
    background: color-mix(in oklab, var(--danger) 8%, transparent);
  }

  .schema-retry {
    margin-top: 0.25rem;
    padding: 0.4rem 0.7rem;
    border: 1px solid color-mix(in oklab, var(--primary) 48%, var(--border));
    border-radius: var(--r);
    background: transparent;
    color: var(--foreground);
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    cursor: pointer;
    transition: border-color 120ms ease, background-color 120ms ease, box-shadow 120ms ease;
  }

  .schema-retry:hover {
    border-color: var(--primary);
    background: color-mix(in oklab, var(--primary) 10%, transparent);
  }

  .schema-retry:focus-visible {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--ring) 30%, transparent);
  }

  .schema-skeleton {
    display: grid;
    gap: 0.75rem;
  }

  .skeleton-field {
    height: 3.5rem;
    border-radius: var(--r);
    background: color-mix(in oklab, var(--muted) 82%, transparent);
    animation: schema-pulse 1.4s ease-in-out infinite;
  }

  .skeleton-field.short {
    width: 60%;
  }

  @keyframes schema-pulse {
    0%,
    100% {
      opacity: 0.45;
    }
    50% {
      opacity: 1;
    }
  }

  @keyframes schema-spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  @keyframes schema-result-in {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  @keyframes schema-check-pop {
    0% {
      opacity: 0;
      transform: scale(0.5) rotate(-12deg);
    }
    60% {
      opacity: 1;
      transform: scale(1.12) rotate(3deg);
    }
    100% {
      opacity: 1;
      transform: scale(1) rotate(0deg);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .skeleton-field,
    .icon.spin,
    .result-panel,
    .result-copy.copied .icon {
      animation: none;
    }

    .schema-field,
    .control-input,
    .switch-track,
    .switch-thumb,
    .primary-button.schema-run,
    .secondary-button.schema-reset,
    .result-copy,
    .result-copy .icon,
    .schema-retry {
      transition: none;
    }

    .primary-button.schema-run:active:not(:disabled),
    .secondary-button.schema-reset:active:not(:disabled),
    .result-copy:active {
      transform: none;
    }
  }
</style>
