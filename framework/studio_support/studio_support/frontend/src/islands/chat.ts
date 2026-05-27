import { mount } from 'svelte';
import ChatWindow from '../components/ChatWindow.svelte';

const target = document.getElementById('chat-island');

if (target) {
  mount(ChatWindow, {
    target,
    props: {
      threadsEndpoint: target.dataset.threadsEndpoint ?? '',
      messagesEndpoint: target.dataset.messagesEndpoint ?? '',
      sessionsEndpoint: target.dataset.sessionsEndpoint ?? '',
      renderMarkdown: target.dataset.renderMarkdown ?? 'false',
      chatTabs: target.dataset.chatTabs ?? ''
    }
  });
}
