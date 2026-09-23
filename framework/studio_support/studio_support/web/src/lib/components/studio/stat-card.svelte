<script lang="ts">
	import * as Card from "$lib/components/ui/card/index.js";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import type { IconComponent } from "$lib/nav";

	let {
		label,
		value,
		hint,
		icon,
		badge,
	}: {
		label: string;
		value: string | number;
		hint?: string;
		icon?: IconComponent;
		badge?: string;
	} = $props();
</script>

<Card.Root class="@container/card">
	<Card.Header>
		<Card.Description>{label}</Card.Description>
		<Card.Title class="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
			{value}
		</Card.Title>
		{#if badge}
			<Card.Action>
				<Badge variant="outline">{badge}</Badge>
			</Card.Action>
		{/if}
	</Card.Header>
	{#if hint}
		<Card.Footer class="flex-col items-start gap-1.5 text-sm">
			<div class="line-clamp-1 flex items-center gap-2 font-medium text-muted-foreground">
				{#if icon}
					{@const Icon = icon}
					<Icon class="size-4" />
				{/if}
				{hint}
			</div>
		</Card.Footer>
	{/if}
</Card.Root>
