<script lang="ts">
	import { countUp } from "$lib/motion";
	import type { IconComponent } from "$lib/nav";

	let {
		label,
		value,
		icon,
		hint,
	}: { label: string; value: number | string; icon?: IconComponent; hint?: string } = $props();

	const numeric = $derived(typeof value === "number");
</script>

<div class="flex flex-col gap-1">
	<div class="text-muted-foreground flex items-center gap-2">
		{#if icon}
			{@const Icon = icon}
			<Icon class="size-4" />
		{/if}
		<span class="text-xs tracking-wide uppercase">{label}</span>
	</div>
	<span class="text-2xl font-semibold tabular-nums">
		{#if numeric}
			<span use:countUp={{ value: value as number }}></span>
		{:else}
			{value}
		{/if}
	</span>
	{#if hint}
		<span class="text-muted-foreground text-xs">{hint}</span>
	{/if}
</div>
