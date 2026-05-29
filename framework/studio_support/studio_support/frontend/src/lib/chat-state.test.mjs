import assert from 'node:assert/strict';
import { deriveChatInteractionState, deriveChatViewState, deriveTargetChange, deriveAgentTargetChange, deriveInitialTab, deriveTabSelection } from './chat-state.ts';

const catalog = {
  agents: ['greeter', 'researcher'],
  runtimes: ['basic-runtime', 'backup-runtime']
};

const threads = [
  {
    thread_id: 'thread-1',
    agent: 'greeter',
    messages: [{ role: 'user', content: 'hello' }]
  }
];

const runtimesView = deriveChatViewState({
  activeTab: 'runtimes',
  selectedThread: 'thread-1',
  selectedAgent: 'greeter',
  threads,
  catalog
});

assert.equal(runtimesView.selectedThread, 'thread-1');
assert.equal(runtimesView.selectedAgent, 'basic-runtime');
assert.deepEqual(runtimesView.messages, []);

const preservedRuntimeView = deriveChatViewState({
  activeTab: 'runtimes',
  selectedThread: 'thread-1',
  selectedAgent: 'basic-runtime',
  threads,
  catalog
});

assert.equal(preservedRuntimeView.selectedAgent, 'basic-runtime');

const agentsView = deriveChatViewState({
  activeTab: 'agents',
  selectedThread: 'thread-1',
  selectedAgent: 'basic-runtime',
  threads,
  catalog
});

assert.equal(agentsView.selectedThread, 'thread-1');
assert.equal(agentsView.selectedAgent, 'greeter');
assert.deepEqual(agentsView.messages, [{ role: 'user', content: 'hello' }]);

const preservedAgentComposerView = deriveChatViewState({
  activeTab: 'agents',
  selectedThread: 'default',
  selectedAgent: 'researcher',
  threads,
  catalog
});

assert.equal(preservedAgentComposerView.selectedThread, 'default');
assert.equal(preservedAgentComposerView.selectedAgent, 'researcher');
assert.deepEqual(preservedAgentComposerView.messages, []);

const blankAgentThreadView = deriveChatViewState({
  activeTab: 'agents',
  selectedThread: 'thread-blank-agent',
  selectedAgent: 'researcher',
  threads: [
    {
      thread_id: 'thread-blank-agent',
      agent: '',
      messages: [{ role: 'assistant', content: 'seed' }]
    }
  ],
  catalog
});

assert.equal(blankAgentThreadView.selectedAgent, 'researcher');
assert.deepEqual(blankAgentThreadView.messages, [{ role: 'assistant', content: 'seed' }]);

const targetChangeView = deriveAgentTargetChange('researcher');

assert.deepEqual(targetChangeView, {
  selectedThread: 'default',
  selectedAgent: 'researcher',
  messages: []
});

assert.deepEqual(deriveChatInteractionState('agents', false, '', catalog, ''), {
  canSend: false,
  canCreateSession: false,
  composerDisabled: true
});

assert.deepEqual(deriveChatInteractionState('agents', false, 'greeter', catalog, ''), {
  canSend: false,
  canCreateSession: false,
  composerDisabled: false
});

assert.deepEqual(deriveChatInteractionState('agents', false, 'greeter', catalog, ' hello ', true), {
  canSend: true,
  canCreateSession: true,
  composerDisabled: false
});

assert.deepEqual(deriveChatInteractionState('agents', true, 'greeter', catalog, 'hello', true), {
  canSend: false,
  canCreateSession: false,
  composerDisabled: true
});

assert.deepEqual(deriveChatInteractionState('runtimes', false, 'basic-runtime', catalog, '', true), {
  canSend: false,
  canCreateSession: false,
  composerDisabled: true
});

assert.equal(deriveTabSelection('agents', catalog, 'researcher'), 'researcher');
assert.equal(deriveTabSelection('runtimes', catalog, 'backup-runtime'), 'backup-runtime');

const runtimeTargetChangeView = deriveTargetChange('runtimes', 'backup-runtime', 'thread-1', [
  { role: 'assistant', content: 'kept-for-state' }
]);

assert.deepEqual(runtimeTargetChangeView, {
  selectedThread: 'thread-1',
  selectedAgent: 'backup-runtime',
  messages: [{ role: 'assistant', content: 'kept-for-state' }]
});

const emptyAgentsView = deriveChatViewState({
  activeTab: 'agents',
  selectedThread: 'missing-thread',
  selectedAgent: '',
  threads: [],
  catalog
});

assert.equal(emptyAgentsView.selectedThread, 'default');
assert.equal(emptyAgentsView.selectedAgent, 'greeter');
assert.deepEqual(emptyAgentsView.messages, []);

assert.equal(deriveTabSelection('agents', catalog), 'greeter');
assert.equal(deriveTabSelection('runtimes', catalog), 'basic-runtime');
assert.equal(deriveInitialTab(['agents', 'runtimes']), 'agents');
assert.equal(deriveInitialTab(['runtimes']), 'runtimes');
assert.equal(deriveInitialTab([]), 'agents');
