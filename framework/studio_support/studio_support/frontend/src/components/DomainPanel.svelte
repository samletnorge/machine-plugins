<script lang="ts">
  import { getJson } from '../lib/api';
  import type { DomainPayload } from '../lib/types';

  interface Props {
    domain: string;
    title: string;
    endpoint: string;
  }

  let { domain, title, endpoint }: Props = $props();

  let payload = $state<DomainPayload | null>(null);
  let loadError = $state('');
  let loading = $state(true);
  let reloadToken = $state(0);

  let categories = $derived.by(() =>
    Object.entries(payload?.categories ?? {}).filter(([, items]) => items.length > 0)
  );

  let totalItems = $derived.by(() =>
    Object.values(payload?.categories ?? {}).reduce((sum, items) => sum + items.length, 0)
  );

  let totalOperations = $derived.by(() =>
    Object.values(payload?.categories ?? {})
      .flat()
      .reduce((sum, item) => sum + (item.operations?.length ?? 0), 0)
  );

  let owners = $derived.by(() => {
    const unique = new Set<string>();
    for (const item of Object.values(payload?.categories ?? {}).flat()) {
      if (item.owner) unique.add(item.owner);
    }
    return unique.size;
  });

  let shownCategories = $state(0);
  let shownResources = $state(0);
  let shownOperations = $state(0);
  let shownOwners = $state(0);

  function prefersReducedMotion() {
    return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false;
  }

  function countUp(target: number, apply: (value: number) => void) {
    if (typeof window === 'undefined' || prefersReducedMotion()) {
      apply(target);
      return () => {};
    }
    const duration = 220;
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      apply(Math.round(target * eased));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }

  $effect(() => {
    const stopCategories = countUp(categories.length, (value) => (shownCategories = value));
    const stopResources = countUp(totalItems, (value) => (shownResources = value));
    const stopOperations = countUp(totalOperations, (value) => (shownOperations = value));
    const stopOwners = countUp(owners, (value) => (shownOwners = value));
    return () => {
      stopCategories();
      stopResources();
      stopOperations();
      stopOwners();
    };
  });

  async function loadDomain() {
    loading = true;
    try {
      payload = await getJson<DomainPayload>(endpoint);
      loadError = '';
    } catch (error) {
      loadError = error instanceof Error ? error.message : `Failed to load ${domain}`;
    } finally {
      loading = false;
    }
  }

  function retry() {
    reloadToken += 1;
    void loadDomain();
  }

  $effect(() => {
    void reloadToken;
    void loadDomain();
  });
</script>

