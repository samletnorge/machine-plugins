<script lang="ts">
	import { base } from "$app/paths";
	import { page } from "$app/state";
	import AppShell from "$lib/components/studio/app-shell.svelte";
	import { NAV_SECTIONS } from "$lib/nav";

	let { children } = $props();

	const pathname = $derived(page.url.pathname);

	const title = $derived.by(() => {
		if (pathname.includes("/domain/")) return "Control plane";
		const rel = pathname.startsWith(base) ? pathname.slice(base.length) : pathname;
		if (rel === "" || rel === "/") return "Dashboard";
		for (const section of NAV_SECTIONS) {
			for (const item of section.items) {
				if (item.href !== "/" && (rel === item.href || rel.startsWith(`${item.href}/`))) {
					return item.label;
				}
			}
		}
		return "Studio";
	});
</script>

<AppShell {title}>{@render children()}</AppShell>
