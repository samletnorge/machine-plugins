<script lang="ts">
	import './layout.css';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { getUser, login } from '$lib/auth';

	let { children } = $props();

	const PUBLIC_ROUTES = ['/login-02', '/signup-02'];

	onMount(async () => {
		const path = page.url.pathname;
		if (PUBLIC_ROUTES.some((route) => path.endsWith(route))) return;
		const user = await getUser();
		if (!user) login();
	});
</script>

{@render children()}
