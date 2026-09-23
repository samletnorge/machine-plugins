<script lang="ts">
	import SidebarIcon from "@lucide/svelte/icons/sidebar";
	import * as Breadcrumb from "$lib/components/ui/breadcrumb/index.js";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import { Separator } from "$lib/components/ui/separator/index.js";
	import CommandMenu from "./command-menu.svelte";
	import { studio } from "$lib/store.svelte";

	let { title = "Overview" }: { title?: string } = $props();

	const sidebar = Sidebar.useSidebar();
	const overview = $derived(studio.overview);
	const attached = $derived(overview?.attachment_status === "attached");
</script>

<header class="sticky top-0 z-50 flex w-full items-center border-b bg-background">
	<div class="flex h-(--header-height) w-full items-center gap-2 px-4">
		<Button class="size-8" variant="ghost" size="icon" onclick={sidebar.toggle}>
			<SidebarIcon />
			<span class="sr-only">Toggle sidebar</span>
		</Button>
		<Separator orientation="vertical" class="me-1 hidden h-4 sm:block" />
		<div class="flex items-center gap-2">
			<div
				class="bg-primary text-primary-foreground flex size-7 items-center justify-center rounded-md"
			>
				<svg viewBox="0 0 48 48" fill="none" class="size-4">
					<path
						d="M11 36V12L24 27L37 12V36"
						stroke="currentColor"
						stroke-width="6"
						stroke-linecap="round"
						stroke-linejoin="round"
					/>
				</svg>
			</div>
			<span class="hidden text-sm font-semibold sm:inline">Machine Core</span>
		</div>
		<Separator orientation="vertical" class="mx-1 h-4" />
		<Breadcrumb.Root class="hidden sm:block">
			<Breadcrumb.List>
				<Breadcrumb.Item>
					<Breadcrumb.Link href="/_studio/app/">Studio</Breadcrumb.Link>
				</Breadcrumb.Item>
				<Breadcrumb.Separator />
				<Breadcrumb.Item>
					<Breadcrumb.Page>{title}</Breadcrumb.Page>
				</Breadcrumb.Item>
			</Breadcrumb.List>
		</Breadcrumb.Root>
		<div class="ms-auto flex items-center gap-2">
			{#if overview}
				<Badge variant={attached ? "secondary" : "outline"} class="hidden capitalize sm:inline-flex">
					{overview.environment_display_status ?? overview.attachment_status}
				</Badge>
			{/if}
			<CommandMenu />
		</div>
	</div>
</header>
