<script lang="ts">
	import { onMount } from "svelte";
	import DataState from "$lib/components/studio/data-state.svelte";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import { Label } from "$lib/components/ui/label/index.js";
	import * as Select from "$lib/components/ui/select/index.js";
	import {
		getContext,
		getEnvironments,
		getProjects,
		getTenants,
		switchContext,
		type ContextResponse,
		type Environment,
		type Project,
		type Tenant,
	} from "$lib/api";

	let current = $state<ContextResponse | null>(null);
	let tenants = $state<Tenant[]>([]);
	let projects = $state<Project[]>([]);
	let environments = $state<Environment[]>([]);
	let tenant = $state("");
	let project = $state("");
	let environment = $state("");
	let loading = $state(true);
	let error = $state<string | null>(null);
	let busy = $state(false);
	let message = $state<string | null>(null);

	onMount(async () => {
		try {
			const [context, tenantList] = await Promise.all([getContext(), getTenants()]);
			current = context;
			tenants = tenantList;
			tenant = context.context.tenant_slug;
			project = context.context.project_slug;
			environment = context.context.environment_name;
			await refreshProjects(tenant, false);
			await refreshEnvironments(project, false);
		} catch (caught) {
			error = caught instanceof Error ? caught.message : String(caught);
		} finally {
			loading = false;
		}
	});

	async function refreshProjects(slug: string, reset = true) {
		projects = slug ? await getProjects(slug) : [];
		if (reset) {
			project = projects[0]?.slug ?? "";
			environments = [];
			environment = "";
		}
	}

	async function refreshEnvironments(slug: string, reset = true) {
		environments = slug ? await getEnvironments(slug) : [];
		if (reset) environment = environments[0]?.name ?? "";
	}

	async function onTenant(value: string) {
		tenant = value;
		await refreshProjects(value);
	}

	async function onProject(value: string) {
		project = value;
		await refreshEnvironments(value);
	}

	async function apply() {
		busy = true;
		message = null;
		try {
			current = await switchContext({
				tenant_slug: tenant,
				project_slug: project,
				environment_name: environment,
			});
			message = "Context switched.";
		} catch (caught) {
			message = caught instanceof Error ? caught.message : String(caught);
		} finally {
			busy = false;
		}
	}

	const attachment = $derived(current?.attachment);
</script>

<DataState loading={loading} error={error}>
	<div class="grid gap-4 lg:grid-cols-2">
		<Card.Root>
			<Card.Header>
				<Card.Title>Switch context</Card.Title>
				<Card.Description>Choose the tenant, project and environment to attach.</Card.Description>
			</Card.Header>
			<Card.Content class="grid gap-4">
				<div class="grid gap-2">
					<Label for="tenant">Tenant</Label>
					<Select.Root type="single" value={tenant} onValueChange={onTenant}>
						<Select.Trigger id="tenant" class="w-full">
							<span data-slot="select-value">{tenant || "Select tenant"}</span>
						</Select.Trigger>
						<Select.Content>
							{#each tenants as option (option.slug)}
								<Select.Item value={option.slug}>{option.name}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>
				<div class="grid gap-2">
					<Label for="project">Project</Label>
					<Select.Root type="single" value={project} onValueChange={onProject}>
						<Select.Trigger id="project" class="w-full">
							<span data-slot="select-value">{project || "Select project"}</span>
						</Select.Trigger>
						<Select.Content>
							{#each projects as option (option.slug)}
								<Select.Item value={option.slug}>{option.name}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>
				<div class="grid gap-2">
					<Label for="environment">Environment</Label>
					<Select.Root type="single" value={environment} onValueChange={(v) => (environment = v)}>
						<Select.Trigger id="environment" class="w-full">
							<span data-slot="select-value">{environment || "Select environment"}</span>
						</Select.Trigger>
						<Select.Content>
							{#each environments as option (option.name)}
								<Select.Item value={option.name}>{option.name}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>
				<div class="flex items-center gap-3">
					<Button disabled={busy || !tenant || !project || !environment} onclick={apply}>
						Apply
					</Button>
					{#if message}
						<span class="text-sm text-muted-foreground">{message}</span>
					{/if}
				</div>
			</Card.Content>
		</Card.Root>

		<Card.Root>
			<Card.Header>
				<Card.Title>Active</Card.Title>
				<Card.Description>Currently attached runtime.</Card.Description>
				<Card.Action>
					<Badge
						variant={attachment?.status === "attached" ? "secondary" : "outline"}
						class="capitalize"
					>
						{attachment?.status ?? "detached"}
					</Badge>
				</Card.Action>
			</Card.Header>
			<Card.Content class="grid gap-3 text-sm">
				<div class="flex items-center justify-between gap-4">
					<span class="text-muted-foreground">Tenant</span>
					<span class="font-medium">{current?.context.tenant_name}</span>
				</div>
				<div class="flex items-center justify-between gap-4">
					<span class="text-muted-foreground">Project</span>
					<span class="font-medium">{current?.context.project_name}</span>
				</div>
				<div class="flex items-center justify-between gap-4">
					<span class="text-muted-foreground">Environment</span>
					<span class="font-medium">{current?.context.environment_name}</span>
				</div>
				<div class="flex items-center justify-between gap-4">
					<span class="text-muted-foreground">Runtime</span>
					<span class="font-medium">{attachment?.machine_name || "—"}</span>
				</div>
				{#if attachment?.error}
					<p class="text-destructive">{attachment.error}</p>
				{/if}
			</Card.Content>
		</Card.Root>
	</div>
</DataState>
