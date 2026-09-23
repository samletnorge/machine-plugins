<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { FieldGroup, Field, FieldSeparator } from "$lib/components/ui/field/index.js";
	import { cn, type WithElementRef } from "$lib/utils.js";
	import { login } from "$lib/auth";
	import type { HTMLFormAttributes } from "svelte/elements";

	let {
		ref = $bindable(null),
		class: className,
		...restProps
	}: WithElementRef<HTMLFormAttributes> = $props();

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		login();
	}
</script>

<form
	class={cn("flex flex-col gap-6", className)}
	bind:this={ref}
	onsubmit={handleSubmit}
	{...restProps}
>
	<FieldGroup>
		<div class="flex flex-col items-center gap-1 text-center">
			<h1 class="text-2xl font-bold">Welcome back</h1>
			<p class="text-sm text-balance text-muted-foreground">
				Sign in with your organization account to continue to Machine Studio.
			</p>
		</div>
		<Field>
			<Button type="submit">Continue with SSO</Button>
		</Field>
		<FieldSeparator>Machine Core</FieldSeparator>
	</FieldGroup>
</form>
