import { mount } from 'svelte';
import DomainPanel from '../components/DomainPanel.svelte';

const target = document.getElementById('observe-island');

if (target) {
  mount(DomainPanel, {
    target,
    props: {
      domain: 'observe',
      title: 'Observability',
      endpoint: target.dataset.endpoint ?? '/_studio/api/observe/traces'
    }
  });
}
