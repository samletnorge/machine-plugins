import { mount } from 'svelte';
import DomainPanel from '../components/DomainPanel.svelte';

const target = document.getElementById('workspace-island');

if (target) {
  mount(DomainPanel, {
    target,
    props: {
      domain: 'workspace',
      title: 'Workspace',
      endpoint: target.dataset.endpoint ?? '/_studio/api/workspace/files'
    }
  });
}
