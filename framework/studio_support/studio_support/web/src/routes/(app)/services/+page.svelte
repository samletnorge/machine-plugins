<script lang="ts">
	import { onMount } from "svelte";
	import PlayIcon from "@lucide/svelte/icons/play";
	import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
	import RotateCwIcon from "@lucide/svelte/icons/rotate-cw";
	import SquareIcon from "@lucide/svelte/icons/square";
	import { toast } from "svelte-sonner";
	import DataState from "$lib/components/studio/data-state.svelte";
	import PageHeader from "$lib/components/studio/page-header.svelte";
	import { Alert, AlertDescription, AlertTitle } from "$lib/components/ui/alert/index.js";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import { api, getServicesStatus, type ServicesStatus } from "$lib/api";
	import { reveal } from "$lib/motion";

	let status = $state<ServicesStatus | null>(null);
	let error = $state<string | null>(null);
	let loading = $state(true);
	let busy = $state<string | null>(null);
	let result = $state<{ action: string; ok: boolean; body: unknown } | null>(null);

	onMount(async () => {
		try {
			status = await getServicesStatus();
		} catch (caught) {
			error = caught instanceof Error ? caught.message : String(caught);
		} finally {
			loading = false;
		}
	});

	const actions = [
		{ key: "start", label: "Start", icon: PlayIcon },
		{ key: "stop", label: "Stop", icon: SquareIcon },
		{ key: "restart", label: "Restart", icon: RotateCwIcon },
	];

	async function act(action: string) {
		busy = action;
		try {
			const body = await api(`/api/services/${action}`, { method: "POST" });
			result = { action, ok: true, body };
			toast.success(`Service action "${action}" accepted`);
		} catch (caught) {
			result = { action, ok: false, body: { error: String(caught) } };
			toast.error(`Service action "${action}" failed`);
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

<div class="flex flex-col gap-4 md:gap-6" use:reveal>
	<div data-reveal>
		<PageHeader
			title="Services"
			description="Control-plane endpoints and runtime service actions."
		>
			<Badge variant="secondary">control plane</Badge>
		</PageHeader>
	</div>

	<DataState loading={loading} error={error}>
		<div class="grid gap-4 lg:grid-cols-3" data-reveal>
			<Card.Root class="lg:col-span-2">
				<Card.Header>
					<Card.Title>Endpoints</Card.Title>
					<Card.Description>Where the studio and runtime expose their APIs.</Card.Description>
				</Card.Header>
				<Card.Content class="grid gap-4 sm:grid-cols-2">
					{#each fields as field (field.label)}
						<div class="flex flex-col gap-1">
							<span class="text-muted-foreground text-xs uppercase tracking-wide">
								{field.label}
							</span>
							<code class="bg-muted truncate rounded px-2 py-1 text-xs">{field.value}</code>
						</div>
					{/each}
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Title>Actions</Card.Title>
					<Card.Description>Runtime service controls.</Card.Description>
				</Card.Header>
				<Card.Content class="flex flex-col gap-3">
					<div class="flex flex-wrap gap-2">
						{#each actions as action (action.key)}
							<Button
								size="sm"
								variant={action.key === "start" ? "default" : "outline"}
								disabled={busy !== null}
								onclick={() => act(action.key)}
							>
								<action.icon
									data-icon="inline-start"
									class={busy === action.key ? "animate-spin" : ""}
								/>
								{action.label}
							</Button>
						{/each}
					</div>
					{#if result}
						<pre
							class="bg-muted overflow-auto rounded-lg p-3 text-xs text-muted-foreground">{JSON.stringify(
								result.body,
								null,
								2
							)}</pre>
					{/if}
				</Card.Content>
			</Card.Root>

			{#if status?.notes?.length}
				<Card.Root class="lg:col-span-3">
					<Card.Content class="pt-6">
						<Alert>
							<AlertTitle>Control plane notes</AlertTitle>
							<AlertDescription>
								<ul class="list-disc space-y-1 ps-4">
									{#each status.notes as note (note)}
										<li>{note}</li>
									{/each}
								</ul>
							</AlertDescription>
						</Alert>
					</Card.Content>
				</Card.Root>
			{/if}
		</div>
	</DataState>
</div>
