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
    source: string;
    target: string;
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
  let hoveredNode = $state<string | null>(null);

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
          d: `M ${sx} ${sy} C ${sx + curve} ${sy}, ${tx - curve} ${ty}, ${tx} ${ty}`,
          source: edge.source,
          target: edge.target
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
          {#each layout.edges as edge, edgeIndex (edge.id)}
            <path
              class="dag-edge"
              class:highlight={Boolean(hoveredNode) && (edge.source === hoveredNode || edge.target === hoveredNode)}
              class:dimmed={Boolean(hoveredNode) && edge.source !== hoveredNode && edge.target !== hoveredNode}
              d={edge.d}
              pathLength={1}
              style={`--edge-index:${edgeIndex}`}
              marker-end={`url(#${uid}-arrow)`}
            ></path>
          {/each}
        </g>

        <g class="dag-nodes">
          {#each layout.nodes as node, nodeIndex (node.id)}
            <g
              class={`dag-node ${node.cls}`}
              class:dimmed={Boolean(hoveredNode) && hoveredNode !== node.id}
              transform={`translate(${node.x} ${node.y})`}
              style={`--node-index:${nodeIndex}`}
              role="img"
              aria-label={`${node.label} · ${node.kind}`}
              onpointerenter={() => (hoveredNode = node.id)}
              onpointerleave={() => (hoveredNode = null)}
            >
              <title>{node.label} · {node.kind}</title>
              <rect class="dag-node-rect" width={NODE_W} height={NODE_H} rx="8" ry="8"></rect>
              <circle class={`dag-node-dot ${node.cls}`} cx="14" cy="14" r="3.5"></circle>
              <text class="dag-node-label" x={NODE_W / 2 + 6} y={NODE_H / 2 - 5} text-anchor="middle" dominant-baseline="middle">
                {truncate(node.label)}
              </text>
              <text class="dag-node-kind" x={NODE_W / 2 + 6} y={NODE_H / 2 + 13} text-anchor="middle" dominant-baseline="middle">
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
    --hair: color-mix(in oklab, var(--border) 100%, transparent);
    --r: var(--radius);
    --mono: var(--font-mono, ui-monospace, SFMono-Regular, 'JetBrains Mono', Menlo, Consolas, monospace);
    display: grid;
    gap: 1rem;
    background: transparent;
    border: 0;
    border-radius: 0;
  }

  .dag-panel > :not(.dag-header) {
    margin-inline: 18px;
  }

  .dag-panel > :last-child {
    margin-bottom: 18px;
  }

  .dag-header {
    align-items: flex-start;
    margin-bottom: 0;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--hair);
  }

  .dag-heading {
    display: grid;
    gap: 0.25rem;
    min-width: 0;
  }

  .dag-heading h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: -0.01em;
  }

  .dag-subtitle {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--muted-foreground);
  }

  .dag-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: center;
  }

  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted-foreground);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .legend-swatch {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--primary);
  }

  .legend-swatch.kind-1 {
    background: var(--ring);
  }

  .legend-swatch.kind-2 {
    background: var(--foreground);
  }

  .legend-swatch.kind-3 {
    background: var(--muted-foreground);
  }

  .dag-canvas-wrap {
    padding: 1rem;
    overflow-x: auto;
    border: 1px solid var(--hair);
    border-radius: var(--r);
    background-color: color-mix(in oklab, var(--background) 100%, transparent);
    background-image:
      linear-gradient(color-mix(in oklab, var(--border) 42%, transparent) 1px, transparent 1px),
      linear-gradient(90deg, color-mix(in oklab, var(--border) 42%, transparent) 1px, transparent 1px);
    background-size: 28px 28px;
  }

  .dag-canvas {
    display: block;
    width: 100%;
    height: auto;
    max-height: 30rem;
  }

  .dag-edge {
    fill: none;
    stroke: color-mix(in oklab, var(--muted-foreground) 55%, transparent);
    stroke-width: 1.2;
    stroke-dasharray: 1;
    stroke-dashoffset: 1;
    animation: dag-draw 220ms ease-out forwards;
    animation-delay: calc(var(--edge-index, 0) * 28ms);
    transition: stroke 140ms ease, stroke-width 140ms ease, opacity 140ms ease;
  }

  .dag-edge.highlight {
    stroke: var(--primary);
    stroke-width: 1.8;
  }

  .dag-edge.dimmed {
    opacity: 0.15;
  }

  .dag-node {
    animation: dag-node-in 200ms ease-out backwards;
    animation-delay: calc(var(--node-index, 0) * 36ms);
    transition: opacity 140ms ease;
  }

  .dag-node.dimmed {
    opacity: 0.25;
  }

  .dag-arrow {
    fill: color-mix(in oklab, var(--muted-foreground) 72%, transparent);
  }

  .dag-node-rect {
    fill: color-mix(in oklab, var(--card) 96%, transparent);
    stroke: var(--hair);
    stroke-width: 1;
  }

  .dag-node-dot {
    fill: var(--primary);
  }

  .dag-node-dot.kind-1 {
    fill: var(--ring);
  }

  .dag-node-dot.kind-2 {
    fill: var(--foreground);
  }

  .dag-node-dot.kind-3 {
    fill: var(--muted-foreground);
  }

  .dag-node-label {
    fill: var(--foreground);
    font-family: var(--font-sans);
    font-size: 12px;
    font-weight: 600;
  }

  .dag-node-kind {
    fill: var(--muted-foreground);
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .dag-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0;
    border: 1px solid var(--hair);
    border-radius: var(--r);
    overflow: hidden;
  }

  .dag-stat {
    display: grid;
    gap: 0.125rem;
    padding: 0.625rem 0.75rem;
    border-left: 1px solid var(--hair);
  }

  .dag-stat:first-child {
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

  .dag-stat strong {
    font-family: var(--mono);
    font-size: 1rem;
    font-weight: 600;
    color: var(--foreground);
    font-variant-numeric: tabular-nums;
  }

  .dag-runs {
    display: grid;
    gap: 0.5rem;
  }

  .dag-runs-empty {
    margin: 0;
    font-size: 0.8125rem;
  }

  .dag-run-list {
    display: grid;
    gap: 0;
    margin: 0;
    padding: 0;
    list-style: none;
    border: 1px solid var(--hair);
    border-radius: var(--r);
    overflow: hidden;
  }

  .dag-run {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0.75rem;
    border-top: 1px solid var(--hair);
    font-size: 0.8125rem;
  }

  .dag-run:first-child {
    border-top: 0;
  }

  .run-id {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: var(--mono);
    font-size: 0.75rem;
  }

  .run-status {
    flex: none;
    padding: 0.1rem 0.45rem;
    border-radius: 999px;
    border: 1px solid var(--hair);
    background: transparent;
    color: var(--muted-foreground);
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    text-transform: lowercase;
    letter-spacing: 0.02em;
  }

  .run-status.ok {
    color: color-mix(in oklab, var(--success) 82%, var(--foreground));
    border-color: color-mix(in oklab, var(--success) 45%, var(--border));
  }

  .run-status.running {
    color: color-mix(in oklab, var(--warning) 82%, var(--foreground));
    border-color: color-mix(in oklab, var(--warning) 45%, var(--border));
  }

  .run-status.error {
    color: color-mix(in oklab, var(--danger) 88%, var(--foreground));
    border-color: color-mix(in oklab, var(--danger) 52%, var(--border));
  }

  .dag-state {
    display: grid;
    gap: 0.5rem;
    justify-items: start;
    padding: 1rem;
    border: 1px solid var(--hair);
    border-radius: var(--r);
  }

  .dag-state h4 {
    margin: 0;
    font-size: 0.9375rem;
    font-weight: 600;
  }

  .dag-state p {
    margin: 0;
    color: var(--muted-foreground);
    line-height: 1.55;
  }

  .dag-state.error {
    border-color: color-mix(in oklab, var(--danger) 52%, var(--border));
    background: color-mix(in oklab, var(--danger) 8%, transparent);
  }

  .dag-retry {
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

  .dag-retry:hover {
    border-color: var(--primary);
    background: color-mix(in oklab, var(--primary) 10%, transparent);
  }

  .dag-retry:focus-visible {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--ring) 30%, transparent);
  }

  .dag-skeleton {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 1rem;
    border: 1px solid var(--hair);
    border-radius: var(--r);
  }

  .skeleton-node {
    width: 8.5rem;
    height: 3rem;
    border-radius: var(--r);
    background: color-mix(in oklab, var(--muted) 82%, transparent);
    animation: dag-pulse 1.4s ease-in-out infinite;
  }

  .skeleton-edge {
    width: 3.5rem;
    height: 1px;
    background: color-mix(in oklab, var(--muted-foreground) 45%, transparent);
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

  @keyframes dag-pulse {
    0%,
    100% {
      opacity: 0.45;
    }
    50% {
      opacity: 1;
    }
  }

  @keyframes dag-draw {
    to {
      stroke-dashoffset: 0;
    }
  }

  @keyframes dag-node-in {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .skeleton-node {
      animation: none;
    }

    .dag-edge {
      animation: none;
      stroke-dashoffset: 0;
      transition: none;
    }

    .dag-node {
      animation: none;
      transition: none;
    }

    .dag-retry {
      transition: none;
    }
  }

  @media (max-width: 560px) {
    .dag-stats {
      grid-template-columns: 1fr;
    }

    .dag-stat {
      border-left: 0;
      border-top: 1px solid var(--hair);
    }

    .dag-stat:first-child {
      border-top: 0;
    }
  }
</style>
