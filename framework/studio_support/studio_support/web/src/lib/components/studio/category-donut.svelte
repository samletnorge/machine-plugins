<script lang="ts">
	import { PieChart } from "layerchart";
	import * as Chart from "$lib/components/ui/chart/index.js";

	let { counts, class: className = "" }: { counts: Record<string, number>; class?: string } =
		$props();

	const palette = [
		"var(--chart-1)",
		"var(--chart-2)",
		"var(--chart-3)",
		"var(--chart-4)",
		"var(--chart-5)",
	];

	const data = $derived(
		Object.entries(counts).map(([label, value]) => ({ key: label, label, value }))
	);
	const config = $derived(
		Object.fromEntries(
			data.map((entry, index) => [
				entry.key,
				{ label: entry.label, color: palette[index % palette.length] },
			])
		) satisfies Chart.ChartConfig
	);
</script>

<div class={className}>
	{#if data.length}
		<Chart.Container {config} class="aspect-auto h-full min-h-[220px] w-full">
			<PieChart {data} key="key" label="label" value="value" innerRadius={0.62} />
		</Chart.Container>
	{:else}
		<p class="text-muted-foreground py-10 text-center text-sm">No data.</p>
	{/if}
</div>
