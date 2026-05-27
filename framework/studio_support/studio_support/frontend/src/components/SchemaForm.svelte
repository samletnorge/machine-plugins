<script lang="ts">
  import { getJson } from '../lib/api';
  import type { ToolDetail } from '../lib/types';

  interface Props {
    detailEndpoint: string;
  }

  let { detailEndpoint }: Props = $props();

  let detail = $state<ToolDetail | null>(null);
  let loadError = $state('');

  async function loadDetail() {
    try {
      detail = await getJson<ToolDetail>(detailEndpoint);
      loadError = '';
    } catch (error) {
      loadError = error instanceof Error ? error.message : 'Failed to load tool detail';
    }
  }

  $effect(() => {
    void loadDetail();
  });
</script>

<section class="panel">
  <div class="panel-header compact">
    <div>
      <span class="eyebrow">Island</span>
      <h3>Schema-driven tool runner</h3>
    </div>
  </div>

  {#if loadError}
    <p class="muted">{loadError}</p>
  {:else if detail}
    <div class="detail-list">
      <div><span>Owner</span><strong>{detail.owner ?? 'runtime'}</strong></div>
      <div><span>Operations</span><strong>{detail.operations.join(', ')}</strong></div>
    </div>
    <ul class="simple-list">
      {#each Object.entries(detail.input_schema.properties ?? {}) as [name, meta] (name)}
        <li><strong>{name}</strong> · {meta.type ?? meta.title ?? 'value'}</li>
      {/each}
    </ul>
  {/if}
</section>
