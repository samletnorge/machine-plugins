import { mount } from 'svelte';
import DomainPanel from '../components/DomainPanel.svelte';

const target = document.getElementById('memory-island');

if (target) {
  mount(DomainPanel, {
    target,
    props: {
      domain: 'memory',
      title: 'Memory',
      endpoint: target.dataset.endpoint ?? '/_studio/api/memory/threads'
    }
  });
}
