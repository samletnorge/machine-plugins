<script lang="ts">
	import { toast } from "svelte-sonner";
	import EyeIcon from "@lucide/svelte/icons/eye";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Dialog from "$lib/components/ui/dialog/index.js";
	import { getWorkflowDetail, getWorkflowRuns, type WorkflowGraph } from "$lib/api";

	let { workflowName }: { workflowName: string } = $props();

	let open = $state(false);
	let graph = $state<WorkflowGraph | null>(null);
	let runs = $state<Record<string, unknown>[]>([]);
	let loading = $state(false);

	async function load() {
		loading = true;
		graph = null;
		runs = [];
		try {
			const [detail, runList] = await Promise.all([
				getWorkflowDetail(workflowName),
				getWorkflowRuns(workflowName),
			]);
			graph = detail.graph;
			runs = runList.runs;
		} catch (caught) {
			toast.error(caught instanceof Error ? caught.message : String(caught));
		} finally {
			loading = false;
		}
	}
</script>

<Dialog.Root bind:open onOpenChange={(value) => value && load()}>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<Button variant="outline" size="sm" {...props}>
				<EyeIcon data-icon="inline-start" />
				View
			</Button>
		{/snippet}
	</Dialog.Trigger>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>{workflowName}</Dialog.Title>
			<Dialog.Description>Workflow graph and recent runs.</Dialog.Description>
		</Dialog.Header>
		<div class="grid gap-4">
			{#if loading}
				<p class="text-muted-foreground text-sm">Loading…</p>
			{:else if graph}
				<div class="grid gap-2">
					<span class="text-muted-foreground text-xs uppercase tracking-wide">Steps</span>
					<div class="flex flex-wrap items-center gap-2">
						{#each graph.nodes as node, index (node.id)}
							{#if index > 0}
								<span class="text-muted-foreground">→</span>
							{/if}
							<div class="flex items-center gap-1 rounded-lg border px-2 py-1 text-sm">
								<span>{node.label}</span>
								<Badge variant="secondary" class="text-xs capitalize">{node.kind}</Badge>
							</div>
						{/each}
					</div>
				</div>
				<div class="grid gap-2">
					<span class="text-muted-foreground text-xs uppercase tracking-wide">
						Runs ({runs.length})
					</span>
					{#if runs.length}
						{#each runs as run (JSON.stringify(run))}
							<pre class="bg-muted overflow-auto rounded-lg p-3 text-xs">{JSON.stringify(
									run,
									null,
									2
								)}</pre>
						{/each}
					{:else}
						<p class="text-muted-foreground text-sm">No runs recorded.</p>
					{/if}
				</div>
			{:else}
				<p class="text-muted-foreground text-sm">No graph available.</p>
			{/if}
		</div>
	</Dialog.Content>
</Dialog.Root>
