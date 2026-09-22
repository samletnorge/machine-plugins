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

  let categories = $derived.by(() =>
    Object.entries(payload?.categories ?? {}).filter(([, items]) => items.length > 0)
  );

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

  $effect(() => {
    void loadDomain();
  });
</script>

<section class="panel" data-domain={domain}>
  <div class="panel-header compact">
    <div>
      <span class="eyebrow">Island</span>
      <h3>{title}</h3>
    </div>
    {#if payload}
      <span class="pill">{payload.installed ? 'installed' : 'not installed'}</span>
    {/if}
  </div>

  {#if loadError}
    <p class="muted">{loadError}</p>
  {:else if loading}
    <p class="muted">Loading {title}…</p>
  {:else if payload && !payload.installed}
    <p class="muted">This surface is empty because its plugin is not installed in the active runtime.</p>
  {:else if payload}
    {#each categories as [category, items] (category)}
      <div class="domain-category">
        <h4>{category} <span class="pill">{items.length}</span></h4>
        <table class="domain-table">
          <thead>
            <tr><th>Name</th><th>Owner</th><th>Description</th><th>Operations</th></tr>
          </thead>
          <tbody>
            {#each items as item (item.name)}
              <tr>
                <td>{item.name}</td>
                <td>{item.owner ?? '—'}</td>
                <td>{item.description ?? '—'}</td>
                <td>{item.operations?.join(', ') || '—'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/each}
  {/if}
</section>
