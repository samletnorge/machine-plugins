<script lang="ts">
	import { onMount } from "svelte";
	import PuzzleIcon from "@tabler/icons-svelte/icons/puzzle";
	import DataState from "$lib/components/studio/data-state.svelte";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { getPlugins, type PluginManifest } from "$lib/api";
	import { studio } from "$lib/store.svelte";

	let plugins = $state<PluginManifest[] | null>(null);
	let error = $state<string | null>(null);
	let loading = $state(true);
	let query = $state("");

	onMount(async () => {
		try {
			plugins = await getPlugins();
		} catch (caught) {
			error = caught instanceof Error ? caught.message : String(caught);
		} finally {
			loading = false;
		}
	});

	const filtered = $derived(
		(plugins ?? []).filter((plugin) => plugin.name.toLowerCase().includes(query.toLowerCase()))
	);
	const declared = $derived(studio.overview?.plugins_declared ?? []);
</script>

<DataState loading={loading} error={error}>
	<div class="flex flex-wrap items-center gap-3">
		<Input bind:value={query} placeholder="Search plugins…" class="max-w-sm" />
		<Badge variant="outline">{filtered.length} plugins</Badge>
	</div>

	{#if filtered.length}
		<div class="grid gap-4 @xl/main:grid-cols-2 @5xl/main:grid-cols-3">
			{#each filtered as plugin (plugin.name)}
				<Card.Root>
					<Card.Header>
						<Card.Title class="flex items-center gap-2">
							<PuzzleIcon class="size-4 text-muted-foreground" />
							{plugin.name}
						</Card.Title>
						{#if plugin.version}
							<Card.Action>
								<Badge variant="outline">v{plugin.version}</Badge>
							</Card.Action>
						{/if}
					</Card.Header>
					<Card.Content class="grid gap-2 text-sm">
						<p class="text-muted-foreground">{plugin.description ?? "No description."}</p>
						{#if plugin.path}
							<code class="truncate rounded bg-muted px-2 py-1 text-xs">{plugin.path}</code>
						{/if}
					</Card.Content>
				</Card.Root>
			{/each}
		</div>
	{:else}
		<div class="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">
			No plugin manifests found.
			{#if declared.length}
				<span class="mt-2 block">Declared in config: {declared.join(", ")}</span>
			{/if}
		</div>
	{/if}
</DataState>
