<script lang="ts">
	import { onMount } from "svelte";
	import { base } from "$app/paths";
	import { goto } from "$app/navigation";
	import LogOutIcon from "@lucide/svelte/icons/log-out";
	import SearchIcon from "@lucide/svelte/icons/search";
	import * as Command from "$lib/components/ui/command/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import { logout } from "$lib/auth";
	import { NAV_SECTIONS, type NavItem } from "$lib/nav";

	let open = $state(false);

	onMount(() => {
		const onKey = (event: KeyboardEvent) => {
			if (event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey)) {
				event.preventDefault();
				open = !open;
			}
		};
		window.addEventListener("keydown", onKey);
		return () => window.removeEventListener("keydown", onKey);
	});

	function run(item: NavItem) {
		open = false;
		goto(`${base}${item.href}`);
	}
</script>

<Button
	variant="outline"
	size="sm"
	class="text-muted-foreground w-full justify-start gap-2 sm:w-56"
	onclick={() => (open = true)}
>
	<SearchIcon data-icon="inline-start" />
	<span class="hidden sm:inline">Search…</span>
	<kbd
		class="bg-muted ms-auto hidden rounded border px-1.5 font-mono text-[10px] sm:inline-block"
	>
		⌘K
	</kbd>
</Button>

<Command.Dialog bind:open title="Command palette" description="Jump to a Studio page">
	<Command.Input placeholder="Search pages and actions…" />
	<Command.List>
		<Command.Empty>No results found.</Command.Empty>
		{#each NAV_SECTIONS as section (section.section)}
			<Command.Group heading={section.section}>
				{#each section.items as item (item.key)}
					{@const Icon = item.icon}
					<Command.Item onSelect={() => run(item)}>
						<Icon />
						<span>{item.label}</span>
					</Command.Item>
				{/each}
			</Command.Group>
		{/each}
		<Command.Separator />
		<Command.Group heading="Account">
			<Command.Item onSelect={() => logout()}>
				<LogOutIcon />
				<span>Log out</span>
			</Command.Item>
		</Command.Group>
	</Command.List>
</Command.Dialog>
