<script lang="ts">
	import { BarChart } from "layerchart";
	import * as Card from "$lib/components/ui/card/index.js";
	import * as Chart from "$lib/components/ui/chart/index.js";

	let { counts }: { counts: Record<string, number> } = $props();

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

<Card.Root class="@container/card">
	<Card.Header>
		<Card.Title>Registry by category</Card.Title>
		<Card.Description>Installed runtime items per category</Card.Description>
	</Card.Header>
	<Card.Content class="px-2 pt-4 sm:px-6 sm:pt-6">
		{#if data.length}
			<Chart.Container config={config} class="aspect-auto h-[260px] w-full">
				<BarChart {data} x="category" y="count" />
			</Chart.Container>
		{:else}
			<p class="py-10 text-center text-sm text-muted-foreground">No categories registered.</p>
		{/if}
	</Card.Content>
</Card.Root>
