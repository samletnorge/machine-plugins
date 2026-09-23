<script lang="ts">
	import type { Snippet } from "svelte";

	let {
		title,
		description,
		children,
	}: { title: string; description?: string; children?: Snippet } = $props();
</script>

<div class="flex flex-wrap items-end justify-between gap-4">
	<div class="flex flex-col gap-1">
		<h1 class="text-2xl font-semibold tracking-tight">{title}</h1>
		{#if description}
			<p class="text-muted-foreground text-sm">{description}</p>
		{/if}
	</div>
	{#if children}
		<div class="flex items-center gap-2">{@render children()}</div>
	{/if}
</div>
