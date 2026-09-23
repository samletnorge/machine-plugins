<script lang="ts">
	import { onMount, tick } from "svelte";
	import BotIcon from "@lucide/svelte/icons/bot";
	import MessagesSquareIcon from "@lucide/svelte/icons/messages-square";
	import PlusIcon from "@lucide/svelte/icons/plus";
	import SendIcon from "@lucide/svelte/icons/send";
	import { toast } from "svelte-sonner";
	import DataState from "$lib/components/studio/data-state.svelte";
	import PageHeader from "$lib/components/studio/page-header.svelte";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import * as Empty from "$lib/components/ui/empty/index.js";
	import * as ScrollArea from "$lib/components/ui/scroll-area/index.js";
	import * as Select from "$lib/components/ui/select/index.js";
	import { Textarea } from "$lib/components/ui/textarea/index.js";
	import {
		createChatSession,
		getChatThreads,
		sendChatMessage,
		type ChatThread,
	} from "$lib/api";
	import { reveal } from "$lib/motion";

	let loading = $state(true);
	let error = $state<string | null>(null);
	let agents = $state<string[]>([]);
	let threads = $state<ChatThread[]>([]);
	let activeId = $state("");
	let agent = $state("");
	let draft = $state("");
	let sending = $state(false);
	let viewport = $state<HTMLElement | null>(null);

	const active = $derived(threads.find((thread) => thread.thread_id === activeId) ?? null);
	const messages = $derived(active?.messages ?? []);

	onMount(async () => {
		try {
			const data = await getChatThreads();
			agents = data.catalog.agents;
			threads = data.threads;
			agent = agents[0] ?? "";
			if (threads.length) {
				selectThread(threads[0]);
			} else if (agents.length) {
				await newThread();
			}
		} catch (caught) {
			error = caught instanceof Error ? caught.message : String(caught);
		} finally {
			loading = false;
		}
	});

	async function scrollToEnd() {
		await tick();
		if (viewport) viewport.scrollTop = viewport.scrollHeight;
	}

	function selectThread(thread: ChatThread) {
		activeId = thread.thread_id;
		agent = thread.agent || agents[0] || "";
		scrollToEnd();
	}

	async function newThread() {
		try {
			const session = await createChatSession();
			threads = [...threads, { thread_id: session.thread_id, agent: "", messages: [] }];
			activeId = session.thread_id;
			agent = agent || agents[0] || "";
		} catch (caught) {
			toast.error(caught instanceof Error ? caught.message : String(caught));
		}
	}

	async function send() {
		const text = draft.trim();
		if (!text || !agent || !activeId || sending) return;
		draft = "";
		sending = true;

		threads = threads.map((thread) =>
			thread.thread_id === activeId
				? { ...thread, agent, messages: [...thread.messages, { role: "user", content: text }] }
				: thread
		);
		await scrollToEnd();

		try {
			const response = await sendChatMessage(activeId, agent, text);
			threads = threads.map((thread) =>
				thread.thread_id === activeId
					? { ...thread, agent, messages: response.messages }
					: thread
			);
			await scrollToEnd();
		} catch (caught) {
			toast.error(caught instanceof Error ? caught.message : String(caught));
		} finally {
			sending = false;
		}
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === "Enter" && !event.shiftKey) {
			event.preventDefault();
			send();
		}
	}
</script>

<div class="flex flex-col gap-4 md:gap-6" use:reveal>
	<div data-reveal>
		<PageHeader title="Chat" description="Talk to the agents registered in the attached runtime.">
			<Badge variant="outline">{agents.length} agents</Badge>
		</PageHeader>
	</div>

	<DataState loading={loading} error={error}>
		{#if agents.length === 0}
			<Card.Root data-reveal>
				<Card.Content class="py-6">
					<Empty.Root class="border-0">
						<Empty.Header>
							<Empty.Media variant="icon">
								<BotIcon />
							</Empty.Media>
							<Empty.Title>No chat-capable agents</Empty.Title>
							<Empty.Description>
								Register an agent whose <code>run</code> accepts a single message to chat with it
								here.
							</Empty.Description>
						</Empty.Header>
					</Empty.Root>
				</Card.Content>
			</Card.Root>
		{:else}
			<div class="grid gap-4 lg:grid-cols-[300px_1fr]" data-reveal>
				<Card.Root class="h-fit">
					<Card.Header>
						<Card.Title>Threads</Card.Title>
						<Card.Action>
							<Button variant="outline" size="sm" onclick={newThread}>
								<PlusIcon data-icon="inline-start" />
								New
							</Button>
						</Card.Action>
					</Card.Header>
					<Card.Content class="flex flex-col gap-4">
						<div class="flex flex-col gap-2">
							<span class="text-muted-foreground text-xs uppercase tracking-wide">Agent</span>
							<Select.Root type="single" value={agent} onValueChange={(value) => (agent = value)}>
								<Select.Trigger class="w-full">
									<span data-slot="select-value">{agent || "Select agent"}</span>
								</Select.Trigger>
								<Select.Content>
									{#each agents as option (option)}
										<Select.Item value={option}>{option}</Select.Item>
									{/each}
								</Select.Content>
							</Select.Root>
						</div>
						<div class="flex flex-col gap-1">
							{#each threads as thread (thread.thread_id)}
								<button
									type="button"
									class="hover:bg-accent hover:text-accent-foreground flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors data-[active=true]:bg-accent"
									data-active={thread.thread_id === activeId}
									onclick={() => selectThread(thread)}
								>
									<span class="flex items-center gap-2 truncate">
										<MessagesSquareIcon class="text-muted-foreground size-4" />
										<span class="truncate">{thread.thread_id}</span>
									</span>
									<Badge variant="outline" class="text-xs">{thread.messages.length}</Badge>
								</button>
							{/each}
						</div>
					</Card.Content>
				</Card.Root>

				<Card.Root class="flex min-h-[min(70vh,640px)] flex-col">
					<Card.Header>
						<Card.Title class="flex items-center gap-2">
							<BotIcon class="text-muted-foreground" />
							{agent || "Agent"}
						</Card.Title>
						<Card.Description>{activeId || "No thread selected"}</Card.Description>
					</Card.Header>
					<Card.Content class="flex flex-1 flex-col gap-4">
						<ScrollArea.Root bind:viewportRef={viewport} class="h-[min(52vh,460px)] pe-3">
							{#if messages.length === 0}
								<p class="text-muted-foreground py-10 text-center text-sm">
									Send a message to start the conversation.
								</p>
							{:else}
								<div class="flex flex-col gap-3">
									{#each messages as message, index (index)}
										<div
											class="flex"
											class:justify-end={message.role === "user"}
										>
											<div
												class="max-w-[80%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap {message.role ===
												'user'
													? 'bg-primary text-primary-foreground'
													: 'bg-muted'}"
											>
												{message.content}
											</div>
										</div>
									{/each}
								</div>
							{/if}
						</ScrollArea.Root>

						<div class="flex items-end gap-2">
							<Textarea
								bind:value={draft}
								onkeydown={onKeydown}
								placeholder="Message the agent… (Enter to send, Shift+Enter for newline)"
								class="min-h-[52px] resize-none"
								rows={2}
							/>
							<Button disabled={sending || !draft.trim()} onclick={send}>
								<SendIcon data-icon="inline-start" />
								Send
							</Button>
						</div>
					</Card.Content>
				</Card.Root>
			</div>
		{/if}
	</DataState>
</div>
