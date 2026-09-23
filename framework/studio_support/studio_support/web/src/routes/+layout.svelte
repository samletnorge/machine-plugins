<script lang="ts">
	import './layout.css';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { login } from '$lib/auth';
	import { loadStudio, studio } from '$lib/store.svelte';

	let { children } = $props();

	const PUBLIC_ROUTES = ['/login-02', '/signup-02'];

	onMount(async () => {
		const path = page.url.pathname;
		if (PUBLIC_ROUTES.some((route) => path.endsWith(route))) return;
		await loadStudio();
		if (!studio.user) login();
	});
</script>

{@render children()}
