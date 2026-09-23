<script lang="ts">
	import PlayIcon from "@lucide/svelte/icons/play";
	import { toast } from "svelte-sonner";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Dialog from "$lib/components/ui/dialog/index.js";
	import { Label } from "$lib/components/ui/label/index.js";
	import { Textarea } from "$lib/components/ui/textarea/index.js";
	import { executeTool, getToolDetail, type ToolDetail } from "$lib/api";

	let { toolName }: { toolName: string } = $props();

	let open = $state(false);
	let detail = $state<ToolDetail | null>(null);
	let payload = $state("{}");
	let result = $state<string | null>(null);
	let busy = $state(false);

	async function load() {
		result = null;
		try {
			detail = await getToolDetail(toolName);
			const props = detail.input_schema?.properties ?? {};
			const example: Record<string, unknown> = {};
			for (const key of Object.keys(props)) example[key] = "";
			payload = JSON.stringify(example, null, 2);
		} catch {
			detail = null;
			payload = "{}";
		}
	}

	async function run() {
		busy = true;
		result = null;
		try {
			const body = JSON.parse(payload || "{}") as Record<string, unknown>;
			const response = await executeTool(toolName, body);
			result = JSON.stringify(response.result, null, 2);
			toast.success(`${toolName} executed`);
		} catch (caught) {
			result = caught instanceof Error ? caught.message : String(caught);
			toast.error(`${toolName} failed`);
		} finally {
			busy = false;
		}
	}
</script>

<Dialog.Root bind:open onOpenChange={(value) => value && load()}>
	<Dialog.Trigger>
		{#snippet child({ props })}
			<Button variant="outline" size="sm" {...props}>
				<PlayIcon data-icon="inline-start" />
				Run
			</Button>
		{/snippet}
	</Dialog.Trigger>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>Run {toolName}</Dialog.Title>
			<Dialog.Description>
				{detail?.description ?? "Send a JSON payload to this tool."}
			</Dialog.Description>
		</Dialog.Header>
		<div class="grid gap-4">
			<div class="grid gap-2">
				<Label for="payload">Input (JSON)</Label>
				<Textarea id="payload" bind:value={payload} class="min-h-[120px] font-mono text-xs" />
			</div>
			{#if result}
				<div class="grid gap-2">
					<span class="text-muted-foreground text-xs uppercase tracking-wide">Result</span>
					<pre
						class="bg-muted max-h-56 overflow-auto rounded-lg p-3 text-xs">{result}</pre>
				</div>
			{/if}
		</div>
		<Dialog.Footer>
			<Button disabled={busy} onclick={run}>
				<PlayIcon data-icon="inline-start" />
				Execute
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
