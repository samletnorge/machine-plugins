<script lang="ts">
  import { getJson, postJson } from '../lib/api';
  import { renderMarkdown as renderMarkdownContent } from '../lib/markdown';
  import type { ChatMessage, ChatThreadsPayload } from '../lib/types';

  interface Props {
    threadsEndpoint: string;
    messagesEndpoint: string;
    sessionsEndpoint?: string;
    renderMarkdown?: string;
    chatTabs?: string;
  }

  let { threadsEndpoint, messagesEndpoint, sessionsEndpoint = '', renderMarkdown = 'false', chatTabs = '' }: Props = $props();

  let threads = $state<ChatThreadsPayload['threads']>([]);
  let catalog = $state<ChatThreadsPayload['catalog']>({ agents: [], runtimes: [] });
  let selectedThread = $state('default');
  let selectedAgent = $state('');
  let activeTab = $state<'agents' | 'runtimes'>('agents');
  let messages = $state<ChatMessage[]>([]);
  let draft = $state('');
  let sending = $state(false);
  let loadError = $state('');

  let sessionMessagesEndpoint = $derived(
    messagesEndpoint.replace('/default/messages', `/${selectedThread}/messages`)
  );

  function onDraftKeydown(event: KeyboardEvent) {
    if (event.key !== 'Enter' || event.shiftKey) return;
    event.preventDefault();
    void sendMessage();
  }

  let markdownEnabled = $derived(renderMarkdown === 'true');
  let tabs = $derived(chatTabs.split(',').filter(Boolean) as Array<'agents' | 'runtimes'>);

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

  const chevronIcon = `<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m5 7 5 6 5-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const sendIcon = `<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4 10h9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="m10 4 6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const spinnerIcon = `<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.8" opacity="0.28"/><path d="M17 10a7 7 0 0 0-7-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;

  function applyQuickAction(prompt: string) {
    draft = prompt;
  }

  async function loadThreads() {
    try {
      const payload = await getJson<ChatThreadsPayload>(threadsEndpoint);
      catalog = payload.catalog;
      threads = payload.threads;
      const activeThread = payload.threads.find((thread) => thread.thread_id === selectedThread) ?? payload.threads[0];
      selectedThread = activeThread?.thread_id ?? 'default';
      selectedAgent = activeThread?.agent ?? payload.catalog.agents[0] ?? payload.catalog.runtimes[0] ?? '';
      messages = activeThread?.messages ?? [];
      loadError = '';
    } catch (error) {
      loadError = error instanceof Error ? error.message : 'Failed to load threads';
    }
  }

  async function createSession() {
    if (!sessionsEndpoint) return;
    try {
      const payload = await postJson<{ thread_id: string }>(sessionsEndpoint, {});
      selectedThread = payload.thread_id;
      await loadThreads();
      messages = [];
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
    selectedAgent = thread.agent || selectedAgent;
    messages = thread.messages;
  }

  async function sendMessage() {
    if (!draft.trim()) return;
    const message = draft.trim();
    draft = '';
    sending = true;
    try {
      const payload = await postJson<{ thread_id: string; messages: ChatMessage[] }>(sessionMessagesEndpoint, {
        agent: selectedAgent,
        message
      });
      const updatedThread = { thread_id: payload.thread_id, agent: selectedAgent, messages: payload.messages };
      const existingIndex = threads.findIndex((thread) => thread.thread_id === payload.thread_id);
      if (existingIndex >= 0) {
        threads = threads.map((thread) => (thread.thread_id === payload.thread_id ? updatedThread : thread));
      } else {
        threads = [updatedThread, ...threads];
      }
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
    void loadThreads();
  });
</script>

<section class="chat-console">
  {#if loadError}
    <p class="muted">{loadError}</p>
  {/if}

  <div class="chat-workbench">
    <aside class="chat-sidebar">
      <div class="chat-sidebar-block">
        <span class="eyebrow">Mode</span>
        <div class="tab-strip chat-tabs">
          {#each tabs as tab (tab)}
            <button type="button" class:active={activeTab === tab} class="tab-button" onclick={() => { activeTab = tab; selectedAgent = catalog[tab][0] ?? ''; }}>
              {tab}
            </button>
          {/each}
        </div>
      </div>

      <div class="chat-sidebar-block">
        <div class="chat-sidebar-header">
          <div>
            <span class="eyebrow">Sessions</span>
            <strong>{selectedThread}</strong>
          </div>
          <button type="button" class="secondary-button session-create" onclick={createSession}>New</button>
        </div>
        <div class="chat-session-list">
          {#each threads as thread (thread.thread_id)}
            <button type="button" class:active={selectedThread === thread.thread_id} class="chat-session-item" onclick={() => selectSession(thread.thread_id)}>
              <span>{thread.thread_id}</span>
              <small>{thread.messages.length} msgs</small>
            </button>
          {/each}
        </div>
      </div>

      <div class="chat-sidebar-block chat-target-picker">
        <span class="eyebrow">Target</span>
        <label class="select-shell">
          <select bind:value={selectedAgent} class="control-input">
            {#each activeCatalog as agentName (agentName)}
              <option value={agentName}>{agentName}</option>
            {/each}
          </select>
          <span class="select-icon">{@html chevronIcon}</span>
        </label>
      </div>
    </aside>

    <div class="chat-main">
      <header class="chat-toolbar">
        <div>
          <span class="eyebrow">Live channel</span>
          <h3>{selectedAgent || 'Runtime console'}</h3>
        </div>
        <div class="chat-toolbar-meta">
          <span>{activeTab === 'agents' ? 'Direct exchange' : 'Runtime handoff planning'}</span>
          <strong>{messages.length} messages</strong>
        </div>
      </header>

      <div class="chat-transcript-shell">
        <div class="chat-stream compact chat-transcript">
          {#if messages.length === 0}
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
            <article class={`chat-bubble ${message.role === 'assistant' ? 'assistant' : 'user'}`}>
              <div class="chat-meta">{message.role}</div>
              {#if markdownEnabled && message.role === 'assistant'}
                <div class="chat-body markdown-body">{@html renderMarkdownContent(message.content)}</div>
              {:else}
                <div class="chat-body">{message.content}</div>
              {/if}
            </article>
          {/each}
        </div>

        <div class="chat-composer">
          <div class="chat-composer-shell">
            <textarea bind:value={draft} class="control-input chat-composer-input" rows="3" placeholder="Ask the active target something specific" onkeydown={onDraftKeydown}></textarea>
            <button type="button" class="composer-send chat-composer-action" onclick={sendMessage} aria-label={sending ? 'Sending message' : 'Send message'}>
              <span class="chat-composer-action-icon">{@html sending ? spinnerIcon : sendIcon}</span>
              <span>{sending ? 'Sending…' : 'Send'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
