<script lang="ts">
	import { onMount } from "svelte";
	import GlobeIcon from "@lucide/svelte/icons/globe";
	import LayersIcon from "@lucide/svelte/icons/layers";
	import TargetIcon from "@lucide/svelte/icons/target";
	import { toast } from "svelte-sonner";
	import DataState from "$lib/components/studio/data-state.svelte";
	import Metric from "$lib/components/studio/metric.svelte";
	import PageHeader from "$lib/components/studio/page-header.svelte";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import { Label } from "$lib/components/ui/label/index.js";
	import * as Select from "$lib/components/ui/select/index.js";
	import * as Table from "$lib/components/ui/table/index.js";
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
	import { reveal } from "$lib/motion";
	import { loadStudio, studio } from "$lib/store.svelte";

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

	const targets = $derived(studio.overview?.project_targets ?? []);

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
		try {
			current = await switchContext({
				tenant_slug: tenant,
				project_slug: project,
				environment_name: environment,
			});
			await loadStudio(true);
			toast.success(`Attached to ${current.context.project_name} · ${current.context.environment_name}`);
		} catch (caught) {
			toast.error(caught instanceof Error ? caught.message : String(caught));
		} finally {
			busy = false;
		}
	}

	const attachment = $derived(current?.attachment);
</script>

<div class="flex flex-col gap-4 md:gap-6" use:reveal>
	<div data-reveal>
		<PageHeader
			title="Context"
			description="Attach the studio to a tenant, project and environment."
		>
			<Badge variant={attachment?.status === "attached" ? "secondary" : "outline"} class="capitalize">
				{attachment?.status ?? "detached"}
			</Badge>
		</PageHeader>
	</div>

	<DataState loading={loading} error={error}>
		<div class="grid gap-4 lg:grid-cols-3" data-reveal>
			<Card.Root class="lg:col-span-2">
				<Card.Header>
					<Card.Title>Active attachment</Card.Title>
					<Card.Description>Current runtime binding.</Card.Description>
				</Card.Header>
				<Card.Content class="grid grid-cols-2 gap-6 py-6 sm:grid-cols-4">
					<Metric label="Tenant" value={current?.context.tenant_name ?? "—"} icon={GlobeIcon} />
					<Metric label="Project" value={current?.context.project_name ?? "—"} icon={LayersIcon} />
					<Metric
						label="Environment"
						value={current?.context.environment_name ?? "—"}
						icon={TargetIcon}
					/>
					<Metric label="Targets" value={targets.length} />
					{#if current?.context.environment_connection_ref}
						<div class="col-span-2 flex flex-col gap-1 sm:col-span-4">
							<span class="text-muted-foreground text-xs uppercase tracking-wide">
								Connection
							</span>
							<code class="bg-muted truncate rounded px-2 py-1 text-xs">
								{current.context.environment_connection_ref}
							</code>
						</div>
					{/if}
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Title>Switch</Card.Title>
					<Card.Description>Pick a target and attach.</Card.Description>
				</Card.Header>
				<Card.Content class="flex flex-col gap-4">
					<div class="flex flex-col gap-2">
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
					<div class="flex flex-col gap-2">
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
					<div class="flex flex-col gap-2">
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
					<Button disabled={busy || !tenant || !project || !environment} onclick={apply}>
						Attach
					</Button>
				</Card.Content>
			</Card.Root>

			<Card.Root class="lg:col-span-3">
				<Card.Header>
					<Card.Title>Targets</Card.Title>
					<Card.Description>Every configured tenant · project · environment.</Card.Description>
				</Card.Header>
				<Card.Content>
					{#if targets.length}
						<Table.Root>
							<Table.Header>
								<Table.Row>
									<Table.Head>Tenant</Table.Head>
									<Table.Head>Project</Table.Head>
									<Table.Head>Environment</Table.Head>
									<Table.Head>Entry</Table.Head>
									<Table.Head>Status</Table.Head>
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#each targets as target (`${target.tenant_slug}-${target.project_slug}-${target.environment}`)}
									<Table.Row data-active={target.active}>
										<Table.Cell>{target.tenant_name}</Table.Cell>
										<Table.Cell class="font-medium">{target.project_name}</Table.Cell>
										<Table.Cell>{target.environment}</Table.Cell>
										<Table.Cell>
											<code class="text-xs">{target.entry ?? "—"}</code>
										</Table.Cell>
										<Table.Cell>
											<Badge variant={target.active ? "secondary" : "outline"} class="capitalize">
												{target.display_status}
											</Badge>
										</Table.Cell>
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					{:else}
						<p class="text-muted-foreground text-sm">No targets configured.</p>
					{/if}
				</Card.Content>
			</Card.Root>
		</div>
	</DataState>
</div>
