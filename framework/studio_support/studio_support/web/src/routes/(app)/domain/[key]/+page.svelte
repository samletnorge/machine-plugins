<script lang="ts">
	import { page } from "$app/state";
	import DataState from "$lib/components/studio/data-state.svelte";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import { getDomain, type DomainPayload } from "$lib/api";
	import { findDomain } from "$lib/nav";

	let payload = $state<DomainPayload | null>(null);
	let error = $state<string | null>(null);
	let loading = $state(true);

	const key = $derived(String(page.params.key ?? ""));
	const nav = $derived(findDomain(key));

	async function load(currentKey: string) {
		loading = true;
		error = null;
		payload = null;
		const item = findDomain(currentKey);
		if (!item?.endpoint) {
			error = `Unknown domain '${currentKey}'.`;
			loading = false;
			return;
		}
		try {
			payload = await getDomain(item.endpoint);
		} catch (caught) {
			error = caught instanceof Error ? caught.message : String(caught);
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load(key);
	});
</script>

<DataState loading={loading} error={error}>
	{#if payload}
		<Card.Root>
			<Card.Header>
				<Card.Title class="capitalize">{nav?.label ?? payload.domain}</Card.Title>
				<Card.Description>
					{payload.installed ? "Installed runtime items." : "No items registered for this domain."}
				</Card.Description>
				<Card.Action>
					<Badge variant={payload.installed ? "secondary" : "outline"}>
						{payload.installed ? "installed" : "not installed"}
					</Badge>
				</Card.Action>
			</Card.Header>
		</Card.Root>

		{#if payload.installed}
			{#each Object.entries(payload.categories) as [category, items] (category)}
				{#if items.length}
					<Card.Root>
						<Card.Header>
							<Card.Title class="capitalize">{category.replace(/_/g, " ")}</Card.Title>
							<Card.Description>{items.length} items</Card.Description>
						</Card.Header>
						<Card.Content class="grid gap-3 @xl/main:grid-cols-2 @5xl/main:grid-cols-3">
							{#each items as item (item.name)}
								<div class="rounded-lg border p-4">
									<div class="flex items-start justify-between gap-2">
										<span class="font-medium">{item.name}</span>
										{#if item.owner}
											<Badge variant="outline" class="text-xs">{item.owner}</Badge>
										{/if}
									</div>
									{#if item.description}
										<p class="mt-1 text-sm text-muted-foreground">{item.description}</p>
									{/if}
								</div>
							{/each}
						</Card.Content>
					</Card.Root>
				{/if}
			{/each}
		{:else}
			<div class="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">
				This domain has no registered items in the current runtime.
			</div>
		{/if}
	{/if}
</DataState>
