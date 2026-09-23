<script lang="ts">
	import { Skeleton } from "$lib/components/ui/skeleton/index.js";
	import type { Snippet } from "svelte";

	let {
		loading = false,
		error = null,
		empty = false,
		emptyLabel = "Nothing here yet.",
		children,
	}: {
		loading?: boolean;
		error?: string | null;
		empty?: boolean;
		emptyLabel?: string;
		children: Snippet;
	} = $props();
</script>

{#if loading}
	<div class="space-y-3">
		<Skeleton class="h-24 w-full rounded-xl" />
		<Skeleton class="h-40 w-full rounded-xl" />
	</div>
{:else if error}
	<div class="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
		{error}
	</div>
{:else if empty}
	<div class="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">
		{emptyLabel}
	</div>
{:else}
	{@render children()}
{/if}
