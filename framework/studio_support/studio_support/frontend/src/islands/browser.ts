import { mount } from 'svelte';
import DomainPanel from '../components/DomainPanel.svelte';

const target = document.getElementById('browser-island');

if (target) {
  mount(DomainPanel, {
    target,
    props: {
      domain: 'browser',
      title: 'Browser',
      endpoint: target.dataset.endpoint ?? '/_studio/api/browser/sessions'
    }
  });
}
