import type { ChatMessage, ChatThreadsPayload } from './types';

export type ChatTab = 'agents' | 'runtimes';

export function deriveInitialTab(tabs: ChatTab[]): ChatTab {
  return !tabs.length || tabs.includes('agents') ? 'agents' : 'runtimes';
}

export interface ChatViewStateInput {
  activeTab: ChatTab;
  selectedThread: string;
  selectedAgent: string;
  threads: ChatThreadsPayload['threads'];
  catalog: ChatThreadsPayload['catalog'];
}

export interface ChatViewStateOutput {
  selectedThread: string;
  selectedAgent: string;
  messages: ChatMessage[];
}

export interface ChatInteractionState {
  canSend: boolean;
  canCreateSession: boolean;
  composerDisabled: boolean;
}

export function deriveAgentTargetChange(selectedAgent: string): ChatViewStateOutput {
  return {
    selectedThread: 'default',
    selectedAgent,
    messages: []
  };
}

export function deriveTargetChange(
  activeTab: ChatTab,
  selectedAgent: string,
  selectedThread: string,
  messages: ChatMessage[]
): ChatViewStateOutput {
  if (activeTab === 'runtimes') {
    return {
      selectedThread,
      selectedAgent,
      messages
    };
  }

  return deriveAgentTargetChange(selectedAgent);
}

export function deriveChatInteractionState(
  activeTab: ChatTab,
  sending: boolean,
  selectedAgent = '',
  catalog?: ChatThreadsPayload['catalog'],
  draft = '',
  canCreateSession = false
): ChatInteractionState {
  if (activeTab === 'runtimes') {
    return {
      canSend: false,
      canCreateSession: false,
      composerDisabled: true
    };
  }

  const hasValidAgent = catalog ? catalog.agents.includes(selectedAgent) : Boolean(selectedAgent);
  const hasDraft = Boolean(draft.trim());

  return {
    canSend: !sending && hasValidAgent && hasDraft,
    canCreateSession: !sending && canCreateSession,
    composerDisabled: sending || !hasValidAgent
  };
}

export function deriveChatViewState({
  activeTab,
  selectedThread,
  selectedAgent,
  threads,
  catalog
}: ChatViewStateInput): ChatViewStateOutput {
  if (activeTab === 'runtimes') {
    const runtimeSelection = catalog.runtimes.includes(selectedAgent)
      ? selectedAgent
      : (catalog.runtimes[0] ?? '');

    return {
      selectedThread,
      selectedAgent: runtimeSelection,
      messages: []
    };
  }

  if (selectedThread === 'default') {
    return {
      selectedThread: 'default',
      selectedAgent: selectedAgent || catalog.agents[0] || '',
      messages: []
    };
  }

  const activeThread = threads.find((thread) => thread.thread_id === selectedThread) ?? threads[0];
  const threadAgent = activeThread?.agent || '';

  return {
    selectedThread: activeThread?.thread_id ?? 'default',
    selectedAgent: threadAgent || selectedAgent || catalog.agents[0] || '',
    messages: activeThread?.messages ?? []
  };
}

export function deriveTabSelection(
  activeTab: ChatTab,
  catalog: ChatThreadsPayload['catalog'],
  currentSelection = ''
): string {
  const availableTargets = activeTab === 'runtimes' ? catalog.runtimes : catalog.agents;
  return availableTargets.includes(currentSelection) ? currentSelection : (availableTargets[0] ?? '');
}