<section class="panel domain-panel" data-domain={domain} aria-busy={loading}>
  <header class="panel-header compact domain-header">
    <div class="domain-heading">
      <span class="eyebrow">Control plane</span>
      <h3>{title}</h3>
      <p class="domain-subtitle">
        {#if payload && payload.installed}
          {totalItems} resource{totalItems === 1 ? '' : 's'} across {categories.length} categor{categories.length === 1 ? 'y' : 'ies'}
        {:else if loading}
          Reading the active runtime registry…
        {:else}
          Runtime registry view for the {title} domain
        {/if}
      </p>
    </div>
    <div class="domain-header-meta" aria-live="polite">
      {#if loading}
        <span class="status-tag">loading…</span>
      {:else if payload}
        <span class="status-tag" class:installed={payload.installed} class:missing={!payload.installed}>
          <span class="status-dot" aria-hidden="true"></span>
          {payload.installed ? 'installed' : 'not installed'}
        </span>
      {/if}
    </div>
  </header>

  {#if loadError}
    <div class="domain-state error" role="alert">
      <span class="state-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none">
          <path d="M12 8v5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
          <circle cx="12" cy="16.4" r="1.1" fill="currentColor" />
          <path d="M10.3 3.9 2.7 17.2a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
        </svg>
      </span>
      <h4>Unable to load {title}</h4>
      <p class="state-copy">{loadError}</p>
      <button type="button" class="domain-retry" onclick={retry}>Try again</button>
    </div>
  {:else if loading}
    <div class="domain-skeleton" aria-hidden="true">
      <div class="skeleton-line skeleton-stat"></div>
      <div class="skeleton-category">
        <div class="skeleton-line skeleton-head"></div>
        {#each [0, 1, 2] as row (row)}
          <div class="skeleton-line" style={`width: ${[92, 78, 84][row]}%`}></div>
        {/each}
      </div>
      <div class="skeleton-category">
        <div class="skeleton-line skeleton-head"></div>
        {#each [0, 1] as row (row)}
          <div class="skeleton-line" style={`width: ${[86, 70][row]}%`}></div>
        {/each}
      </div>
    </div>
  {:else if payload && !payload.installed}
    <div class="domain-state empty">
      <span class="state-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none">
          <path d="M4 8.5 12 4l8 4.5v7L12 20l-8-4.5v-7Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
          <path d="M4 8.5 12 13m0 0 8-4.5M12 13v7" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
        </svg>
      </span>
      <h4>Nothing installed yet</h4>
      <p class="state-copy">This surface is empty because its plugin is not installed in the active runtime.</p>
      <p class="state-copy muted-hint">Install the plugin, then reload this page to see its registered resources.</p>
    </div>
  {:else if payload && categories.length === 0}
    <div class="domain-state empty">
      <span class="state-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none">
          <circle cx="11" cy="11" r="6" stroke="currentColor" stroke-width="1.6" />
          <path d="m20 20-3.5-3.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
        </svg>
      </span>
      <h4>No resources registered</h4>
      <p class="state-copy">The runtime reports this domain as installed but exposes no resources yet.</p>
    </div>
  {:else if payload}
    <div class="domain-stats">
      <div class="domain-stat" style="--enter-index: 0">
        <span class="stat-label">Categories</span>
        <strong>{shownCategories}</strong>
      </div>
      <div class="domain-stat" style="--enter-index: 1">
        <span class="stat-label">Resources</span>
        <strong>{shownResources}</strong>
      </div>
      <div class="domain-stat" style="--enter-index: 2">
        <span class="stat-label">Operations</span>
        <strong>{shownOperations}</strong>
      </div>
      <div class="domain-stat" style="--enter-index: 3">
        <span class="stat-label">Owners</span>
        <strong>{owners ? shownOwners : '—'}</strong>
      </div>
    </div>

    {#each categories as [category, items], categoryIndex (category)}
      <section class="domain-category" style={`--enter-index:${categoryIndex}`}>
        <div class="domain-category-head">
          <h4>{category}</h4>
          <span class="count-badge">{items.length}</span>
        </div>
        <div class="domain-table-wrap">
          <table class="domain-table">
            <caption class="sr-only">{title} {category} resources</caption>
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Owner</th>
                <th scope="col">Description</th>
                <th scope="col">Operations</th>
              </tr>
            </thead>
            <tbody>
              {#each items as item, rowIndex (item.name)}
                <tr style={`--enter-index:${categoryIndex * 4 + rowIndex}`}>
                  <td data-label="Name"><span class="domain-name">{item.name}</span></td>
                  <td data-label="Owner">
                    {#if item.owner}
                      <span class="tag owner">{item.owner}</span>
                    {:else}
                      <span class="tag muted">runtime</span>
                    {/if}
                  </td>
                  <td data-label="Description">{item.description ?? '—'}</td>
                  <td data-label="Operations">
                    {#if item.operations?.length}
                      <span class="tag-list">
                        {#each item.operations ?? [] as operation (operation)}
                          <span class="tag operation">{operation}</span>
                        {/each}
                      </span>
                    {:else}
                      <span class="tag muted">—</span>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/each}
  {/if}
</section>

<style>
  .domain-panel {
    --hair: color-mix(in oklab, var(--border) 100%, transparent);
    --r: var(--radius);
    --mono: var(--font-mono, ui-monospace, SFMono-Regular, 'JetBrains Mono', Menlo, Consolas, monospace);
    display: grid;
    gap: 1rem;
    position: relative;
    background: transparent;
    border: 0;
    border-radius: 0;
  }

  .domain-panel > :not(.domain-header) {
    margin-inline: 18px;
  }

  .domain-panel > :last-child {
    margin-bottom: 18px;
  }

  .domain-header {
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 0;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--hair);
  }

  .domain-heading {
    display: grid;
    gap: 0.25rem;
    min-width: 0;
  }

  .domain-heading h3 {
    margin: 0;
    font-family: var(--font-sans);
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: -0.01em;
  }

  .domain-subtitle {
    margin: 0;
    font-size: 0.8125rem;
    line-height: 1.5;
    color: var(--muted-foreground);
  }

  .domain-header-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    justify-content: flex-end;
  }

  .status-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.2rem 0.5rem;
    border-radius: var(--r);
    border: 1px solid var(--hair);
    background: transparent;
    color: var(--muted-foreground);
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    white-space: nowrap;
    transition: border-color 120ms ease, color 120ms ease;
  }

  .status-tag.installed {
    color: var(--foreground);
    border-color: color-mix(in oklab, var(--primary) 48%, var(--border));
  }

  .status-tag.missing {
    border-style: dashed;
  }

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--muted-foreground);
  }

  .status-tag.installed .status-dot {
    background: var(--primary);
  }

  .domain-stats {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0;
    border: 1px solid var(--hair);
    border-radius: var(--r);
    overflow: hidden;
  }

  .domain-stat {
    display: grid;
    gap: 0.125rem;
    padding: 0.625rem 0.75rem;
    border-left: 1px solid var(--hair);
    animation: domain-enter 220ms ease-out backwards;
    animation-delay: calc(var(--enter-index, 0) * 45ms);
  }

  .domain-stat:first-child {
    border-left: 0;
  }

  .stat-label {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted-foreground);
  }

  .domain-stat strong {
    font-family: var(--mono);
    font-size: 1rem;
    font-weight: 600;
    color: var(--foreground);
    font-variant-numeric: tabular-nums;
  }

  .domain-category {
    display: grid;
    gap: 0.5rem;
    padding: 0;
    animation: domain-enter 220ms ease-out backwards;
    animation-delay: calc(var(--enter-index, 0) * 45ms);
  }

  .domain-category-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .domain-category-head h4 {
    margin: 0;
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted-foreground);
  }

  .count-badge {
    min-width: 1.5rem;
    padding: 0.1rem 0.4rem;
    text-align: center;
    border-radius: var(--r);
    border: 1px solid var(--hair);
    background: transparent;
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    color: var(--muted-foreground);
    font-variant-numeric: tabular-nums;
  }

  .domain-table-wrap {
    overflow-x: auto;
    border: 1px solid var(--hair);
    border-radius: var(--r);
  }

  .domain-table {
    width: 100%;
    border-collapse: collapse;
    border: 0;
    border-radius: 0;
    font-size: 0.8125rem;
  }

  .domain-table th {
    padding: 0.5rem 0.75rem;
    text-align: left;
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted-foreground);
    background: transparent;
    border-bottom: 1px solid var(--hair);
    white-space: nowrap;
  }

  .domain-table td {
    height: 44px;
    padding: 0 0.75rem;
    vertical-align: middle;
    color: var(--muted-foreground);
    border-bottom: 1px solid var(--hair);
  }

  .domain-table tbody tr:last-child td {
    border-bottom: 0;
  }

  .domain-table tbody tr {
    transition: background-color 120ms ease;
    animation: domain-row-enter 200ms ease-out backwards;
    animation-delay: calc(var(--enter-index, 0) * 30ms);
  }

  .domain-table tbody tr:hover {
    background: color-mix(in oklab, var(--muted) 55%, transparent);
  }

  .domain-table tbody td:first-child {
    border-left: 2px solid transparent;
    transition: border-color 140ms ease;
  }

  .domain-table tbody tr:hover td:first-child {
    border-left-color: var(--primary);
  }

  .domain-name {
    font-family: var(--mono);
    font-weight: 500;
    color: var(--foreground);
  }

  .tag-list {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.25rem;
  }

  .tag {
    display: inline-flex;
    align-items: center;
    padding: 0.15rem 0.45rem;
    border-radius: 999px;
    border: 1px solid var(--hair);
    background: transparent;
    color: var(--muted-foreground);
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.02em;
    white-space: nowrap;
  }

  .tag.owner {
    color: var(--foreground);
    border-color: color-mix(in oklab, var(--ring) 42%, var(--border));
  }

  .tag.operation {
    color: var(--foreground);
    border-color: color-mix(in oklab, var(--primary) 40%, var(--border));
    transition: transform 140ms ease, border-color 140ms ease, background-color 140ms ease;
  }

  .tag.operation:hover {
    transform: translateY(-1px);
    border-color: var(--primary);
    background: color-mix(in oklab, var(--primary) 10%, transparent);
  }

  .tag.muted {
    opacity: 0.6;
  }

  .domain-state {
    display: grid;
    gap: 0.5rem;
    justify-items: start;
    padding: 1rem;
    border: 1px solid var(--hair);
    border-radius: var(--r);
  }

  .domain-state h4 {
    margin: 0;
    font-size: 0.9375rem;
    font-weight: 600;
  }

  .domain-state p {
    margin: 0;
    max-width: 42rem;
    line-height: 1.55;
  }

  .domain-state .state-copy {
    font-size: 0.8125rem;
    color: var(--muted-foreground);
  }

  .domain-state .muted-hint {
    font-size: 0.75rem;
    opacity: 0.82;
  }

  .domain-state.error {
    border-color: color-mix(in oklab, var(--danger) 52%, var(--border));
    background: color-mix(in oklab, var(--danger) 8%, transparent);
  }

  .state-icon {
    display: inline-flex;
    width: 1.25rem;
    height: 1.25rem;
    color: var(--muted-foreground);
  }

  .state-icon svg {
    width: 100%;
    height: 100%;
  }

  .domain-state.error .state-icon {
    color: var(--danger);
  }

  .domain-retry {
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

  .domain-retry:hover {
    border-color: var(--primary);
    background: color-mix(in oklab, var(--primary) 10%, transparent);
  }

  .domain-retry:focus-visible {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--ring) 30%, transparent);
  }

  .domain-skeleton {
    display: grid;
    gap: 0.75rem;
  }

  .skeleton-category {
    display: grid;
    gap: 0.5rem;
  }

  .skeleton-line {
    height: 0.75rem;
    border-radius: var(--r);
    background: color-mix(in oklab, var(--muted) 82%, transparent);
    animation: domain-pulse 1.4s ease-in-out infinite;
  }

  .skeleton-stat {
    width: 12rem;
    height: 1rem;
  }

  .skeleton-head {
    width: 9rem;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
    border: 0;
  }

  @keyframes domain-pulse {
    0%,
    100% {
      opacity: 0.45;
    }
    50% {
      opacity: 1;
    }
  }

  @keyframes domain-enter {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  @keyframes domain-row-enter {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .skeleton-line,
    .domain-stat,
    .domain-category,
    .domain-table tbody tr {
      animation: none;
    }

    .domain-retry,
    .status-tag,
    .domain-table tbody tr,
    .domain-table tbody td:first-child,
    .tag.operation {
      transition: none;
    }

    .tag.operation:hover {
      transform: none;
    }
  }

  @media (max-width: 720px) {
    .domain-stats {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .domain-stat:nth-child(3) {
      border-left: 0;
    }

    .domain-stat:nth-child(n + 3) {
      border-top: 1px solid var(--hair);
    }
  }

  @media (max-width: 640px) {
    .domain-table-wrap {
      border: 0;
      overflow: visible;
    }

    .domain-table,
    .domain-table tbody,
    .domain-table tr,
    .domain-table td {
      display: block;
      width: 100%;
    }

    .domain-table thead {
      display: none;
    }

    .domain-table tr {
      margin-bottom: 0.5rem;
      padding: 0.5rem 0.75rem;
      border: 1px solid var(--hair);
      border-radius: var(--r);
    }

    .domain-table tbody tr:hover {
      background: transparent;
    }

    .domain-table td {
      display: grid;
      grid-template-columns: 6rem minmax(0, 1fr);
      gap: 0.5rem;
      align-items: start;
      height: auto;
      padding: 0.375rem 0;
      border: 0;
      border-left: 0;
    }

    .domain-table td::before {
      content: attr(data-label);
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: var(--muted-foreground);
    }
  }
</style>
