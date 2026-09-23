<script lang="ts">
	import DataState from "$lib/components/studio/data-state.svelte";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import { studio } from "$lib/store.svelte";

	const overview = $derived(studio.overview);
	const groups = $derived([
		{ title: "Agents", items: overview?.runtime_agents ?? [] },
		{ title: "Tools", items: overview?.runtime_tools ?? [] },
		{ title: "Workflows", items: overview?.runtime_workflows ?? [] },
	]);
</script>

<DataState loading={studio.loading && !overview} error={studio.error}>
	{#if overview}
		{#each groups as group (group.title)}
			<Card.Root>
				<Card.Header>
					<Card.Title>{group.title}</Card.Title>
					<Card.Description>{group.items.length} installed</Card.Description>
				</Card.Header>
				<Card.Content>
					{#if group.items.length === 0}
						<p class="text-sm text-muted-foreground">Nothing registered.</p>
					{:else}
						<div class="grid gap-3 @xl/main:grid-cols-2 @5xl/main:grid-cols-3">
							{#each group.items as item (item.name)}
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
									{#if item.operations?.length}
										<div class="mt-3 flex flex-wrap gap-1">
											{#each item.operations as operation (operation)}
												<Badge variant="secondary" class="text-xs">{operation}</Badge>
											{/each}
										</div>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</Card.Content>
			</Card.Root>
		{/each}
	{/if}
</DataState>
