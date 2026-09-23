<script lang="ts">
	import { base } from "$app/paths";
	import { goto } from "$app/navigation";
	import ArrowUpRightIcon from "@lucide/svelte/icons/arrow-up-right";
	import BotIcon from "@lucide/svelte/icons/bot";
	import PackageIcon from "@lucide/svelte/icons/package";
	import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
	import SlidersHorizontalIcon from "@lucide/svelte/icons/sliders-horizontal";
	import SparklesIcon from "@lucide/svelte/icons/sparkles";
	import WorkflowIcon from "@lucide/svelte/icons/workflow";
	import WrenchIcon from "@lucide/svelte/icons/wrench";
	import { toast } from "svelte-sonner";
	import CategoryChart from "$lib/components/studio/category-chart.svelte";
	import DataState from "$lib/components/studio/data-state.svelte";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import * as Empty from "$lib/components/ui/empty/index.js";
	import { Progress } from "$lib/components/ui/progress/index.js";
	import * as Tabs from "$lib/components/ui/tabs/index.js";
	import { countUp, reveal } from "$lib/motion";
	import { loadStudio, studio } from "$lib/store.svelte";

	const overview = $derived(studio.overview);
	const counts = $derived(overview?.category_counts ?? {});
	const total = $derived(
		(overview?.runtime_agents.length ?? 0) +
			(overview?.runtime_tools.length ?? 0) +
			(overview?.runtime_workflows.length ?? 0)
	);
	const distribution = $derived(
		Object.entries(counts)
			.map(([category, count]) => ({ category, count }))
			.sort((a, b) => b.count - a.count)
	);
	const maxCount = $derived(Math.max(1, ...Object.values(counts)));
	const topPlugins = $derived((overview?.manifests ?? []).slice(0, 5));

	const stats = $derived([
		{ label: "Agents", value: overview?.runtime_agents.length ?? 0, icon: BotIcon },
		{ label: "Tools", value: overview?.runtime_tools.length ?? 0, icon: WrenchIcon },
		{ label: "Workflows", value: overview?.runtime_workflows.length ?? 0, icon: WorkflowIcon },
	]);

	async function refresh() {
		await loadStudio(true);
		toast.success("Studio state refreshed");
	}
</script>

