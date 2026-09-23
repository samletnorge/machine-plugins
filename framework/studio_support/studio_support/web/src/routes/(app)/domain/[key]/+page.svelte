<script lang="ts">
	import { base } from "$app/paths";
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import BoxesIcon from "@lucide/svelte/icons/boxes";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import * as Empty from "$lib/components/ui/empty/index.js";
	import DataState from "$lib/components/studio/data-state.svelte";
	import Metric from "$lib/components/studio/metric.svelte";
	import PageHeader from "$lib/components/studio/page-header.svelte";
	import { getDomain, type DomainPayload } from "$lib/api";
	import { reveal } from "$lib/motion";
	import { findDomain } from "$lib/nav";

	let payload = $state<DomainPayload | null>(null);
	let error = $state<string | null>(null);
	let loading = $state(true);

	const key = $derived(String(page.params.key ?? ""));
	const nav = $derived(findDomain(key));
	const itemCount = $derived(payload?.items?.length ?? 0);

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

<div class="flex flex-col gap-4 md:gap-6" use:reveal>
	<div data-reveal>
		<PageHeader title={nav?.label ?? "Control plane"} description="Runtime domain items.">
			<Badge variant={payload?.installed ? "secondary" : "outline"}>
				{payload?.installed ? "installed" : "not installed"}
			</Badge>
		</PageHeader>
	</div>

	<DataState loading={loading} error={error}>
		{#if payload?.installed}
			<Card.Root data-reveal>
				<Card.Content class="grid grid-cols-2 gap-6 py-6 sm:grid-cols-4">
					<Metric label="Items" value={itemCount} icon={BoxesIcon} />
					<Metric label="Categories" value={Object.keys(payload.categories).length} />
					<Metric label="Domain" value={payload.domain} />
					<Metric label="Status" value={payload.implemented ? "ready" : "pending"} />
				</Card.Content>
			</Card.Root>

			{#each Object.entries(payload.categories) as [category, items] (category)}
				{#if items.length}
					<Card.Root data-reveal>
						<Card.Header>
							<Card.Title class="capitalize">{category.replace(/_/g, " ")}</Card.Title>
							<Card.Description>{items.length} items</Card.Description>
						</Card.Header>
						<Card.Content class="grid gap-3 @2xl/main:grid-cols-2 @5xl/main:grid-cols-3">
							{#each items as item (item.name)}
								<div class="flex flex-col gap-2 rounded-xl border p-4">
									<div class="flex items-start justify-between gap-2">
										<span class="font-medium">{item.name}</span>
										{#if item.owner}
											<Badge variant="outline" class="text-xs">{item.owner}</Badge>
										{/if}
									</div>
									{#if item.description}
										<p class="text-muted-foreground text-sm">{item.description}</p>
									{/if}
								</div>
							{/each}
						</Card.Content>
					</Card.Root>
				{/if}
			{/each}
		{:else}
			<Card.Root data-reveal>
				<Card.Content class="py-6">
					<Empty.Root class="border-0">
						<Empty.Header>
							<Empty.Media variant="icon">
								<BoxesIcon />
							</Empty.Media>
							<Empty.Title>Nothing registered</Empty.Title>
							<Empty.Description>
								This domain has no items in the current runtime. Install a plugin that provides
								it, or attach a runtime that does.
							</Empty.Description>
						</Empty.Header>
						<Empty.Content>
							<Button variant="outline" size="sm" onclick={() => goto(`${base}/registry`)}>
								Browse registry
							</Button>
						</Empty.Content>
					</Empty.Root>
				</Card.Content>
			</Card.Root>
		{/if}
	</DataState>
</div>
