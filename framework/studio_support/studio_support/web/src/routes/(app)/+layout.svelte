<script lang="ts">
	import AppSidebar from "$lib/components/app-sidebar.svelte";
	import SiteHeader from "$lib/components/site-header.svelte";
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import { Toaster } from "$lib/components/ui/sonner/index.js";
	import { base } from "$app/paths";
	import { page } from "$app/state";
	import { titleFor } from "$lib/nav";

	let { children } = $props();

	const title = $derived(titleFor(page.url.pathname, base));
</script>

<div class="[--header-height:calc(--spacing(14))]">
	<Sidebar.Provider class="flex flex-col">
		<SiteHeader {title} />
		<div class="flex flex-1">
			<AppSidebar />
			<Sidebar.Inset>
				<div class="flex flex-1 flex-col gap-4 p-4 md:gap-6 md:p-6">
					{@render children()}
				</div>
			</Sidebar.Inset>
		</div>
	</Sidebar.Provider>
	<Toaster />
</div>