<DataState loading={studio.loading && !overview} error={studio.error}>
	{#if overview}
		<div class="flex flex-col gap-4 md:gap-6" use:reveal>
			<div data-reveal class="flex flex-wrap items-end justify-between gap-4">
				<div class="flex flex-col gap-1">
					<h1 class="text-2xl font-semibold tracking-tight">{overview.machine_name}</h1>
					<p class="text-muted-foreground text-sm">
						{overview.tenant_name} · {overview.project_name} · {overview.environment}
					</p>
				</div>
				<div class="flex items-center gap-2">
					<Button variant="outline" size="sm" onclick={refresh}>
						<RefreshCwIcon data-icon="inline-start" />
						Refresh
					</Button>
					<Button size="sm" onclick={() => goto(`${base}/context`)}>
						<SlidersHorizontalIcon data-icon="inline-start" />
						Switch context
					</Button>
				</div>
			</div>

			<div class="grid gap-4 lg:grid-cols-6">
				<Card.Root data-reveal class="lg:col-span-4">
					<Card.Header>
						<Card.Title class="flex items-center gap-2">
							<SparklesIcon class="text-muted-foreground" />
							Runtime pulse
						</Card.Title>
						<Card.Description>Installed capabilities across the attached runtime.</Card.Description>
						<Card.Action>
							<Badge variant="secondary">{total} total</Badge>
						</Card.Action>
					</Card.Header>
					<Card.Content class="flex flex-col gap-6">
						<div class="flex items-end gap-6">
							<div class="flex flex-col">
								<span class="text-5xl font-semibold tabular-nums" use:countUp={{ value: total }}></span>
								<span class="text-muted-foreground text-xs uppercase tracking-wide">
									registered items
								</span>
							</div>
							<div class="grid flex-1 grid-cols-3 gap-4">
								{#each stats as stat (stat.label)}
									<div class="flex flex-col gap-1">
										<stat.icon class="text-muted-foreground size-4" />
										<span class="text-2xl font-semibold tabular-nums">{stat.value}</span>
										<span class="text-muted-foreground text-xs">{stat.label}</span>
									</div>
								{/each}
							</div>
						</div>
						<CategoryChart {counts} class="h-52" />
					</Card.Content>
				</Card.Root>

				<Card.Root data-reveal class="lg:col-span-2">
					<Card.Header>
						<Card.Title>Context</Card.Title>
						<Card.Description>Active attachment</Card.Description>
						<Card.Action>
							<Badge
								variant={overview.attachment_status === "attached" ? "secondary" : "outline"}
								class="capitalize"
							>
								{overview.environment_display_status ?? overview.attachment_status}
							</Badge>
						</Card.Action>
					</Card.Header>
					<Card.Content class="flex flex-col gap-4 text-sm">
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
						<div class="flex flex-col gap-1">
							<span class="text-muted-foreground">Entry</span>
							<code class="bg-muted truncate rounded px-2 py-1 text-xs">{overview.entry}</code>
						</div>
						<Button variant="outline" size="sm" class="w-full" onclick={() => goto(`${base}/context`)}>
							Manage
							<ArrowUpRightIcon data-icon="inline-end" />
						</Button>
					</Card.Content>
				</Card.Root>

				<Card.Root data-reveal class="lg:col-span-2">
					<Card.Header>
						<Card.Title>Distribution</Card.Title>
						<Card.Description>Share by category</Card.Description>
					</Card.Header>
					<Card.Content class="flex flex-col gap-4">
						{#if distribution.length}
							{#each distribution as row (row.category)}
								<div class="flex flex-col gap-1.5">
									<div class="flex items-center justify-between text-sm">
										<span class="capitalize">{row.category.replace(/_/g, " ")}</span>
										<span class="text-muted-foreground tabular-nums">{row.count}</span>
									</div>
									<Progress value={(row.count / maxCount) * 100} />
								</div>
							{/each}
						{:else}
							<p class="text-muted-foreground text-sm">No categories registered.</p>
						{/if}
					</Card.Content>
				</Card.Root>

				<Card.Root data-reveal class="lg:col-span-4">
					<Card.Header>
						<Card.Title class="flex items-center gap-2">
							<PackageIcon class="text-muted-foreground" />
							Registry highlights
						</Card.Title>
						<Card.Description>{overview.manifests.length} plugin manifests</Card.Description>
						<Card.Action>
							<Button variant="ghost" size="sm" onclick={() => goto(`${base}/registry`)}>
								View all
							</Button>
						</Card.Action>
					</Card.Header>
					<Card.Content>
						{#if topPlugins.length}
							<div class="flex flex-col divide-y">
								{#each topPlugins as plugin (plugin.name)}
									<div class="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
										<div class="flex min-w-0 flex-col">
											<span class="truncate font-medium">{plugin.name}</span>
											<span class="text-muted-foreground truncate text-xs">
												{plugin.description ?? "No description."}
											</span>
										</div>
										{#if plugin.version}
											<Badge variant="outline">v{plugin.version}</Badge>
										{/if}
									</div>
								{/each}
							</div>
						{:else}
							<p class="text-muted-foreground text-sm">No plugin manifests installed.</p>
						{/if}
					</Card.Content>
				</Card.Root>

				<Card.Root data-reveal class="lg:col-span-3">
					<Card.Header>
						<Card.Title>Build surface</Card.Title>
						<Card.Description>Agents, tools and workflows</Card.Description>
					</Card.Header>
					<Card.Content>
						<Tabs.Root value="agents">
							<Tabs.List class="mb-4">
								<Tabs.Trigger value="agents">Agents</Tabs.Trigger>
								<Tabs.Trigger value="tools">Tools</Tabs.Trigger>
								<Tabs.Trigger value="workflows">Workflows</Tabs.Trigger>
							</Tabs.List>
							<Tabs.Content value="agents">
								<div class="flex flex-col gap-2">
									{#each overview.runtime_agents as item (item.name)}
										<div class="rounded-lg border p-3">
											<div class="flex items-center justify-between gap-2">
												<span class="truncate font-medium">{item.name}</span>
												<Badge variant="outline" class="text-xs">{item.owner}</Badge>
											</div>
											<p class="text-muted-foreground mt-1 line-clamp-2 text-xs">
												{item.description}
											</p>
										</div>
									{:else}
										<p class="text-muted-foreground text-sm">No agents.</p>
									{/each}
								</div>
							</Tabs.Content>
							<Tabs.Content value="tools">
								<div class="flex flex-col gap-2">
									{#each overview.runtime_tools as item (item.name)}
										<div class="rounded-lg border p-3">
											<div class="flex items-center justify-between gap-2">
												<span class="truncate font-medium">{item.name}</span>
												<Badge variant="outline" class="text-xs">{item.owner}</Badge>
											</div>
											<p class="text-muted-foreground mt-1 line-clamp-2 text-xs">
												{item.description}
											</p>
										</div>
									{:else}
										<p class="text-muted-foreground text-sm">No tools.</p>
									{/each}
								</div>
							</Tabs.Content>
							<Tabs.Content value="workflows">
								<div class="flex flex-col gap-2">
									{#each overview.runtime_workflows as item (item.name)}
										<div class="rounded-lg border p-3">
											<div class="flex items-center justify-between gap-2">
												<span class="truncate font-medium">{item.name}</span>
												<Badge variant="outline" class="text-xs">{item.owner}</Badge>
											</div>
											<p class="text-muted-foreground mt-1 line-clamp-2 text-xs">
												{item.description}
											</p>
										</div>
									{:else}
										<p class="text-muted-foreground text-sm">No workflows.</p>
									{/each}
								</div>
							</Tabs.Content>
						</Tabs.Root>
					</Card.Content>
				</Card.Root>

				<Card.Root data-reveal class="lg:col-span-3">
					<Card.Header>
						<Card.Title>Recent activity</Card.Title>
						<Card.Description>Traces and events</Card.Description>
					</Card.Header>
					<Card.Content>
						<Empty.Root class="border-0">
							<Empty.Header>
								<Empty.Media variant="icon">
									<SparklesIcon />
								</Empty.Media>
								<Empty.Title>No activity yet</Empty.Title>
								<Empty.Description>
									Traces appear here once the runtime handles requests. Attach an observability
									exporter to populate this view.
								</Empty.Description>
							</Empty.Header>
							<Empty.Content>
								<Button variant="outline" size="sm" onclick={() => goto(`${base}/domain/observe`)}>
									Open observability
								</Button>
							</Empty.Content>
						</Empty.Root>
					</Card.Content>
				</Card.Root>
			</div>
		</div>
	{/if}
</DataState>
