<script lang="ts">
	import { base } from "$app/paths";
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import CheckIcon from "@lucide/svelte/icons/check";
	import ChevronsUpDownIcon from "@lucide/svelte/icons/chevrons-up-down";
	import Settings2Icon from "@lucide/svelte/icons/settings-2";
	import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import { getEnvironments, getProjects, switchContext } from "$lib/api";
	import { NAV_SECTIONS } from "$lib/nav";
	import { loadStudio, studio } from "$lib/store.svelte";
	import NavUser from "./nav-user.svelte";
	import type { ComponentProps } from "svelte";

	let { ...restProps }: ComponentProps<typeof Sidebar.Root> = $props();

	const pathname = $derived(page.url.pathname);
	const overview = $derived(studio.overview);
	const tenants = $derived(overview?.tenant_options ?? []);

	function isActive(href: string): boolean {
		const target = `${base}${href}`;
		if (href === "/") return pathname === target || pathname === base;
		return pathname === target || pathname.startsWith(`${target}/`);
	}

	function initial(name: string): string {
		return name.trim().slice(0, 2).toUpperCase();
	}

	async function quickSwitch(slug: string) {
		const projects = await getProjects(slug);
		const project = projects[0];
		if (!project) return;
		const environments = await getEnvironments(project.slug);
		const environment = environments[0];
		if (!environment) return;
		await switchContext({
			tenant_slug: slug,
			project_slug: project.slug,
			environment_name: environment.name,
		});
		await loadStudio(true);
	}
</script>

<Sidebar.Root
	class="top-(--header-height) h-[calc(100svh_-_var(--header-height))]!"
	{...restProps}
>
	<Sidebar.Header>
		<Sidebar.Menu>
			<Sidebar.MenuItem>
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Sidebar.MenuButton
								size="lg"
								class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
								{...props}
							>
								<div
									class="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground"
								>
									<svg viewBox="0 0 48 48" fill="none" class="size-5">
										<path
											d="M11 36V12L24 27L37 12V36"
											stroke="currentColor"
											stroke-width="5"
											stroke-linecap="round"
											stroke-linejoin="round"
										/>
									</svg>
								</div>
								<div class="grid flex-1 text-start text-sm leading-tight">
									<span class="truncate font-medium">{overview?.tenant_name ?? "Machine Core"}</span>
									<span class="truncate text-xs">
										{overview?.project_name ?? "No project"}{#if overview?.environment}· {overview.environment}{/if}
									</span>
								</div>
								<ChevronsUpDownIcon class="ms-auto size-4" />
							</Sidebar.MenuButton>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content
						class="w-(--bits-dropdown-menu-anchor-width) min-w-56 rounded-lg"
						align="start"
						side="bottom"
						sideOffset={4}
					>
						<DropdownMenu.Label class="text-muted-foreground text-xs">Tenants</DropdownMenu.Label>
						<DropdownMenu.Group>
							{#each tenants as tenant (tenant.slug)}
								<DropdownMenu.Item
									class="gap-2"
									disabled={tenant.active}
									onSelect={() => tenant.slug && !tenant.active && quickSwitch(tenant.slug)}
								>
									<div
										class="flex size-6 items-center justify-center rounded-md border text-[10px] font-medium"
									>
										{initial(tenant.name)}
									</div>
									<span class="truncate">{tenant.name}</span>
									{#if tenant.active}
										<CheckIcon class="ms-auto" />
									{/if}
								</DropdownMenu.Item>
							{/each}
							{#if tenants.length === 0}
								<DropdownMenu.Item disabled>No tenants configured</DropdownMenu.Item>
							{/if}
						</DropdownMenu.Group>
						<DropdownMenu.Separator />
						<DropdownMenu.Item onSelect={() => goto(`${base}/context`)}>
							<Settings2Icon />
							Manage context
						</DropdownMenu.Item>
					</DropdownMenu.Content>
				</DropdownMenu.Root>
			</Sidebar.MenuItem>
		</Sidebar.Menu>
	</Sidebar.Header>
	<Sidebar.Content>
		{#each NAV_SECTIONS as section (section.section)}
			<Sidebar.Group>
				<Sidebar.GroupLabel>{section.section}</Sidebar.GroupLabel>
				<Sidebar.Menu>
					{#each section.items as item (item.key)}
						{@const Icon = item.icon}
						<Sidebar.MenuItem>
							<Sidebar.MenuButton isActive={isActive(item.href)} tooltipContent={item.label}>
								{#snippet child({ props })}
									<a href="{base}{item.href}" {...props}>
										<Icon />
										<span>{item.label}</span>
									</a>
								{/snippet}
							</Sidebar.MenuButton>
						</Sidebar.MenuItem>
					{/each}
				</Sidebar.Menu>
			</Sidebar.Group>
		{/each}
	</Sidebar.Content>
	<Sidebar.Footer>
		<NavUser />
	</Sidebar.Footer>
</Sidebar.Root>
