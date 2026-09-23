<script lang="ts">
	import { onMount } from "svelte";
	import DownloadIcon from "@lucide/svelte/icons/download";
	import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
	import StoreIcon from "@lucide/svelte/icons/store";
	import Trash2Icon from "@lucide/svelte/icons/trash-2";
	import { toast } from "svelte-sonner";
	import DataState from "$lib/components/studio/data-state.svelte";
	import Metric from "$lib/components/studio/metric.svelte";
	import PageHeader from "$lib/components/studio/page-header.svelte";
	import { Alert, AlertDescription, AlertTitle } from "$lib/components/ui/alert/index.js";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import * as Tabs from "$lib/components/ui/tabs/index.js";
	import {
		getStore,
		installPlugin,
		uninstallPlugin,
		type StoreActionResult,
		type StoreCatalog,
	} from "$lib/api";
	import { reveal } from "$lib/motion";

	let catalog = $state<StoreCatalog | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let query = $state("");
	let tier = $state("all");
	let busy = $state<string | null>(null);
	let lastResult = $state<StoreActionResult | null>(null);

	onMount(load);

	async function load() {
		loading = true;
		error = null;
		try {
			catalog = await getStore();
		} catch (caught) {
			error = caught instanceof Error ? caught.message : String(caught);
		} finally {
			loading = false;
		}
	}

	const plugins = $derived(catalog?.plugins ?? []);
	const tiers = $derived([...new Set(plugins.map((plugin) => plugin.tier))]);
	const filtered = $derived(
		plugins.filter(
			(plugin) =>
				(tier === "all" || plugin.tier === tier) &&
				(plugin.name.toLowerCase().includes(query.toLowerCase()) ||
					plugin.description.toLowerCase().includes(query.toLowerCase()))
		)
	);
	const declaredCount = $derived(catalog?.declared.length ?? 0);
	const installedCount = $derived(catalog?.installed.length ?? 0);

	async function run(name: string, action: "install" | "uninstall") {
		busy = name;
		try {
			lastResult =
				action === "install" ? await installPlugin(name) : await uninstallPlugin(name);
			toast.success(`${name} ${action === "install" ? "installed" : "removed"}`);
			await load();
		} catch (caught) {
			toast.error(`${name}: ${caught instanceof Error ? caught.message : String(caught)}`);
		} finally {
			busy = null;
		}
	}
</script>

<div class="flex flex-col gap-4 md:gap-6" use:reveal>
	<div data-reveal>
		<PageHeader
			title="Store"
			description="Install plugins into this project — dependency, declaration, and manifest sync."
		>
			<Button variant="outline" size="sm" onclick={load}>
				<RefreshCwIcon data-icon="inline-start" />
				Refresh
			</Button>
		</PageHeader>
	</div>

	<DataState loading={loading} error={error}>
		{#if catalog}
			{#if !catalog.has_pyproject}
				<Alert data-reveal>
					<AlertTitle>No pyproject.toml found</AlertTitle>
					<AlertDescription>
						The store needs a project to install into. Run it from a machine-core project
						directory (with a pyproject.toml).
					</AlertDescription>
				</Alert>
			{/if}

			<Card.Root data-reveal>
				<Card.Content class="grid grid-cols-2 gap-6 py-6 sm:grid-cols-4">
					<Metric label="Available" value={plugins.length} icon={StoreIcon} />
					<Metric label="Declared" value={declaredCount} hint="in pyproject.toml" />
					<Metric label="Installed" value={installedCount} hint="in the environment" />
					<Metric label="Project" value={catalog.project_root.split("/").pop() ?? "—"} />
				</Card.Content>
			</Card.Root>

			<div class="flex flex-wrap items-center gap-3" data-reveal>
				<Input bind:value={query} placeholder="Search plugins…" class="max-w-sm" />
				<Tabs.Root value={tier}>
					<Tabs.List>
						<Tabs.Trigger value="all" onclick={() => (tier = "all")}>All</Tabs.Trigger>
						{#each tiers as option (option)}
							<Tabs.Trigger value={option} onclick={() => (tier = option)}>
								{option}
							</Tabs.Trigger>
						{/each}
					</Tabs.List>
				</Tabs.Root>
				<Badge variant="outline">{filtered.length} shown</Badge>
			</div>

			<div class="grid gap-4 @2xl/main:grid-cols-2 @5xl/main:grid-cols-3" data-reveal>
				{#each filtered as plugin (plugin.name)}
					<Card.Root>
						<Card.Header>
							<Card.Title class="flex items-center gap-2">
								<StoreIcon class="text-muted-foreground" />
								{plugin.name}
							</Card.Title>
							<Card.Action>
								<div class="flex items-center gap-1">
									<Badge variant="outline">{plugin.tier}</Badge>
									{#if plugin.version}
										<Badge variant="outline">v{plugin.version}</Badge>
									{/if}
								</div>
							</Card.Action>
						</Card.Header>
						<Card.Content class="flex flex-1 flex-col gap-3">
							<p class="text-muted-foreground text-sm">{plugin.description}</p>
							<div class="flex flex-wrap gap-1">
								{#if plugin.installed}
									<Badge variant="secondary">installed</Badge>
								{/if}
								{#if plugin.declared}
									<Badge variant="secondary">declared</Badge>
								{/if}
							</div>
							<div class="mt-auto flex gap-2 pt-2">
								{#if plugin.declared || plugin.installed}
									<Button
										variant="outline"
										size="sm"
										disabled={busy !== null}
										onclick={() => run(plugin.name, "uninstall")}
									>
										<Trash2Icon data-icon="inline-start" />
										Remove
									</Button>
								{:else}
									<Button
										size="sm"
										disabled={busy !== null || !catalog.has_pyproject}
										onclick={() => run(plugin.name, "install")}
									>
										<DownloadIcon data-icon="inline-start" />
										{busy === plugin.name ? "Installing…" : "Install"}
									</Button>
								{/if}
							</div>
						</Card.Content>
					</Card.Root>
				{/each}
			</div>

			{#if lastResult}
				<Card.Root data-reveal>
					<Card.Header>
						<Card.Title>Last action: {lastResult.name}</Card.Title>
						<Card.Description>
							{lastResult.commands.map((command) => command.join(" ")).join("  ·  ")}
						</Card.Description>
					</Card.Header>
					{#if lastResult.output}
						<Card.Content>
							<pre
								class="bg-muted max-h-48 overflow-auto rounded-lg p-3 text-xs text-muted-foreground"
								>{lastResult.output}</pre>
						</Card.Content>
					{/if}
				</Card.Root>
			{/if}
		{/if}
	</DataState>
</div>
