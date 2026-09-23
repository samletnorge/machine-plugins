<script lang="ts">
	import * as Field from "$lib/components/ui/field/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import { cn } from "$lib/utils.js";
	import { login } from "$lib/auth";
	import type { HTMLAttributes } from "svelte/elements";

	let { class: className, ...restProps }: HTMLAttributes<HTMLFormElement> = $props();

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		login();
	}
</script>

<form class={cn("flex flex-col gap-6", className)} onsubmit={handleSubmit} {...restProps}>
	<Field.Group>
		<div class="flex flex-col items-center gap-1 text-center">
			<h1 class="text-2xl font-bold">Create your account</h1>
			<p class="text-sm text-balance text-muted-foreground">
				Accounts are managed by your organization's identity provider. Continue to sign up with
				SSO.
			</p>
		</div>
		<Field.Field>
			<Button type="submit">Continue with SSO</Button>
		</Field.Field>
		<Field.Separator>Machine Core</Field.Separator>
	</Field.Group>
</form>
