<script lang="ts">
	import * as Avatar from "$lib/components/ui/avatar/index.js";
	import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import InfoCircleIcon from "@tabler/icons-svelte/icons/info-circle";
	import LogoutIcon from "@tabler/icons-svelte/icons/logout";
	import DotsVerticalIcon from "@tabler/icons-svelte/icons/dots-vertical";
	import UserCircleIcon from "@tabler/icons-svelte/icons/user-circle";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { logout } from "$lib/auth";
	import { initials, studio } from "$lib/store.svelte";

	const sidebar = Sidebar.useSidebar();
	const user = $derived(studio.user);
	const label = $derived(user?.name || user?.email || "Signed in");
	const sublabel = $derived(user?.email ?? "");
	const initialsText = $derived(initials(user?.name, user?.email));
</script>

<Sidebar.Menu>
	<Sidebar.MenuItem>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Sidebar.MenuButton
						{...props}
						size="lg"
						class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
					>
						<Avatar.Root class="size-8 rounded-lg">
							<Avatar.Fallback class="rounded-lg">{initialsText}</Avatar.Fallback>
						</Avatar.Root>
						<div class="grid flex-1 text-start text-sm leading-tight">
							<span class="truncate font-medium">{label}</span>
							<span class="truncate text-xs text-muted-foreground">{sublabel}</span>
						</div>
						<DotsVerticalIcon class="ms-auto size-4" />
					</Sidebar.MenuButton>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content
				class="w-(--bits-dropdown-menu-anchor-width) min-w-56 rounded-lg"
				side={sidebar.isMobile ? "bottom" : "right"}
				align="end"
				sideOffset={4}
			>
				<DropdownMenu.Label class="p-0 font-normal">
					<div class="flex items-center gap-2 px-1 py-1.5 text-start text-sm">
						<Avatar.Root class="size-8 rounded-lg">
							<Avatar.Fallback class="rounded-lg">{initialsText}</Avatar.Fallback>
						</Avatar.Root>
						<div class="grid flex-1 text-start text-sm leading-tight">
							<span class="truncate font-medium">{label}</span>
							<span class="truncate text-xs text-muted-foreground">{sublabel}</span>
						</div>
					</div>
				</DropdownMenu.Label>
				{#if user?.roles?.length}
					<DropdownMenu.Separator />
					<DropdownMenu.Label class="flex flex-wrap gap-1">
						{#each user.roles as role (role)}
							<Badge variant="secondary" class="capitalize">{role}</Badge>
						{/each}
					</DropdownMenu.Label>
				{/if}
				<DropdownMenu.Separator />
				<DropdownMenu.Group>
					<DropdownMenu.Item disabled>
						<UserCircleIcon />
						{sublabel}
					</DropdownMenu.Item>
					<DropdownMenu.Item disabled>
						<InfoCircleIcon />
						Studio v0.2
					</DropdownMenu.Item>
				</DropdownMenu.Group>
				<DropdownMenu.Separator />
				<DropdownMenu.Item onSelect={() => logout()}>
					<LogoutIcon />
					Log out
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</Sidebar.MenuItem>
</Sidebar.Menu>
