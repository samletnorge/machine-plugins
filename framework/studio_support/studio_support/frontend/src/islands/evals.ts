import { mount } from 'svelte';
import DomainPanel from '../components/DomainPanel.svelte';

const target = document.getElementById('evals-island');

if (target) {
  mount(DomainPanel, {
    target,
    props: {
      domain: 'evals',
      title: 'Evals',
      endpoint: target.dataset.endpoint ?? '/_studio/api/evals/runs'
    }
  });
}
