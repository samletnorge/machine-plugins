<script lang="ts">
	import { onMount } from "svelte";
	import PlayerPlayIcon from "@tabler/icons-svelte/icons/player-play";
	import PlayerStopIcon from "@tabler/icons-svelte/icons/player-stop";
	import RefreshIcon from "@tabler/icons-svelte/icons/refresh";
	import DataState from "$lib/components/studio/data-state.svelte";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import { api, getServicesStatus, type ServicesStatus } from "$lib/api";

	let status = $state<ServicesStatus | null>(null);
	let error = $state<string | null>(null);
	let loading = $state(true);
	let busy = $state<string | null>(null);
	let result = $state<{ action: string; body: unknown } | null>(null);

	onMount(async () => {
		try {
			status = await getServicesStatus();
		} catch (caught) {
			error = caught instanceof Error ? caught.message : String(caught);
		} finally {
			loading = false;
		}
	});

	async function act(action: string) {
		busy = action;
		try {
			const body = await api(`/api/services/${action}`, { method: "POST" });
			result = { action, body };
		} catch (caught) {
			result = { action, body: { error: String(caught) } };
		} finally {
			busy = null;
		}
	}

	const fields = $derived(
		status
			? [
					{ label: "Studio mount", value: status.studio_mount },
					{ label: "Runtime API", value: status.runtime_api },
					{ label: "Health", value: status.health_endpoint },
					{ label: "Docs", value: status.docs_endpoint },
				]
			: []
	);
</script>

<DataState loading={loading} error={error}>
	<div class="grid gap-4 lg:grid-cols-2">
		<Card.Root>
			<Card.Header>
				<Card.Title>Control plane</Card.Title>
				<Card.Description>Endpoints exposed by the attached studio.</Card.Description>
			</Card.Header>
			<Card.Content class="grid gap-3 text-sm">
				{#each fields as field (field.label)}
					<div class="flex items-center justify-between gap-4">
						<span class="text-muted-foreground">{field.label}</span>
						<code class="truncate rounded bg-muted px-2 py-1 text-xs">{field.value}</code>
					</div>
				{/each}
			</Card.Content>
		</Card.Root>

		<Card.Root>
			<Card.Header>
				<Card.Title>Actions</Card.Title>
				<Card.Description>Runtime service controls.</Card.Description>
			</Card.Header>
			<Card.Content class="grid gap-3">
				<div class="flex flex-wrap gap-2">
					<Button size="sm" disabled={busy !== null} onclick={() => act("start")}>
						<PlayerPlayIcon class="size-4" /> Start
					</Button>
					<Button size="sm" variant="outline" disabled={busy !== null} onclick={() => act("stop")}>
						<PlayerStopIcon class="size-4" /> Stop
					</Button>
					<Button size="sm" variant="outline" disabled={busy !== null} onclick={() => act("restart")}>
						<RefreshIcon class="size-4" /> Restart
					</Button>
				</div>
				{#if result}
					<div class="rounded-lg border p-3 text-xs">
						<div class="mb-1 flex items-center gap-2">
							<Badge variant="outline" class="capitalize">{result.action}</Badge>
						</div>
						<pre class="overflow-auto text-muted-foreground">{JSON.stringify(
								result.body,
								null,
								2
							)}</pre>
					</div>
				{/if}
			</Card.Content>
		</Card.Root>

		{#if status?.notes?.length}
			<Card.Root class="lg:col-span-2">
				<Card.Header>
					<Card.Title>Notes</Card.Title>
				</Card.Header>
				<Card.Content>
					<ul class="list-disc space-y-1 ps-5 text-sm text-muted-foreground">
						{#each status.notes as note (note)}
							<li>{note}</li>
						{/each}
					</ul>
				</Card.Content>
			</Card.Root>
		{/if}
	</div>
</DataState>
