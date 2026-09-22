import { mount } from 'svelte';
import DomainPanel from '../components/DomainPanel.svelte';

const target = document.getElementById('deploy-island');

if (target) {
  mount(DomainPanel, {
    target,
    props: {
      domain: 'deploy',
      title: 'Deploy',
      endpoint: target.dataset.endpoint ?? '/_studio/api/deploy/targets'
    }
  });
}
