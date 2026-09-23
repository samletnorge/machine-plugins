<script lang="ts">
	import ChevronsUpDownIcon from "@lucide/svelte/icons/chevrons-up-down";
	import LogOutIcon from "@lucide/svelte/icons/log-out";
	import ShieldCheckIcon from "@lucide/svelte/icons/shield-check";
	import UserIcon from "@lucide/svelte/icons/user";
	import * as Avatar from "$lib/components/ui/avatar/index.js";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import { logout } from "$lib/auth";
	import { initials, studio } from "$lib/store.svelte";

	const sidebar = Sidebar.useSidebar();
	const user = $derived(studio.user);
	const name = $derived(user?.name || user?.email || "Signed in");
	const email = $derived(user?.email ?? "");
	const roles = $derived(user?.roles ?? []);
</script>

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
						<Avatar.Root class="size-8 rounded-lg">
							<Avatar.Fallback class="rounded-lg">{initials(user?.name, user?.email)}</Avatar.Fallback>
						</Avatar.Root>
						<div class="grid flex-1 text-start text-sm leading-tight">
							<span class="truncate font-medium">{name}</span>
							<span class="truncate text-xs">{email}</span>
						</div>
						<ChevronsUpDownIcon class="ms-auto size-4" />
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
							<Avatar.Fallback class="rounded-lg">{initials(user?.name, user?.email)}</Avatar.Fallback>
						</Avatar.Root>
						<div class="grid flex-1 text-start text-sm leading-tight">
							<span class="truncate font-medium">{name}</span>
							<span class="truncate text-xs">{email}</span>
						</div>
					</div>
				</DropdownMenu.Label>
				{#if roles.length}
					<DropdownMenu.Separator />
					<DropdownMenu.Label class="flex flex-wrap items-center gap-1">
						<ShieldCheckIcon class="size-3.5 text-muted-foreground" />
						{#each roles as role (role)}
							<Badge variant="secondary" class="capitalize">{role}</Badge>
						{/each}
					</DropdownMenu.Label>
				{/if}
				<DropdownMenu.Separator />
				<DropdownMenu.Group>
					<DropdownMenu.Item disabled>
						<UserIcon />
						{email || "No email"}
					</DropdownMenu.Item>
				</DropdownMenu.Group>
				<DropdownMenu.Separator />
				<DropdownMenu.Item onSelect={() => logout()}>
					<LogOutIcon />
					Log out
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</Sidebar.MenuItem>
</Sidebar.Menu>
