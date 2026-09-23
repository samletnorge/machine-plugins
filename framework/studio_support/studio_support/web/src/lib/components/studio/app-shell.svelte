<script lang="ts">
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Separator } from "$lib/components/ui/separator/index.js";
	import { studio } from "$lib/store.svelte";
	import StudioSidebar from "./studio-sidebar.svelte";
	import type { Snippet } from "svelte";

	let {
		title = "Studio",
		children,
	}: { title?: string; children: Snippet } = $props();

	const overview = $derived(studio.overview);
	const attached = $derived(overview?.attachment_status === "attached");
	const statusLabel = $derived(
		overview?.environment_display_status ?? overview?.attachment_status ?? "unknown"
	);
	const statusVariant = $derived(
		attached ? "secondary" : overview?.attachment_status === "error" ? "destructive" : "outline"
	);
</script>

<Sidebar.Provider
	style="--sidebar-width: calc(var(--spacing) * 72); --header-height: calc(var(--spacing) * 12);"
>
	<StudioSidebar />
	<Sidebar.Inset>
		<header
			class="flex h-(--header-height) shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear"
		>
			<div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
				<Sidebar.Trigger class="-ms-1" />
				<Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />
				<h1 class="truncate text-base font-medium">{title}</h1>
				<div class="ms-auto flex items-center gap-2">
					{#if overview}
						<span class="hidden text-xs text-muted-foreground sm:inline">
							{overview.project_name}{#if overview.environment}· {overview.environment}{/if}
						</span>
					{/if}
					<Badge variant={statusVariant} class="capitalize">{statusLabel}</Badge>
				</div>
			</div>
		</header>
		<div class="flex flex-1 flex-col">
			<div class="@container/main flex flex-1 flex-col gap-4 p-4 md:gap-6 md:p-6">
				{@render children()}
			</div>
		</div>
	</Sidebar.Inset>
</Sidebar.Provider>
