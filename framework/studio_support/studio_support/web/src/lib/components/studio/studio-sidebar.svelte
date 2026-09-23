<script lang="ts">
	import { base } from "$app/paths";
	import { page } from "$app/state";
	import InnerShadowTopIcon from "@tabler/icons-svelte/icons/inner-shadow-top";
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import { NAV_SECTIONS } from "$lib/nav";
	import { studio } from "$lib/store.svelte";
	import StudioUser from "./studio-user.svelte";

	const pathname = $derived(page.url.pathname);
	const machineName = $derived(studio.overview?.machine_name ?? "Machine Studio");
	const contextLabel = $derived(
		[studio.overview?.tenant_name, studio.overview?.project_name, studio.overview?.environment]
			.filter(Boolean)
			.join(" · ")
	);

	function isActive(href: string): boolean {
		const target = `${base}${href}`;
		if (href === "/") return pathname === target || pathname === base;
		return pathname === target || pathname.startsWith(`${target}/`);
	}
</script>

<Sidebar.Root collapsible="offcanvas">
	<Sidebar.Header>
		<Sidebar.Menu>
			<Sidebar.MenuItem>
				<Sidebar.MenuButton size="lg" class="data-[slot=sidebar-menu-button]:!p-1.5">
					{#snippet child({ props })}
						<a href="{base}/" {...props}>
							<div
								class="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
							>
								<InnerShadowTopIcon class="size-5" />
							</div>
							<div class="grid flex-1 text-start text-sm leading-tight">
								<span class="truncate font-semibold">{machineName}</span>
								{#if contextLabel}
									<span class="truncate text-xs text-muted-foreground">{contextLabel}</span>
								{/if}
							</div>
						</a>
					{/snippet}
				</Sidebar.MenuButton>
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
							<Sidebar.MenuButton isActive={isActive(item.href)}>
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
		<StudioUser />
	</Sidebar.Footer>
</Sidebar.Root>
