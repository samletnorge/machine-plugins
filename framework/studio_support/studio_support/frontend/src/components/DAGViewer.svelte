<script lang="ts">
  import { getJson } from '../lib/api';
  import type { WorkflowGraphPayload, WorkflowRunsPayload } from '../lib/types';

  interface Props {
    title: string;
    graphEndpoint: string;
    runsEndpoint: string;
  }

  let { title, graphEndpoint, runsEndpoint }: Props = $props();

  let graph = $state<WorkflowGraphPayload | null>(null);
  let runs = $state<WorkflowRunsPayload['runs']>([]);
  let loadError = $state('');

  let summary = $derived.by(() => {
    const nodeCount = graph?.graph.nodes.length ?? 0;
    return `${nodeCount} nodes loaded for ${title.toLowerCase()}`;
  });

  async function loadWorkflowData() {
    try {
      const [graphPayload, runPayload] = await Promise.all([
        getJson<WorkflowGraphPayload>(graphEndpoint),
        getJson<WorkflowRunsPayload>(runsEndpoint)
      ]);
      graph = graphPayload;
      runs = runPayload.runs;
      loadError = '';
    } catch (error) {
      loadError = error instanceof Error ? error.message : 'Failed to load workflow graph';
    }
  }

  $effect(() => {
    void loadWorkflowData();
  });
</script>

<section class="panel">
  <div class="panel-header compact">
    <div>
      <span class="eyebrow">Island</span>
      <h3>{title}</h3>
    </div>
  </div>
  {#if loadError}
    <p class="muted">{loadError}</p>
  {:else if graph}
    <ul class="simple-list">
      {#each graph.graph.nodes as node (node.id)}
        <li>{node.label} · {node.kind}</li>
      {/each}
    </ul>
    <div class="detail-list">
      <div><span>Edges</span><strong>{graph.graph.edges.length}</strong></div>
      <div><span>Recorded runs</span><strong>{runs.length}</strong></div>
    </div>
    <p>{summary}</p>
  {/if}
</section>
