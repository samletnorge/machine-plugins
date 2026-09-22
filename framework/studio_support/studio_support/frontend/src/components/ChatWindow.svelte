<script lang="ts">
  import { getJson, postJson } from '../lib/api';
  import { deriveChatInteractionState, deriveChatViewState, deriveInitialTab, deriveTabSelection, deriveTargetChange } from '../lib/chat-state';
  import { renderMarkdown as renderMarkdownContent } from '../lib/markdown';
  import type { ChatMessage, ChatThreadsPayload } from '../lib/types';

  interface Props {
    threadsEndpoint: string;
    messagesEndpoint: string;
    sessionsEndpoint?: string;
    renderMarkdown?: string;
    chatTabs?: string;
    activeContext?: string;
    attachment?: string;
  }

  let {
    threadsEndpoint,
    messagesEndpoint,
    sessionsEndpoint = '',
    renderMarkdown = 'false',
    chatTabs = '',
    activeContext = '',
    attachment = ''
  }: Props = $props();

  let threads = $state<ChatThreadsPayload['threads']>([]);
  let catalog = $state<ChatThreadsPayload['catalog']>({ agents: [], runtimes: [] });
  let selectedThread = $state('default');
  let selectedAgent = $state('');
  let selectedAgentTarget = $state('');
  let selectedRuntimeTarget = $state('');
  let tabs = $derived(chatTabs.split(',').filter(Boolean) as Array<'agents' | 'runtimes'>);
  let activeTab = $state<'agents' | 'runtimes'>(deriveInitialTab([]));
  let messages = $state<ChatMessage[]>([]);
  let draft = $state('');
  let sending = $state(false);
  let loadError = $state('');
  let stamps = $state<Record<string, number>>({});
  let transcriptEl = $state<HTMLDivElement | null>(null);

  let sessionMessagesEndpoint = $derived(
    messagesEndpoint.replace('/default/messages', `/${selectedThread}/messages`)
  );

  function onDraftKeydown(event: KeyboardEvent) {
    if (event.key !== 'Enter' || event.shiftKey) return;
    event.preventDefault();
    void sendMessage();
  }

  let markdownEnabled = $derived(renderMarkdown === 'true');
  let runtimesPlanningOnly = $derived(activeTab === 'runtimes');
  let interactionState = $derived(
    deriveChatInteractionState(activeTab, sending, selectedAgent, catalog, draft, Boolean(sessionsEndpoint))
  );

  let activeCatalog = $derived.by(() => catalog[activeTab] ?? []);
  let quickActions = $derived.by(() => {
    if (activeTab === 'runtimes') {
      return [
        'List the runtime capabilities available in this project.',
        'Explain which runtime to use for a Brreg lookup.',
        'Summarize the inputs this runtime expects before I run it.'
      ];
    }

    return [
      'Find a company by name and explain which register endpoint you used.',
      'Look up an organisation number and summarize the key registry facts.',
      'Compare two possible lookup strategies before calling any tool.'
    ];
  });

  let scrollSignal = $derived(messages.length + (sending ? 1 : 0));

  const chevronIcon = `<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m5 7 5 6 5-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const sendIcon = `<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4 10h9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="m10 4 6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const spinnerIcon = `<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.8" opacity="0.28"/><path d="M17 10a7 7 0 0 0-7-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;
  const botIcon = `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="4" y="7.5" width="16" height="11" rx="3" stroke="currentColor" stroke-width="1.6"/><circle cx="9.4" cy="13" r="1.15" fill="currentColor"/><circle cx="14.6" cy="13" r="1.15" fill="currentColor"/><path d="M12 7.5V4.6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="12" cy="3.7" r="1.05" fill="currentColor"/></svg>`;
  const userIcon = `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="8.2" r="3.3" stroke="currentColor" stroke-width="1.6"/><path d="M5.3 19.4c1.3-3.1 3.8-4.7 6.7-4.7s5.4 1.6 6.7 4.7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`;
  const alertIcon = `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 8.4v4.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="16.5" r="1.1" fill="currentColor"/><path d="M10.4 3.9 2.8 17.2a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L13.6 3.9a2 2 0 0 0-3.2 0Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`;

  function stampKey(message: ChatMessage, index: number) {
    return `${selectedThread}:${index}:${message.role}:${message.content}`;
  }

  function formatStamp(message: ChatMessage, index: number) {
    const value = stamps[stampKey(message, index)];
    if (!value) return '';
    return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function applyQuickAction(prompt: string) {
    draft = prompt;
  }

  function applyViewState(nextActiveTab = activeTab) {
    const viewState = deriveChatViewState({
      activeTab: nextActiveTab,
      selectedThread,
      selectedAgent,
      threads,
      catalog
    });
    selectedThread = viewState.selectedThread;
    selectedAgent = viewState.selectedAgent;
    messages = viewState.messages;
    if (nextActiveTab === 'agents') {
      selectedAgentTarget = viewState.selectedAgent;
    } else {
      selectedRuntimeTarget = viewState.selectedAgent;
    }
  }

  function switchTab(tab: 'agents' | 'runtimes') {
    activeTab = tab;
    const currentSelection = tab === 'agents' ? selectedAgentTarget : selectedRuntimeTarget;
    selectedAgent = deriveTabSelection(tab, catalog, currentSelection);
    if (tab === 'agents') {
      selectedAgentTarget = selectedAgent;
    } else {
      selectedRuntimeTarget = selectedAgent;
    }
    applyViewState(tab);
  }

  function handleTargetChange(event: Event) {
    const nextTarget = (event.currentTarget as HTMLSelectElement).value;
    const nextViewState = deriveTargetChange(activeTab, nextTarget, selectedThread, messages);
    selectedThread = nextViewState.selectedThread;
    selectedAgent = nextViewState.selectedAgent;
    messages = nextViewState.messages;
    if (activeTab === 'agents') {
      selectedAgentTarget = nextTarget;
    } else {
      selectedRuntimeTarget = nextTarget;
    }
  }

  async function loadThreads() {
    try {
      const payload = await getJson<ChatThreadsPayload>(threadsEndpoint);
      catalog = payload.catalog;
      threads = payload.threads;
      applyViewState(activeTab);
      loadError = '';
    } catch (error) {
      loadError = error instanceof Error ? error.message : 'Failed to load threads';
    }
  }

  async function createSession() {
    if (!interactionState.canCreateSession) return;
    if (!sessionsEndpoint) return;
    try {
      const payload = await postJson<{ thread_id: string }>(sessionsEndpoint, {});
      selectedThread = payload.thread_id;
      await loadThreads();
      loadError = '';
    } catch (error) {
      loadError = error instanceof Error ? error.message : 'Failed to create session';
    }
  }

  function selectSession(threadId: string) {
    selectedThread = threadId;
    const thread = threads.find((item) => item.thread_id === threadId);
    if (!thread) {
      messages = [];
      return;
    }
    applyViewState(activeTab);
  }

  async function sendMessage() {
    if (sending) return;
    const sendTarget = selectedAgent;
    if (activeTab === 'runtimes') return;
    if (!catalog.agents.includes(sendTarget)) return;
    if (!draft.trim()) return;
    const message = draft.trim();
    draft = '';
    sending = true;
    try {
      const payload = await postJson<{ thread_id: string; messages: ChatMessage[] }>(sessionMessagesEndpoint, {
        agent: sendTarget,
        message
      });
      const updatedThread = { thread_id: payload.thread_id, agent: sendTarget, messages: payload.messages };
      const existingIndex = threads.findIndex((thread) => thread.thread_id === payload.thread_id);
      if (existingIndex >= 0) {
        threads = threads.map((thread) => (thread.thread_id === payload.thread_id ? updatedThread : thread));
      } else {
        threads = [updatedThread, ...threads];
      }
      selectedThread = payload.thread_id;
      messages = payload.messages;
      loadError = '';
    } catch (error) {
      draft = message + (draft ? ` ${draft}` : '');
      loadError = error instanceof Error ? error.message : 'Failed to send message';
    } finally {
      sending = false;
    }
  }

  $effect(() => {
    const initialTab = deriveInitialTab(tabs);
    if (!tabs.includes(activeTab)) {
      activeTab = initialTab;
    }
  });

  $effect(() => {
    void loadThreads();
  });

  $effect(() => {
    const list = messages;
    let next = stamps;
    let patched = false;
    list.forEach((message, index) => {
      const key = stampKey(message, index);
      if (!(key in next)) {
        if (!patched) {
          next = { ...next };
          patched = true;
        }
        next[key] = Date.now();
      }
    });
    if (patched) {
      stamps = next;
    }
  });

  $effect(() => {
    void scrollSignal;
    if (transcriptEl) {
      transcriptEl.scrollTop = transcriptEl.scrollHeight;
    }
  });
</script>

<section class="chat-console" aria-busy={sending}>
  {#if loadError}
    <div class="chat-alert" role="alert">
      <span class="chat-alert-icon" aria-hidden="true">{@html alertIcon}</span>
      <span class="chat-alert-copy">{loadError}</span>
      <button type="button" class="chat-alert-action" onclick={loadThreads}>Retry</button>
    </div>
  {/if}

  <div class="chat-workbench">
    <aside class="chat-sidebar" aria-label="Conversation controls">
      <div class="chat-sidebar-block">
        <span class="eyebrow">Mode</span>
        <div class="tab-strip chat-tabs" role="tablist" aria-label="Conversation mode">
          {#each tabs as tab (tab)}
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === tab}
              class:active={activeTab === tab}
              class="tab-button"
              onclick={() => switchTab(tab)}
            >
              {tab}
            </button>
          {/each}
        </div>
      </div>

      <div class="chat-sidebar-block">
        <div class="chat-sidebar-header">
          <div>
            <span class="eyebrow">Sessions</span>
            <strong class="chat-session-current">{selectedThread}</strong>
          </div>
          <button type="button" class="secondary-button session-create" onclick={createSession} disabled={!interactionState.canCreateSession}>New</button>
        </div>
        <div class="chat-session-list">
          {#if threads.length === 0}
            <p class="chat-sidebar-empty muted">No sessions recorded yet.</p>
          {:else}
            {#each threads as thread (thread.thread_id)}
              <button type="button" class:active={selectedThread === thread.thread_id} class="chat-session-item" onclick={() => selectSession(thread.thread_id)}>
                <span class="chat-session-name">{thread.thread_id}</span>
                <small>{thread.messages.length} msgs</small>
              </button>
            {/each}
          {/if}
        </div>
      </div>

      <div class="chat-sidebar-block chat-target-picker">
        <label class="eyebrow" for="chat-target-select">Target</label>
        <div class="select-shell">
          <select id="chat-target-select" bind:value={selectedAgent} class="control-input" onchange={handleTargetChange}>
            {#each activeCatalog as agentName (agentName)}
              <option value={agentName}>{agentName}</option>
            {/each}
          </select>
          <span class="select-icon">{@html chevronIcon}</span>
        </div>
      </div>
    </aside>

    <div class="chat-main">
      <header class="chat-toolbar">
        <div class="chat-toolbar-title">
          <span class="eyebrow">Live channel</span>
          <h3>{selectedAgent || 'Runtime console'}</h3>
        </div>
        <div class="chat-toolbar-meta">
          <span>{activeTab === 'agents' ? 'Direct exchange' : 'Runtime handoff planning'}</span>
          <strong>{messages.length} messages</strong>
        </div>
      </header>

      <div class="chat-context-status">
        <div class="chat-context-row">
          <span class="eyebrow">Context</span>
          <strong>{activeContext || 'Unknown context'}</strong>
        </div>
        <p class="muted">Attachment: {attachment || 'detached'}</p>
        {#if activeTab === 'runtimes'}
          <p class="muted">Runtime planning only. Direct sends stay disabled in this first pass.</p>
        {/if}
      </div>

      <div class="chat-transcript-shell">
        <div
          class="chat-stream compact chat-transcript"
          bind:this={transcriptEl}
          role="log"
          aria-live="polite"
          aria-relevant="additions"
          aria-label="Conversation transcript"
        >
          {#if messages.length === 0 && !sending}
            <div class="chat-empty-state">
              <span class="eyebrow">Ready</span>
              <h4>Start with a concrete ask</h4>
              <p class="muted">Use a prompt below to start with a search, a registry lookup, or a tool-selection question.</p>
              <div class="chat-prompt-grid">
                {#each quickActions as action (action)}
                  <button type="button" class="chat-prompt-chip" onclick={() => applyQuickAction(action)}>{action}</button>
                {/each}
              </div>
            </div>
          {/if}

          {#each messages as message, index (`${message.role}-${index}`)}
            {@const stamp = formatStamp(message, index)}
            <article class={`chat-message-row ${message.role === 'assistant' ? 'assistant' : 'user'}`}>
              <article class={`chat-bubble ${message.role === 'assistant' ? 'assistant' : 'user'}`}>
                <header class="chat-bubble-head">
                  <span class="chat-meta">{message.role === 'assistant' ? 'assistant' : 'operator'}</span>
                  {#if stamp}<time class="chat-time">{stamp}</time>{/if}
                </header>
                {#if markdownEnabled && message.role === 'assistant'}
                  <div class="chat-body markdown-body">{@html renderMarkdownContent(message.content)}</div>
                {:else}
                  <div class="chat-body">{message.content}</div>
                {/if}
              </article>
              <span class="chat-avatar" aria-hidden="true">{@html message.role === 'assistant' ? botIcon : userIcon}</span>
            </article>
          {/each}

          {#if sending}
            <article class="chat-message-row assistant chat-streaming" aria-label="Assistant is responding">
              <div class="chat-bubble assistant chat-typing">
                <header class="chat-bubble-head">
                  <span class="chat-meta">assistant · streaming</span>
                </header>
                <span class="chat-typing-dots" aria-hidden="true"><i></i><i></i><i></i></span>
              </div>
              <span class="chat-avatar" aria-hidden="true">{@html botIcon}</span>
            </article>
          {/if}
        </div>

        <div class="chat-composer">
          <div class="chat-composer-shell">
            <textarea
              bind:value={draft}
              class="control-input chat-composer-input"
              rows="3"
              aria-label="Compose a message"
              placeholder={activeTab === 'runtimes' ? 'Runtime planning only. Switch to Agents to send a live message.' : 'Ask the active target something specific'}
              onkeydown={onDraftKeydown}
              disabled={interactionState.composerDisabled}
            ></textarea>
            <button type="button" class="composer-send chat-composer-action" onclick={sendMessage} aria-label={sending ? 'Sending message' : 'Send message'} disabled={!interactionState.canSend}>
              <span class="chat-composer-action-icon">{@html sending ? spinnerIcon : sendIcon}</span>
              <span>{activeTab === 'runtimes' ? 'Runtime planning only' : sending ? 'Sending…' : 'Send'}</span>
            </button>
          </div>
          <p class="chat-composer-hint muted">
            {runtimesPlanningOnly ? 'Switch to the Agents tab to send a live message.' : 'Enter to send · Shift + Enter for a new line'}
          </p>
        </div>
      </div>
    </div>
  </div>
</section>

<style>
  .chat-console {
    display: grid;
    gap: 1rem;
  }

  .chat-alert {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.7rem 0.85rem;
    border: 1px solid color-mix(in oklab, oklch(0.65 0.19 25) 46%, var(--border));
    border-radius: calc(var(--radius) + 0.2rem);
    background: color-mix(in oklab, oklch(0.65 0.19 25) 10%, var(--card));
    color: var(--foreground);
    font-size: 0.9rem;
  }

  .chat-alert-icon {
    display: inline-flex;
    width: 1.15rem;
    height: 1.15rem;
    color: oklch(0.72 0.17 25);
    flex: none;
  }

  .chat-alert-icon :global(svg) {
    width: 100%;
    height: 100%;
  }

  .chat-alert-copy {
    flex: 1;
    min-width: 0;
  }

  .chat-alert-action {
    flex: none;
    padding: 0.35rem 0.7rem;
    border: 1px solid color-mix(in oklab, oklch(0.65 0.19 25) 50%, var(--border));
    border-radius: 999px;
    background: color-mix(in oklab, oklch(0.65 0.19 25) 16%, var(--accent));
    color: var(--foreground);
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
  }

  .chat-workbench {
    display: grid;
    grid-template-columns: 16rem minmax(0, 1fr);
    gap: 1.5rem;
    align-items: start;
  }

  .chat-sidebar {
    display: grid;
    gap: 1.25rem;
    padding-right: 1.15rem;
    border-right: 1px solid color-mix(in oklab, var(--border) 90%, transparent);
  }

  .chat-sidebar-block {
    display: grid;
    gap: 0.55rem;
    min-width: 0;
  }

  .chat-sidebar-header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
  }

  .chat-session-current {
    display: block;
    margin-top: 0.1rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chat-session-list {
    display: grid;
    gap: 0.35rem;
    max-height: 16rem;
    overflow-y: auto;
    padding-right: 0.15rem;
  }

  .chat-sidebar-empty {
    margin: 0;
    padding: 0.6rem 0.2rem;
    font-size: 0.85rem;
  }

  .chat-session-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chat-main {
    display: grid;
    gap: 1rem;
    min-width: 0;
  }

  .chat-toolbar {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 1rem;
    align-items: end;
    padding-bottom: 0.85rem;
    border-bottom: 1px solid color-mix(in oklab, var(--border) 85%, transparent);
  }

  .chat-toolbar h3 {
    margin: 0.1rem 0 0;
    font-size: 1.05rem;
  }

  .chat-toolbar-meta {
    display: grid;
    gap: 0.15rem;
    justify-items: end;
    text-align: right;
  }

  .chat-toolbar-meta strong {
    font-variant-numeric: tabular-nums;
  }

  .chat-context-status {
    display: grid;
    gap: 0.3rem;
    padding: 0.8rem 0.9rem;
    border: 1px solid color-mix(in oklab, var(--border) 92%, transparent);
    border-radius: calc(var(--radius) + 0.15rem);
    background: color-mix(in oklab, var(--accent) 72%, transparent);
  }

  .chat-context-row {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .chat-context-status p {
    margin: 0;
  }

  .chat-transcript-shell {
    position: relative;
    display: grid;
    gap: 0.55rem;
  }

  .chat-transcript {
    display: grid;
    gap: 0.85rem;
    padding: 0.2rem 0.35rem 0.35rem 0.05rem;
    max-height: min(60vh, 40rem);
    overflow-y: auto;
    scroll-behavior: smooth;
  }

  .chat-message-row {
    display: grid;
    gap: 0.6rem;
    align-items: start;
    animation: chat-fade-in 0.18s ease-out;
  }

  .chat-message-row.assistant {
    grid-template-columns: 2rem minmax(0, 1fr);
  }

  .chat-message-row.user {
    grid-template-columns: minmax(0, 1fr) 2rem;
  }

  .chat-message-row.assistant .chat-avatar {
    order: -1;
  }

  .chat-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    border: 1px solid var(--border);
    background: color-mix(in oklab, var(--accent) 80%, transparent);
    color: var(--muted-foreground);
  }

  .chat-avatar :global(svg) {
    width: 1.1rem;
    height: 1.1rem;
  }

  .chat-message-row.user .chat-avatar {
    border-color: color-mix(in oklab, var(--primary) 30%, var(--border));
    background: color-mix(in oklab, var(--primary) 18%, var(--accent));
    color: color-mix(in oklab, var(--primary) 80%, var(--foreground));
  }

  .chat-bubble {
    display: grid;
    gap: 0.35rem;
    max-width: min(46rem, 100%);
    padding: 0.8rem 0.95rem;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) + 0.4rem);
    background: color-mix(in oklab, var(--card) 86%, transparent);
    box-shadow: 0 1px 0 color-mix(in oklab, var(--foreground) 4%, transparent);
  }

  .chat-message-row.assistant .chat-bubble {
    justify-self: start;
    border-top-left-radius: calc(var(--radius) + 0.1rem);
  }

  .chat-message-row.user .chat-bubble {
    justify-self: end;
    border-color: color-mix(in oklab, var(--primary) 26%, var(--border));
    background: color-mix(in oklab, var(--primary) 12%, var(--card));
    border-top-right-radius: calc(var(--radius) + 0.1rem);
  }

  .chat-bubble-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .chat-time {
    font-size: 0.7rem;
    color: var(--muted-foreground);
    font-variant-numeric: tabular-nums;
  }

  .chat-body {
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.55;
  }

  .chat-body :global(.markdown-body p:last-child),
  .chat-body :global(.markdown-body ul:last-child),
  .chat-body :global(.markdown-body ol:last-child) {
    margin-bottom: 0;
  }

  .chat-body :global(.markdown-body pre) {
    margin: 0.5rem 0 0;
    padding: 0.75rem 0.85rem;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) + 0.15rem);
    background: color-mix(in oklab, var(--background) 70%, transparent);
    overflow-x: auto;
  }

  .chat-body :global(.markdown-body code) {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.85em;
  }

  .chat-typing {
    display: grid;
    gap: 0.4rem;
    min-width: 4.5rem;
  }

  .chat-typing-dots {
    display: inline-flex;
    align-items: center;
    gap: 0.28rem;
    padding: 0.15rem 0;
  }

  .chat-typing-dots i {
    width: 0.42rem;
    height: 0.42rem;
    border-radius: 50%;
    background: var(--muted-foreground);
    animation: chat-bounce 1.15s ease-in-out infinite;
  }

  .chat-typing-dots i:nth-child(2) {
    animation-delay: 0.15s;
  }

  .chat-typing-dots i:nth-child(3) {
    animation-delay: 0.3s;
  }

  .chat-composer {
    position: sticky;
    bottom: 0;
    z-index: 3;
    padding-top: 0.55rem;
    background: linear-gradient(
      180deg,
      color-mix(in oklab, var(--card) 0%, transparent) 0%,
      color-mix(in oklab, var(--card) 96%, transparent) 34%,
      var(--card) 100%
    );
  }

  .chat-composer-shell {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.6rem;
    align-items: end;
    padding: 0.5rem;
    border: 1px solid color-mix(in oklab, var(--border) 92%, transparent);
    border-radius: calc(var(--radius) + 0.6rem);
    background: color-mix(in oklab, var(--card) 94%, transparent);
    box-shadow: 0 10px 30px color-mix(in oklab, var(--background) 88%, transparent);
    transition: border-color 140ms ease, box-shadow 140ms ease;
  }

  .chat-composer-shell:focus-within {
    border-color: color-mix(in oklab, var(--primary) 36%, var(--border));
    box-shadow: 0 0 0 1px color-mix(in oklab, var(--primary) 20%, transparent),
      0 16px 34px color-mix(in oklab, var(--background) 80%, transparent);
  }

  .chat-composer-input {
    min-height: 4.75rem;
    max-height: 12rem;
    padding: 0.8rem 0.9rem;
    border: 0;
    border-radius: calc(var(--radius) + 0.2rem);
    background: transparent;
    box-shadow: none;
    font-size: 0.95rem;
    line-height: 1.5;
    resize: vertical;
  }

  .chat-composer-input:focus {
    box-shadow: none;
    outline: none;
  }

  .chat-composer-action {
    align-self: end;
    min-height: 2.7rem;
    white-space: nowrap;
  }

  .chat-composer-hint {
    margin: 0.4rem 0.2rem 0;
    font-size: 0.76rem;
  }

  @keyframes chat-fade-in {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes chat-bounce {
    0%,
    60%,
    100% {
      transform: translateY(0);
      opacity: 0.55;
    }
    30% {
      transform: translateY(-3px);
      opacity: 1;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .chat-transcript {
      scroll-behavior: auto;
    }

    .chat-message-row,
    .chat-typing-dots i {
      animation: none;
    }
  }

  @media (max-width: 1100px) {
    .chat-workbench {
      grid-template-columns: 1fr;
    }

    .chat-sidebar {
      padding-right: 0;
      padding-bottom: 1rem;
      border-right: 0;
      border-bottom: 1px solid color-mix(in oklab, var(--border) 90%, transparent);
    }

    .chat-session-list {
      max-height: 12rem;
    }
  }

  @media (max-width: 720px) {
    .chat-toolbar,
    .chat-composer-shell {
      grid-template-columns: 1fr;
      align-items: stretch;
    }

    .chat-toolbar-meta {
      justify-items: start;
      text-align: left;
    }

    .chat-composer-action {
      justify-content: center;
      width: 100%;
    }

    .chat-transcript {
      max-height: none;
    }
  }
</style>
