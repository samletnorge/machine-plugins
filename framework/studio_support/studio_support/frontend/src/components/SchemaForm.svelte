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
            <button type="button" class="result-copy" onclick={copyResult}>
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
    display: grid;
    gap: 1rem;
  }

  .schema-header {
    align-items: flex-start;
    margin-bottom: 0;
    padding-bottom: 0.9rem;
    border-bottom: 1px solid color-mix(in oklab, var(--border) 82%, transparent);
  }

  .schema-heading {
    display: grid;
    gap: 0.2rem;
    min-width: 0;
  }

  .schema-heading h3 {
    margin: 0;
    font-size: 1.15rem;
  }

  .schema-subtitle {
    margin: 0;
    max-width: 46rem;
    font-size: 0.86rem;
    color: var(--muted-foreground);
  }

  .schema-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    justify-content: flex-end;
  }

  .meta-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.6rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: color-mix(in oklab, var(--accent) 70%, transparent);
    font-size: 0.75rem;
    color: var(--foreground);
  }

  .meta-label {
    font-size: 0.62rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--muted-foreground);
  }

  .schema-form {
    display: grid;
    gap: 1rem;
  }

  .schema-fields {
    display: grid;
    gap: 0.85rem;
  }

  .schema-field {
    display: grid;
    gap: 0.35rem;
    padding: 0.85rem 0.95rem;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) + 0.15rem);
    background: color-mix(in oklab, var(--card) 78%, transparent);
  }

  .schema-field.invalid {
    border-color: color-mix(in oklab, oklch(0.65 0.19 25) 52%, var(--border));
    background: color-mix(in oklab, oklch(0.65 0.19 25) 7%, var(--card));
  }

  .field-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
  }

  .field-head label {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--foreground);
  }

  .required-badge {
    padding: 0.1rem 0.45rem;
    border: 1px dashed var(--border);
    border-radius: 999px;
    font-size: 0.62rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--muted-foreground);
  }

  .field-hint {
    margin: 0;
    font-size: 0.8rem;
    color: var(--muted-foreground);
  }

  .field-error {
    margin: 0;
    font-size: 0.8rem;
    color: oklch(0.72 0.17 25);
  }

  .schema-textarea {
    min-height: 6rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.85rem;
    resize: vertical;
  }

  .switch {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
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
    width: 2.4rem;
    height: 1.35rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: color-mix(in oklab, var(--muted) 82%, transparent);
    transition: background-color 140ms ease, border-color 140ms ease;
  }

  .switch-thumb {
    position: absolute;
    top: 50%;
    left: 0.16rem;
    width: 1rem;
    height: 1rem;
    border-radius: 50%;
    background: var(--foreground);
    transform: translateY(-50%);
    transition: left 140ms ease, background-color 140ms ease;
  }

  .switch input:checked + .switch-track {
    border-color: color-mix(in oklab, var(--primary) 52%, var(--border));
    background: color-mix(in oklab, var(--primary) 58%, var(--accent));
  }

  .switch input:checked + .switch-track .switch-thumb {
    left: calc(100% - 1.16rem);
    background: var(--primary-foreground);
  }

  .switch input:focus-visible + .switch-track {
    outline: 2px solid color-mix(in oklab, var(--ring) 72%, transparent);
    outline-offset: 2px;
  }

  .switch-label {
    font-size: 0.8rem;
    color: var(--muted-foreground);
    font-variant-numeric: tabular-nums;
  }

  .schema-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.7rem;
  }

  .schema-run {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
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
    font-size: 0.8rem;
  }

  .result-panel {
    display: grid;
    gap: 0.5rem;
  }

  .result-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
  }

  .result-copy {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.65rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: color-mix(in oklab, var(--accent) 72%, transparent);
    color: var(--foreground);
    font-size: 0.76rem;
    font-weight: 600;
    cursor: pointer;
  }

  .result-copy:hover,
  .result-copy:focus-visible {
    border-color: color-mix(in oklab, var(--primary) 40%, var(--border));
  }

  .result-body {
    margin: 0;
    max-height: 20rem;
    overflow: auto;
    padding: 0.9rem 1rem;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) + 0.15rem);
    background: color-mix(in oklab, var(--background) 68%, transparent);
    color: var(--foreground);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.84rem;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .result-body.result-error {
    border-color: color-mix(in oklab, oklch(0.65 0.19 25) 50%, var(--border));
    background: color-mix(in oklab, oklch(0.65 0.19 25) 10%, var(--card));
    color: oklch(0.78 0.16 25);
  }

  .schema-state {
    display: grid;
    gap: 0.5rem;
    justify-items: start;
    padding: 1.4rem;
    border: 1px dashed var(--border);
    border-radius: calc(var(--radius) + 0.25rem);
    background: color-mix(in oklab, var(--card) 60%, transparent);
  }

  .schema-state h4 {
    margin: 0;
  }

  .schema-state p {
    margin: 0;
    color: var(--muted-foreground);
  }

  .schema-state.error {
    border-style: solid;
    border-color: color-mix(in oklab, oklch(0.65 0.19 25) 46%, var(--border));
    background: color-mix(in oklab, oklch(0.65 0.19 25) 9%, var(--card));
  }

  .schema-retry {
    margin-top: 0.3rem;
    padding: 0.5rem 0.9rem;
    border: 1px solid color-mix(in oklab, var(--primary) 34%, var(--border));
    border-radius: calc(var(--radius) + 0.15rem);
    background: color-mix(in oklab, var(--primary) 14%, var(--accent));
    color: var(--foreground);
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
  }

  .schema-skeleton {
    display: grid;
    gap: 0.75rem;
  }

  .skeleton-field {
    height: 3.6rem;
    border-radius: calc(var(--radius) + 0.15rem);
    background: linear-gradient(
      90deg,
      color-mix(in oklab, var(--muted) 70%, transparent) 0%,
      color-mix(in oklab, var(--foreground) 12%, var(--muted)) 50%,
      color-mix(in oklab, var(--muted) 70%, transparent) 100%
    );
    background-size: 200% 100%;
    animation: schema-shimmer 1.5s ease-in-out infinite;
  }

  .skeleton-field.short {
    width: 60%;
  }

  @keyframes schema-shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
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

  @media (prefers-reduced-motion: reduce) {
    .skeleton-field,
    .icon.spin {
      animation: none;
    }
  }
</style>
