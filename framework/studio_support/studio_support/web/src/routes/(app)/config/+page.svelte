<script lang="ts">
	import { onMount } from "svelte";
	import CopyIcon from "@lucide/svelte/icons/copy";
	import { toast } from "svelte-sonner";
	import DataState from "$lib/components/studio/data-state.svelte";
	import PageHeader from "$lib/components/studio/page-header.svelte";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import { api } from "$lib/api";
	import { reveal } from "$lib/motion";

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

	async function copy() {
		try {
			await navigator.clipboard.writeText(JSON.stringify(config ?? {}, null, 2));
			toast.success("Configuration copied");
		} catch {
			toast.error("Copy failed");
		}
	}
</script>

<div class="flex flex-col gap-4 md:gap-6" use:reveal>
	<div data-reveal>
		<PageHeader title="Config" description="Effective configuration for the attached workspace.">
			<Button variant="outline" size="sm" onclick={copy}>
				<CopyIcon data-icon="inline-start" />
				Copy JSON
			</Button>
		</PageHeader>
	</div>

	<DataState
		loading={loading}
		error={error}
		empty={entries.length === 0}
		emptyLabel="No configuration available."
	>
		<Card.Root data-reveal>
			<Card.Header>
				<Card.Title>Values</Card.Title>
				<Card.Description>{entries.length} keys</Card.Description>
			</Card.Header>
			<Card.Content class="flex flex-col">
				{#each entries as [key, value] (key)}
					<div class="flex flex-col gap-1 border-b py-4 first:pt-0 last:border-b-0 last:pb-0">
						<span class="font-medium capitalize">{key.replace(/_/g, " ")}</span>
						<pre
							class="text-muted-foreground overflow-auto whitespace-pre-wrap break-words text-xs">{render(
								value
							)}</pre>
					</div>
				{/each}
			</Card.Content>
		</Card.Root>
	</DataState>
</div>
