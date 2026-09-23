<script lang="ts">
	import { BarChart } from "layerchart";
	import * as Chart from "$lib/components/ui/chart/index.js";

	let { counts, class: className = "" }: { counts: Record<string, number>; class?: string } =
		$props();

	const data = $derived(
		Object.entries(counts).map(([category, count]) => ({
			category: category.replace(/_/g, " "),
			count,
		}))
	);
	const config = {
		count: { label: "Items", color: "var(--primary)" },
	} satisfies Chart.ChartConfig;
</script>

<div class={className}>
	{#if data.length}
		<Chart.Container {config} class="aspect-auto h-full min-h-[200px] w-full">
			<BarChart {data} x="category" y="count" />
		</Chart.Container>
	{:else}
		<p class="py-10 text-center text-sm text-muted-foreground">No categories registered.</p>
	{/if}
</div>
