<script lang="ts">
  import { getJson } from '../lib/api';
  import type { WorkflowGraphPayload, WorkflowRunsPayload } from '../lib/types';

  interface Props {
    title: string;
    graphEndpoint: string;
    runsEndpoint: string;
  }

  interface LayoutNode {
    id: string;
    label: string;
    kind: string;
    x: number;
    y: number;
    cls: string;
  }

  interface LayoutEdge {
    id: string;
    d: string;
  }

  interface DagLayout {
    width: number;
    height: number;
    nodes: LayoutNode[];
    edges: LayoutEdge[];
  }

  let { title, graphEndpoint, runsEndpoint }: Props = $props();

  const NODE_W = 176;
  const NODE_H = 52;
  const GAP_X = 78;
  const GAP_Y = 26;
  const PAD = 16;
  const KIND_CLASSES = ['kind-0', 'kind-1', 'kind-2', 'kind-3'];

  let graph = $state<WorkflowGraphPayload | null>(null);
  let runs = $state<WorkflowRunsPayload['runs']>([]);
  let loadError = $state('');
  let loading = $state(true);
  let reloadToken = $state(0);

  let nodes = $derived(graph?.graph.nodes ?? []);
  let edges = $derived(graph?.graph.edges ?? []);
  let layout = $derived(buildLayout(nodes, edges));

  let summary = $derived.by(() => {
    if (!graph) return `Loading ${title.toLowerCase()}…`;
    return `${nodes.length} node${nodes.length === 1 ? '' : 's'} · ${edges.length} edge${edges.length === 1 ? '' : 's'} · ${runs.length} run${runs.length === 1 ? '' : 's'}`;
  });

  const uid = `dag-${Math.random().toString(36).slice(2, 9)}`;

  function truncate(value: string, max = 22) {
    return value.length > max ? `${value.slice(0, max - 1)}…` : value;
  }

  function kindClass(kind: string) {
    const key = (kind || '').toLowerCase();
    const known: Record<string, string> = {
      step: 'kind-0',
      tool: 'kind-1',
      agent: 'kind-2',
      condition: 'kind-3',
      branch: 'kind-3',
      parallel: 'kind-1',
      workflow: 'kind-2'
    };
    if (known[key]) return known[key];
    let hash = 0;
    for (let i = 0; i < key.length; i += 1) {
      hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
    }
    return KIND_CLASSES[hash % KIND_CLASSES.length];
  }

  function statusClass(status: string) {
    const value = (status || '').toLowerCase();
    if (['success', 'succeeded', 'done', 'completed', 'ok', 'passed'].includes(value)) return 'ok';
    if (['failed', 'error', 'errored', 'cancelled'].includes(value)) return 'error';
    if (['running', 'in_progress', 'pending', 'queued', 'started'].includes(value)) return 'running';
    return 'neutral';
  }

  function buildLayout(inputNodes: WorkflowGraphPayload['graph']['nodes'], inputEdges: WorkflowGraphPayload['graph']['edges']): DagLayout {
    if (inputNodes.length === 0) {
      return { width: 0, height: 0, nodes: [], edges: [] };
    }

    const incoming = new Map<string, string[]>();
    const outgoing = new Map<string, string[]>();
    for (const node of inputNodes) {
      incoming.set(node.id, []);
      outgoing.set(node.id, []);
    }
    for (const edge of inputEdges) {
      if (!incoming.has(edge.target) || !outgoing.has(edge.source)) continue;
      incoming.get(edge.target)!.push(edge.source);
      outgoing.get(edge.source)!.push(edge.target);
    }

    const level = new Map<string, number>();
    const visiting = new Set<string>();
    const depth = (id: string): number => {
      const cached = level.get(id);
      if (cached !== undefined) return cached;
      if (visiting.has(id)) return 0;
      visiting.add(id);
      const preds = incoming.get(id) ?? [];
      const value = preds.length ? Math.max(...preds.map((pred) => depth(pred) + 1)) : 0;
      visiting.delete(id);
      level.set(id, value);
      return value;
    };
    for (const node of inputNodes) depth(node.id);

    const byLevel = new Map<number, string[]>();
    for (const node of inputNodes) {
      const value = level.get(node.id) ?? 0;
      if (!byLevel.has(value)) byLevel.set(value, []);
      byLevel.get(value)!.push(node.id);
    }

    const levels = [...byLevel.keys()].sort((a, b) => a - b);
    const maxRows = Math.max(...levels.map((value) => byLevel.get(value)!.length), 1);
    const height = PAD * 2 + maxRows * NODE_H + (maxRows - 1) * GAP_Y;
    const width = PAD * 2 + levels.length * NODE_W + Math.max(0, levels.length - 1) * GAP_X;

    const position = new Map<string, { x: number; y: number }>();    for (const value of levels) {
      const column = byLevel.get(value)!;
      const columnHeight = column.length * NODE_H + (column.length - 1) * GAP_Y;
      const offset = (height - columnHeight) / 2;
      column.forEach((id, index) => {
        position.set(id, {
          x: PAD + value * (NODE_W + GAP_X),
          y: offset + index * (NODE_H + GAP_Y)
        });
      });
    }

    const laidOutNodes: LayoutNode[] = inputNodes
      .filter((node) => position.has(node.id))
      .map((node) => {
        const point = position.get(node.id)!;
        return { ...node, x: point.x, y: point.y, cls: kindClass(node.kind) };
      });

    const laidOutEdges: LayoutEdge[] = inputEdges
      .filter((edge) => position.has(edge.source) && position.has(edge.target))
      .map((edge) => {
        const source = position.get(edge.source)!;
        const target = position.get(edge.target)!;
        const sx = source.x + NODE_W;
        const sy = source.y + NODE_H / 2;
        const tx = target.x;
        const ty = target.y + NODE_H / 2;
        const curve = Math.max(26, (tx - sx) * 0.5);
        return {
          id: `${edge.source}->${edge.target}`,
          d: `M ${sx} ${sy} C ${sx + curve} ${sy}, ${tx - curve} ${ty}, ${tx} ${ty}`
        };
      });

    return { width, height, nodes: laidOutNodes, edges: laidOutEdges };
  }

  async function loadWorkflowData() {
    loading = true;
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
    } finally {
      loading = false;
    }
  }

  function retry() {
    reloadToken += 1;
    void loadWorkflowData();
  }

  $effect(() => {
    void reloadToken;
    void loadWorkflowData();
  });
