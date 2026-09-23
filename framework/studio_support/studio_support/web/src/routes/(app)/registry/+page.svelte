<script lang="ts">
	import { onMount } from "svelte";
	import PackageIcon from "@lucide/svelte/icons/package";
	import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
	import { toast } from "svelte-sonner";
	import CategoryChart from "$lib/components/studio/category-chart.svelte";
	import DataState from "$lib/components/studio/data-state.svelte";
	import Metric from "$lib/components/studio/metric.svelte";
	import PageHeader from "$lib/components/studio/page-header.svelte";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import * as Select from "$lib/components/ui/select/index.js";
	import { getPlugins, type PluginManifest } from "$lib/api";
	import { reveal } from "$lib/motion";
	import { studio } from "$lib/store.svelte";

	let plugins = $state<PluginManifest[] | null>(null);
	let error = $state<string | null>(null);
	let loading = $state(true);
	let query = $state("");
	let prefix = $state("all");

	onMount(load);

	async function load() {
		loading = true;
		error = null;
		try {
			plugins = await getPlugins();
		} catch (caught) {
			error = caught instanceof Error ? caught.message : String(caught);
		} finally {
			loading = false;
		}
	}

	function prefixOf(name: string): string {
		return name.split(/[_-]/)[0] || name;
	}

	const prefixes = $derived(
		[...new Set((plugins ?? []).map((p) => prefixOf(p.name)))].sort()
	);
	const counts = $derived(
		(plugins ?? []).reduce<Record<string, number>>((acc, p) => {
			const key = prefixOf(p.name);
			acc[key] = (acc[key] ?? 0) + 1;
			return acc;
		}, {})
	);
	const chartCounts = $derived(
		Object.fromEntries(
			Object.entries(counts)
				.sort((a, b) => b[1] - a[1])
				.slice(0, 10)
		)
	);
	const filtered = $derived(
		(plugins ?? []).filter(
			(plugin) =>
				(prefix === "all" || prefixOf(plugin.name) === prefix) &&
				plugin.name.toLowerCase().includes(query.toLowerCase())
		)
	);
	const declared = $derived(studio.overview?.plugins_declared ?? []);
	const loaded = $derived(studio.overview?.loaded_plugins ?? []);
</script>

<div class="flex flex-col gap-4 md:gap-6" use:reveal>
	<div data-reveal>
		<PageHeader title="Registry" description="Plugins and capabilities available to the runtime.">
			<Button variant="outline" size="sm" onclick={() => { load(); toast.success("Registry refreshed"); }}>
				<RefreshCwIcon data-icon="inline-start" />
				Refresh
			</Button>
		</PageHeader>
	</div>

	<Card.Root data-reveal>
		<Card.Content class="grid grid-cols-2 gap-6 py-6 sm:grid-cols-4">
			<Metric label="Plugins" value={plugins?.length ?? 0} icon={PackageIcon} />
			<Metric label="Categories" value={prefixes.length} />
			<Metric label="Loaded" value={loaded.length} />
			<Metric label="Declared" value={declared.length} />
		</Card.Content>
	</Card.Root>

	<DataState loading={loading} error={error}>
		<div class="grid gap-4 lg:grid-cols-3" data-reveal>
			<Card.Root class="lg:col-span-1">
				<Card.Header>
					<Card.Title>By category</Card.Title>
					<Card.Description>Plugins per name prefix</Card.Description>
				</Card.Header>
				<Card.Content>
					<CategoryChart counts={chartCounts} class="h-64" />
				</Card.Content>
			</Card.Root>

			<div class="flex flex-col gap-4 lg:col-span-2">
				<div class="flex flex-wrap items-center gap-3">
					<Input bind:value={query} placeholder="Search plugins…" class="max-w-sm" />
					<Select.Root type="single" value={prefix} onValueChange={(v) => (prefix = v)}>
						<Select.Trigger class="w-44">
							<span data-slot="select-value">
								{prefix === "all" ? "All categories" : prefix}
							</span>
						</Select.Trigger>
						<Select.Content>
							<Select.Item value="all">All categories</Select.Item>
							{#each prefixes as option (option)}
								<Select.Item value={option}>{option}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
					<Badge variant="outline">{filtered.length} shown</Badge>
				</div>

				{#if filtered.length}
					<div class="grid gap-4 @2xl/main:grid-cols-2">
						{#each filtered as plugin (plugin.name)}
							<Card.Root>
								<Card.Header>
									<Card.Title class="flex items-center gap-2">
										<PackageIcon class="text-muted-foreground" />
										{plugin.name}
									</Card.Title>
									{#if plugin.version}
										<Card.Action>
											<Badge variant="outline">v{plugin.version}</Badge>
										</Card.Action>
									{/if}
								</Card.Header>
								<Card.Content class="flex flex-col gap-2">
									<p class="text-muted-foreground text-sm">
										{plugin.description ?? "No description."}
									</p>
									{#if plugin.path}
										<code class="bg-muted truncate rounded px-2 py-1 text-xs">{plugin.path}</code>
									{/if}
								</Card.Content>
							</Card.Root>
						{/each}
					</div>
				{:else}
					<div class="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">
						No plugins match your filters.
					</div>
				{/if}
			</div>
		</div>
	</DataState>
</div>
