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
      <div class="domain-stat">
        <span class="stat-label">Categories</span>
        <strong>{categories.length}</strong>
      </div>
      <div class="domain-stat">
        <span class="stat-label">Resources</span>
        <strong>{totalItems}</strong>
      </div>
      <div class="domain-stat">
        <span class="stat-label">Operations</span>
        <strong>{totalOperations}</strong>
      </div>
      <div class="domain-stat">
        <span class="stat-label">Owners</span>
        <strong>{owners || '—'}</strong>
      </div>
    </div>

    {#each categories as [category, items] (category)}
      <section class="domain-category">
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
              {#each items as item (item.name)}
                <tr>
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
    display: grid;
    gap: 1.1rem;
    position: relative;
  }

  .domain-header {
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 0;
    padding-bottom: 0.9rem;
    border-bottom: 1px solid color-mix(in oklab, var(--border) 82%, transparent);
  }

  .domain-heading {
    display: grid;
    gap: 0.2rem;
    min-width: 0;
  }

  .domain-heading h3 {
    margin: 0;
    font-size: 1.15rem;
    letter-spacing: -0.01em;
  }

  .domain-subtitle {
    margin: 0;
    font-size: 0.86rem;
    color: var(--muted-foreground);
  }

  .domain-header-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    justify-content: flex-end;
  }

  .status-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.42rem;
    padding: 0.32rem 0.68rem;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: color-mix(in oklab, var(--accent) 70%, transparent);
    color: var(--muted-foreground);
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: lowercase;
    white-space: nowrap;
  }

  .status-tag.installed {
    color: var(--foreground);
    border-color: color-mix(in oklab, var(--primary) 42%, var(--border));
    background: color-mix(in oklab, var(--primary) 16%, var(--accent));
  }

  .status-tag.missing {
    border-style: dashed;
  }

  .status-dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 50%;
    background: var(--muted-foreground);
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--muted-foreground) 16%, transparent);
  }

  .status-tag.installed .status-dot {
    background: var(--primary);
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--primary) 22%, transparent);
  }

  .domain-stats {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.7rem;
  }

  .domain-stat {
    display: grid;
    gap: 0.15rem;
    padding: 0.7rem 0.8rem;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) + 0.15rem);
    background: color-mix(in oklab, var(--card) 82%, transparent);
  }

  .stat-label {
    font-size: 0.67rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted-foreground);
  }

  .domain-stat strong {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--foreground);
  }

  .domain-category {
    display: grid;
    gap: 0.55rem;
  }

  .domain-category-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
  }

  .domain-category-head h4 {
    margin: 0;
    font-size: 0.92rem;
    letter-spacing: 0.01em;
    text-transform: capitalize;
  }

  .count-badge {
    min-width: 1.6rem;
    padding: 0.15rem 0.5rem;
    text-align: center;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: color-mix(in oklab, var(--accent) 75%, transparent);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--muted-foreground);
  }

  .domain-table-wrap {
    overflow-x: auto;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) + 0.2rem);
    background: color-mix(in oklab, var(--card) 72%, transparent);
  }

  .domain-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
  }

  .domain-table th {
    padding: 0.6rem 0.8rem;
    text-align: left;
    font-size: 0.67rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--muted-foreground);
    background: color-mix(in oklab, var(--accent) 45%, transparent);
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }

  .domain-table td {
    padding: 0.65rem 0.8rem;
    vertical-align: top;
    color: var(--muted-foreground);
    border-bottom: 1px solid color-mix(in oklab, var(--border) 58%, transparent);
  }

  .domain-table tbody tr:last-child td {
    border-bottom: 0;
  }

  .domain-table tbody tr:hover {
    background: color-mix(in oklab, var(--accent) 42%, transparent);
  }

  .domain-name {
    font-weight: 600;
    color: var(--foreground);
  }

  .tag-list {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.3rem;
  }

  .tag {
    display: inline-flex;
    align-items: center;
    padding: 0.18rem 0.5rem;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: color-mix(in oklab, var(--accent) 70%, transparent);
    color: var(--muted-foreground);
    font-size: 0.72rem;
    font-weight: 600;
    white-space: nowrap;
  }

  .tag.owner {
    color: var(--foreground);
    border-color: color-mix(in oklab, var(--ring) 36%, var(--border));
    background: color-mix(in oklab, var(--ring) 12%, var(--accent));
  }

  .tag.operation {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.7rem;
    color: color-mix(in oklab, var(--foreground) 86%, var(--muted-foreground));
  }

  .tag.muted {
    opacity: 0.72;
  }

  .domain-state {
    display: grid;
    gap: 0.5rem;
    justify-items: start;
    padding: 1.4rem;
    border: 1px dashed var(--border);
    border-radius: calc(var(--radius) + 0.25rem);
    background: color-mix(in oklab, var(--card) 60%, transparent);
  }

  .domain-state h4 {
    margin: 0;
    font-size: 1rem;
  }

  .domain-state p {
    margin: 0;
    max-width: 42rem;
  }

  .domain-state .state-copy {
    color: var(--muted-foreground);
  }

  .domain-state .muted-hint {
    font-size: 0.85rem;
    opacity: 0.86;
  }

  .domain-state.error {
    border-style: solid;
    border-color: color-mix(in oklab, oklch(0.65 0.19 25) 46%, var(--border));
    background: color-mix(in oklab, oklch(0.65 0.19 25) 9%, var(--card));
  }

  .state-icon {
    display: inline-flex;
    width: 2rem;
    height: 2rem;
    color: var(--primary);
  }

  .state-icon svg {
    width: 100%;
    height: 100%;
  }

  .domain-state.error .state-icon {
    color: oklch(0.72 0.17 25);
  }

  .domain-retry {
    margin-top: 0.3rem;
    padding: 0.5rem 0.9rem;
    border: 1px solid color-mix(in oklab, var(--primary) 34%, var(--border));
    border-radius: calc(var(--radius) + 0.15rem);
    background: color-mix(in oklab, var(--primary) 14%, var(--accent));
    color: var(--foreground);
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 140ms ease, border-color 140ms ease, transform 140ms ease;
  }

  .domain-retry:hover,
  .domain-retry:focus-visible {
    background: color-mix(in oklab, var(--primary) 24%, var(--accent));
    border-color: color-mix(in oklab, var(--primary) 44%, var(--border));
    transform: translateY(-1px);
  }

  .domain-skeleton {
    display: grid;
    gap: 1rem;
  }

  .skeleton-category {
    display: grid;
    gap: 0.55rem;
  }

  .skeleton-line {
    height: 0.8rem;
    border-radius: 999px;
    background: linear-gradient(
      90deg,
      color-mix(in oklab, var(--muted) 70%, transparent) 0%,
      color-mix(in oklab, var(--foreground) 12%, var(--muted)) 50%,
      color-mix(in oklab, var(--muted) 70%, transparent) 100%
    );
    background-size: 200% 100%;
    animation: domain-shimmer 1.5s ease-in-out infinite;
  }

  .skeleton-stat {
    width: 12rem;
    height: 1.1rem;
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

  @keyframes domain-shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .skeleton-line {
      animation: none;
    }

    .domain-retry {
      transition: none;
    }
  }

  @media (max-width: 720px) {
    .domain-stats {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 640px) {
    .domain-table-wrap {
      border: 0;
      background: transparent;
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
      margin-bottom: 0.65rem;
      padding: 0.55rem 0.7rem;
      border: 1px solid var(--border);
      border-radius: calc(var(--radius) + 0.2rem);
      background: color-mix(in oklab, var(--card) 82%, transparent);
    }

    .domain-table tbody tr:hover {
      background: color-mix(in oklab, var(--card) 82%, transparent);
    }

    .domain-table td {
      display: grid;
      grid-template-columns: 6.5rem minmax(0, 1fr);
      gap: 0.6rem;
      align-items: start;
      padding: 0.35rem 0;
      border: 0;
    }

    .domain-table td::before {
      content: attr(data-label);
      font-size: 0.67rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: var(--muted-foreground);
    }
  }
</style>