</script>

<section class="panel dag-panel" aria-busy={loading}>
  <header class="panel-header compact dag-header">
    <div class="dag-heading">
      <span class="eyebrow">Workflow</span>
      <h3>{title}</h3>
      <p class="dag-subtitle">{summary}</p>
    </div>
    {#if graph}
      <div class="dag-legend" aria-hidden="true">
        <span class="legend-item"><i class="legend-swatch kind-0"></i>step</span>
        <span class="legend-item"><i class="legend-swatch kind-1"></i>tool</span>
        <span class="legend-item"><i class="legend-swatch kind-2"></i>agent</span>
        <span class="legend-item"><i class="legend-swatch kind-3"></i>branch</span>
      </div>
    {/if}
  </header>

  {#if loadError}
    <div class="dag-state error" role="alert">
      <h4>Unable to load workflow</h4>
      <p>{loadError}</p>
      <button type="button" class="dag-retry" onclick={retry}>Try again</button>
    </div>
  {:else if loading}
    <div class="dag-skeleton" aria-hidden="true">
      <div class="skeleton-node"></div>
      <div class="skeleton-edge"></div>
      <div class="skeleton-node"></div>
      <div class="skeleton-edge"></div>
      <div class="skeleton-node"></div>
    </div>
  {:else if graph && nodes.length === 0}
    <div class="dag-state">
      <h4>No graph steps</h4>
      <p>This workflow is registered but exposes no nodes yet.</p>
    </div>
  {:else if graph}
    <div class="dag-canvas-wrap">
      <svg
        class="dag-canvas"
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        role="img"
        aria-label={`${title}: ${nodes.length} nodes and ${edges.length} edges`}
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <marker id={`${uid}-arrow`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path class="dag-arrow" d="M 0 0 L 10 5 L 0 10 z"></path>
          </marker>
        </defs>

        <g class="dag-edges">
          {#each layout.edges as edge (edge.id)}
            <path class="dag-edge" d={edge.d} marker-end={`url(#${uid}-arrow)`}></path>
          {/each}
        </g>

        <g class="dag-nodes">
          {#each layout.nodes as node (node.id)}
            <g class={`dag-node ${node.cls}`} transform={`translate(${node.x} ${node.y})`}>
              <title>{node.label} · {node.kind}</title>
              <rect class="dag-node-rect" width={NODE_W} height={NODE_H} rx="9" ry="9"></rect>
              <text class="dag-node-label" x={NODE_W / 2} y={NODE_H / 2 - 5} text-anchor="middle" dominant-baseline="middle">
                {truncate(node.label)}
              </text>
              <text class="dag-node-kind" x={NODE_W / 2} y={NODE_H / 2 + 13} text-anchor="middle" dominant-baseline="middle">
                {node.kind}
              </text>
            </g>
          {/each}
        </g>
      </svg>
    </div>

    <ul class="sr-only" aria-label="Workflow nodes and edges">
      {#each nodes as node (node.id)}
        <li>{node.label} ({node.kind})</li>
      {/each}
      {#each edges as edge (`${edge.source}->${edge.target}`)}
        <li>{edge.source} to {edge.target}</li>
      {/each}
    </ul>

    <div class="dag-stats">
      <div class="dag-stat"><span class="stat-label">Nodes</span><strong>{nodes.length}</strong></div>
      <div class="dag-stat"><span class="stat-label">Edges</span><strong>{edges.length}</strong></div>
      <div class="dag-stat"><span class="stat-label">Recorded runs</span><strong>{runs.length}</strong></div>
    </div>

    <div class="dag-runs">
      <span class="eyebrow">Recent runs</span>
      {#if runs.length === 0}
        <p class="muted dag-runs-empty">No runs recorded for this workflow yet.</p>
      {:else}
        <ul class="dag-run-list">
          {#each runs as run (run.run_id)}
            <li class="dag-run">
              <span class="run-id">{run.run_id}</span>
              <span class={`run-status ${statusClass(run.status)}`}>{run.status}</span>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  {/if}
</section>

<style>
  .dag-panel {
    display: grid;
    gap: 1rem;
  }

  .dag-header {
    align-items: flex-start;
    margin-bottom: 0;
    padding-bottom: 0.9rem;
    border-bottom: 1px solid color-mix(in oklab, var(--border) 82%, transparent);
  }

  .dag-heading {
    display: grid;
    gap: 0.2rem;
    min-width: 0;
  }

  .dag-heading h3 {
    margin: 0;
    font-size: 1.15rem;
  }

  .dag-subtitle {
    margin: 0;
    font-size: 0.86rem;
    color: var(--muted-foreground);
  }

  .dag-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    align-items: center;
  }

  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.72rem;
    color: var(--muted-foreground);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .legend-swatch {
    width: 0.6rem;
    height: 0.6rem;
    border-radius: 0.2rem;
    border: 1px solid var(--border);
    background: var(--accent);
  }

  .legend-swatch.kind-0 {
    background: color-mix(in oklab, var(--primary) 45%, var(--accent));
  }

  .legend-swatch.kind-1 {
    background: color-mix(in oklab, var(--ring) 45%, var(--accent));
  }

  .legend-swatch.kind-2 {
    background: color-mix(in oklab, oklch(0.7 0.14 300) 42%, var(--accent));
  }

  .legend-swatch.kind-3 {
    background: color-mix(in oklab, oklch(0.78 0.14 70) 42%, var(--accent));
  }

  .dag-canvas-wrap {
    padding: 0.85rem;
    overflow-x: auto;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) + 0.25rem);
    background: color-mix(in oklab, var(--card) 68%, transparent);
  }

  .dag-canvas {
    display: block;
    width: 100%;
    height: auto;
    max-height: 30rem;
  }

  .dag-edge {
    fill: none;
    stroke: color-mix(in oklab, var(--muted-foreground) 52%, transparent);
    stroke-width: 1.6;
  }

  .dag-arrow {
    fill: color-mix(in oklab, var(--muted-foreground) 70%, transparent);
  }

  .dag-node-rect {
    fill: color-mix(in oklab, var(--accent) 84%, transparent);
    stroke: var(--border);
    stroke-width: 1;
  }

  .dag-node.kind-0 .dag-node-rect {
    fill: color-mix(in oklab, var(--primary) 14%, var(--card));
    stroke: color-mix(in oklab, var(--primary) 52%, var(--border));
  }

  .dag-node.kind-1 .dag-node-rect {
    fill: color-mix(in oklab, var(--ring) 14%, var(--card));
    stroke: color-mix(in oklab, var(--ring) 52%, var(--border));
  }

  .dag-node.kind-2 .dag-node-rect {
    fill: color-mix(in oklab, oklch(0.7 0.14 300) 12%, var(--card));
    stroke: color-mix(in oklab, oklch(0.7 0.14 300) 48%, var(--border));
  }

  .dag-node.kind-3 .dag-node-rect {
    fill: color-mix(in oklab, oklch(0.78 0.14 70) 14%, var(--card));
    stroke: color-mix(in oklab, oklch(0.78 0.14 70) 48%, var(--border));
  }

  .dag-node-label {
    fill: var(--foreground);
    font-family: var(--font-sans);
    font-size: 12px;
    font-weight: 600;
  }

  .dag-node-kind {
    fill: var(--muted-foreground);
    font-family: var(--font-sans);
    font-size: 9.5px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .dag-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.7rem;
  }

  .dag-stat {
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

  .dag-stat strong {
    font-size: 1.15rem;
    font-weight: 700;
  }

  .dag-runs {
    display: grid;
    gap: 0.5rem;
  }

  .dag-runs-empty {
    margin: 0;
    font-size: 0.88rem;
  }

  .dag-run-list {
    display: grid;
    gap: 0.45rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .dag-run {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    padding: 0.55rem 0.7rem;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) + 0.1rem);
    background: color-mix(in oklab, var(--card) 80%, transparent);
    font-size: 0.85rem;
  }

  .run-id {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.8rem;
  }

  .run-status {
    flex: none;
    padding: 0.18rem 0.55rem;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: color-mix(in oklab, var(--accent) 75%, transparent);
    color: var(--muted-foreground);
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: lowercase;
  }

  .run-status.ok {
    color: var(--foreground);
    border-color: color-mix(in oklab, var(--primary) 42%, var(--border));
    background: color-mix(in oklab, var(--primary) 16%, var(--accent));
  }

  .run-status.running {
    color: var(--foreground);
    border-color: color-mix(in oklab, var(--ring) 42%, var(--border));
    background: color-mix(in oklab, var(--ring) 14%, var(--accent));
  }

  .run-status.error {
    color: var(--foreground);
    border-color: color-mix(in oklab, oklch(0.65 0.19 25) 50%, var(--border));
    background: color-mix(in oklab, oklch(0.65 0.19 25) 16%, var(--accent));
  }

  .dag-state {
    display: grid;
    gap: 0.5rem;
    justify-items: start;
    padding: 1.4rem;
    border: 1px dashed var(--border);
    border-radius: calc(var(--radius) + 0.25rem);
    background: color-mix(in oklab, var(--card) 60%, transparent);
  }

  .dag-state h4 {
    margin: 0;
  }

  .dag-state p {
    margin: 0;
    color: var(--muted-foreground);
  }

  .dag-state.error {
    border-style: solid;
    border-color: color-mix(in oklab, oklch(0.65 0.19 25) 46%, var(--border));
    background: color-mix(in oklab, oklch(0.65 0.19 25) 9%, var(--card));
  }

  .dag-retry {
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

  .dag-skeleton {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.6rem;
    padding: 1.2rem;
    border: 1px dashed var(--border);
    border-radius: calc(var(--radius) + 0.25rem);
  }

  .skeleton-node {
    width: 8.5rem;
    height: 3rem;
    border-radius: calc(var(--radius) + 0.2rem);
    background: linear-gradient(
      90deg,
      color-mix(in oklab, var(--muted) 70%, transparent) 0%,
      color-mix(in oklab, var(--foreground) 12%, var(--muted)) 50%,
      color-mix(in oklab, var(--muted) 70%, transparent) 100%
    );
    background-size: 200% 100%;
    animation: dag-shimmer 1.5s ease-in-out infinite;
  }

  .skeleton-edge {
    width: 3.5rem;
    height: 2px;
    background: color-mix(in oklab, var(--muted-foreground) 40%, transparent);
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

  @keyframes dag-shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .skeleton-node {
      animation: none;
    }
  }

  @media (max-width: 560px) {
    .dag-stats {
      grid-template-columns: 1fr;
    }
  }
</style>
