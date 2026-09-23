<script lang="ts">
	import { onMount } from "svelte";
	import DataState from "$lib/components/studio/data-state.svelte";
	import * as Card from "$lib/components/ui/card/index.js";
	import { api } from "$lib/api";

	let config = $state<Record<string, unknown> | null>(null);
	let error = $state<string | null>(null);
	let loading = $state(true);

	onMount(async () => {
		try {
			config = await api<Record<string, unknown>>("/api/config");
		} catch (caught) {
			error = caught instanceof Error ? caught.message : String(caught);
		} finally {
			loading = false;
		}
	});

	const entries = $derived(Object.entries(config ?? {}));

	function render(value: unknown): string {
		if (value === null || value === undefined) return "—";
		if (typeof value === "object") return JSON.stringify(value, null, 2);
		return String(value);
	}
</script>

<DataState loading={loading} error={error} empty={entries.length === 0} emptyLabel="No configuration.">
	<Card.Root>
		<Card.Header>
			<Card.Title>Configuration</Card.Title>
			<Card.Description>Effective Studio configuration for the attached workspace.</Card.Description>
		</Card.Header>
		<Card.Content class="grid gap-3 text-sm">
			{#each entries as [key, value] (key)}
				<div class="grid gap-1 border-b pb-3 last:border-b-0 last:pb-0">
					<span class="font-medium capitalize">{key.replace(/_/g, " ")}</span>
					<pre class="overflow-auto whitespace-pre-wrap break-words text-xs text-muted-foreground"
						>{render(value)}</pre
					>
				</div>
			{/each}
		</Card.Content>
	</Card.Root>
</DataState>
