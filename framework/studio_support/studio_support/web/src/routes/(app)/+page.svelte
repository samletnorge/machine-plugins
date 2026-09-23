<script lang="ts">
	import PuzzleIcon from "@tabler/icons-svelte/icons/puzzle";
	import SitemapIcon from "@tabler/icons-svelte/icons/sitemap";
	import SparklesIcon from "@tabler/icons-svelte/icons/sparkles";
	import ToolIcon from "@tabler/icons-svelte/icons/tool";
	import CategoryChart from "$lib/components/studio/category-chart.svelte";
	import DataState from "$lib/components/studio/data-state.svelte";
	import StatCard from "$lib/components/studio/stat-card.svelte";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import type { RuntimeItem } from "$lib/api";
	import { studio } from "$lib/store.svelte";

	const overview = $derived(studio.overview);
	const counts = $derived(overview?.category_counts ?? {});

	const groups = $derived<
		{ title: string; items: RuntimeItem[] }[]
	>([
		{ title: "Agents", items: overview?.runtime_agents ?? [] },
		{ title: "Tools", items: overview?.runtime_tools ?? [] },
		{ title: "Workflows", items: overview?.runtime_workflows ?? [] },
	]);
</script>

<DataState loading={studio.loading && !overview} error={studio.error}>
	{#if overview}
		<div
			class="grid grid-cols-1 gap-4 @xl/main:grid-cols-2 @5xl/main:grid-cols-4"
		>
			<StatCard
				label="Agents"
				value={overview.runtime_agents.length}
				hint={`${counts.agent ?? 0} registered`}
				icon={SparklesIcon}
			/>
			<StatCard
				label="Tools"
				value={overview.runtime_tools.length}
				hint={`${counts.tool ?? 0} registered`}
				icon={ToolIcon}
			/>
			<StatCard
				label="Workflows"
				value={overview.runtime_workflows.length}
				hint={`${counts.workflow ?? 0} registered`}
				icon={SitemapIcon}
			/>
			<StatCard
				label="Plugins"
				value={overview.manifests.length}
				hint={`${overview.loaded_plugins.length} loaded`}
				icon={PuzzleIcon}
			/>
		</div>

		<div class="grid gap-4 lg:grid-cols-2">
			<CategoryChart {counts} />
			<Card.Root>
				<Card.Header>
					<Card.Title>Context</Card.Title>
					<Card.Description>Active attachment and workspace</Card.Description>
					<Card.Action>
						<Badge
							variant={overview.attachment_status === "attached" ? "secondary" : "outline"}
							class="capitalize"
						>
							{overview.environment_display_status ?? overview.attachment_status}
						</Badge>
					</Card.Action>
				</Card.Header>
				<Card.Content class="grid gap-3 text-sm">
					<div class="flex items-center justify-between gap-4">
						<span class="text-muted-foreground">Machine</span>
						<span class="truncate font-medium">{overview.machine_name}</span>
					</div>
					<div class="flex items-center justify-between gap-4">
						<span class="text-muted-foreground">Tenant</span>
						<span class="truncate font-medium">{overview.tenant_name}</span>
					</div>
					<div class="flex items-center justify-between gap-4">
						<span class="text-muted-foreground">Project</span>
						<span class="truncate font-medium">{overview.project_name}</span>
					</div>
					<div class="flex items-center justify-between gap-4">
						<span class="text-muted-foreground">Environment</span>
						<span class="truncate font-medium">{overview.environment}</span>
					</div>
					<div class="flex items-center justify-between gap-4">
						<span class="text-muted-foreground">Targets</span>
						<span class="font-medium tabular-nums">{overview.target_count}</span>
					</div>
					<div class="grid gap-1">
						<span class="text-muted-foreground">Entry</span>
						<code class="truncate rounded bg-muted px-2 py-1 text-xs">{overview.entry}</code>
					</div>
				</Card.Content>
			</Card.Root>
		</div>

		<div class="grid gap-4 lg:grid-cols-3">
			{#each groups as group (group.title)}
				<Card.Root>
					<Card.Header>
						<Card.Title>{group.title}</Card.Title>
						<Card.Description>{group.items.length} installed</Card.Description>
					</Card.Header>
					<Card.Content class="grid gap-3">
						{#if group.items.length === 0}
							<p class="text-sm text-muted-foreground">Nothing registered.</p>
						{:else}
							{#each group.items as item (item.name)}
								<div class="rounded-lg border p-3">
									<div class="flex items-center justify-between gap-2">
										<span class="truncate font-medium">{item.name}</span>
										{#if item.owner}
											<Badge variant="outline" class="text-xs">{item.owner}</Badge>
										{/if}
									</div>
									{#if item.description}
										<p class="mt-1 line-clamp-2 text-xs text-muted-foreground">
											{item.description}
										</p>
									{/if}
								</div>
							{/each}
						{/if}
					</Card.Content>
				</Card.Root>
			{/each}
		</div>
	{/if}
</DataState>
