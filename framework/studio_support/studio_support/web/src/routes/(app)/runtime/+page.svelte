<script lang="ts">
	import BotIcon from "@lucide/svelte/icons/bot";
	import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
	import WorkflowIcon from "@lucide/svelte/icons/workflow";
	import WrenchIcon from "@lucide/svelte/icons/wrench";
	import { toast } from "svelte-sonner";
	import DataState from "$lib/components/studio/data-state.svelte";
	import Metric from "$lib/components/studio/metric.svelte";
	import PageHeader from "$lib/components/studio/page-header.svelte";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import * as Tabs from "$lib/components/ui/tabs/index.js";
	import type { RuntimeItem } from "$lib/api";
	import { reveal } from "$lib/motion";
	import { loadStudio, studio } from "$lib/store.svelte";

	const overview = $derived(studio.overview);
	let query = $state("");

	const tabs = $derived<
		{ value: string; label: string; items: RuntimeItem[] }[]
	>([
		{ value: "agents", label: "Agents", items: overview?.runtime_agents ?? [] },
		{ value: "tools", label: "Tools", items: overview?.runtime_tools ?? [] },
		{ value: "workflows", label: "Workflows", items: overview?.runtime_workflows ?? [] },
	]);

	function matches(item: RuntimeItem): boolean {
		const q = query.trim().toLowerCase();
		return !q || item.name.toLowerCase().includes(q) || item.description.toLowerCase().includes(q);
	}

	async function refresh() {
		await loadStudio(true);
		toast.success("Runtime refreshed");
	}
</script>

<div class="flex flex-col gap-4 md:gap-6" use:reveal>
	<div data-reveal>
		<PageHeader
			title="Agents & Tools"
			description="Everything the attached runtime can execute."
		>
			<Button variant="outline" size="sm" onclick={refresh}>
				<RefreshCwIcon data-icon="inline-start" />
				Refresh
			</Button>
		</PageHeader>
	</div>

	<DataState loading={studio.loading && !overview} error={studio.error}>
		{#if overview}
			<Card.Root data-reveal>
				<Card.Content class="grid grid-cols-2 gap-6 py-6 sm:grid-cols-4">
					<Metric label="Agents" value={overview.runtime_agents.length} icon={BotIcon} />
					<Metric label="Tools" value={overview.runtime_tools.length} icon={WrenchIcon} />
					<Metric label="Workflows" value={overview.runtime_workflows.length} icon={WorkflowIcon} />
					<Metric label="Plugins" value={overview.loaded_plugins.length} hint="loaded" />
				</Card.Content>
			</Card.Root>

			<Card.Root data-reveal>
				<Card.Header>
					<Card.Title>Build surface</Card.Title>
					<Card.Description>Search and inspect registered items.</Card.Description>
					<Card.Action>
						<Input bind:value={query} placeholder="Search…" class="w-48" />
					</Card.Action>
				</Card.Header>
				<Card.Content>
					<Tabs.Root value={tabs[0].value}>
						<Tabs.List class="mb-4">
							{#each tabs as tab (tab.value)}
								<Tabs.Trigger value={tab.value}>
									{tab.label}
									<Badge variant="secondary" class="ms-2">{tab.items.length}</Badge>
								</Tabs.Trigger>
							{/each}
						</Tabs.List>
						{#each tabs as tab (tab.value)}
							<Tabs.Content value={tab.value}>
								{#if tab.items.filter(matches).length}
									<div class="grid gap-3 @2xl/main:grid-cols-2 @5xl/main:grid-cols-3">
										{#each tab.items.filter(matches) as item (item.name)}
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
												{#if item.operations?.length}
													<div class="mt-auto flex flex-wrap gap-1 pt-2">
														{#each item.operations as operation (operation)}
															<Badge variant="secondary" class="text-xs">{operation}</Badge>
														{/each}
													</div>
												{/if}
											</div>
										{/each}
									</div>
								{:else}
									<div
										class="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground"
									>
										No {tab.label.toLowerCase()} match.
									</div>
								{/if}
							</Tabs.Content>
						{/each}
					</Tabs.Root>
				</Card.Content>
			</Card.Root>
		{/if}
	</DataState>
</div>
